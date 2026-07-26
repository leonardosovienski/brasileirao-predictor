"""Modo SOMBRA (H3): captura picks do funil pré-registrado SEM dinheiro real.

Por que existe: o walk-forward deu NO-GO em H1 (IC do pnl cruza zero) mas com
CLV open +19,55% — concentrado em UNDER e crescente com o edge (estratificação
2026-07-11). A pergunta que só a operação ao vivo responde: o preço de
abertura do Sofascore é CAPTURÁVEL, ou é abertura-fantasma? A H3 registra a
mesma janela do funil em jogos FUTUROS, com odds lidas ANTES do apito, e
liquida contra o resultado + fechamento reais.

Uso (rotina pré-rodada, depois do ingest):
    python -m src.ingest_sofascore                      # atualiza odds
    python scripts/sombra.py --capture                  # registra picks
    ... (jogos acontecem; novo ingest) ...
    python scripts/sombra.py --settle                   # liquida + CLV
    python scripts/sombra.py --report                   # painel da H3

Arquivos (append-only, fora do git):
    data/sombra_picks.jsonl    — 1 linha por pick capturado (dedupe por
                                 event_id+selection)
    data/sombra_results.jsonl  — 1 linha por pick liquidado

Regras duras: SÓ o mercado da H1 (OU 2.5), SÓ a janela pré-registrada
[min_edge, max_edge], SÓ jogo cujo apito está no futuro no momento da
captura. Banco em read-only.

H5 (h5-ensemble-xg-sombra-2026, registrada 2026-07-17): população PARALELA
com as probabilidades do ensemble atk/def-xG (src/xg_model.py) — mesmos
jogos, mesma janela, mesmas odds; arquivos separados (sombra_h5_*.jsonl).
A H3 continua BASELINE PURO (chama model.predict_match direto — imune à
flag ensemble_xg do serving). Capturar/settle da H5 só acontece com a flag
ligada E o cache do cron presente; sem eles, a H5 é pulada e a H3 não sente.
"""
import argparse
import json
import math
import os
import hashlib
import subprocess
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from src import db, model                              # noqa: E402
from src.ingest import load_config                     # noqa: E402
from src.math_utils import shin_probabilities          # noqa: E402
from src.data.prospective_shadow import record_hash, validate_pick  # noqa: E402
from src.data.bookmaker_odds import (                  # noqa: E402
    MAPPING_VERSION, SNAPSHOTS, closing_quote, load_snapshots, match_fixture,
    persist_snapshots)
from src.data.the_odds_api_provider import TheOddsApiProvider  # noqa: E402
from predictor_core.data.contracts import DataUnavailableError  # noqa: E402

# `pythonw.exe` (executavel de toda tarefa agendada) nao tem console: um
# processo de console filho ganharia janela VISIVEL na tela do dono.
# Saida ja e capturada, entao a flag nao esconde nada.
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

SNAPSHOTS_PATH = ROOT / "data" / SNAPSHOTS

# Coorte com bookmaker NOMEADO (pré-registrada em 2026-07-25). As trials
# `*-sombra-2026` antigas capturavam o agregado do Sofascore rotulado com o nome
# de um book que nunca forneceu aquele preço (defeito B-1). Trocar a fonte do
# preço e a definição de fechamento é mudança de configuração: coorte nova,
# contagem do zero, arquivos novos. Os ledgers antigos ficam intactos como
# LEGACY_INCOMPLETE e NÃO são migrados.
PICKS = ROOT / "data" / "sombra_picks_pinnacle.jsonl"
RESULTS = ROOT / "data" / "sombra_results_pinnacle.jsonl"
TRIAL = "h3-ou25-sombra-pinnacle-2026"

# H5 (ensemble atk/def-xG): população PARALELA à H3 — mesmos jogos, mesma
# janela de edge, mesmas odds; só muda a probabilidade do modelo. Arquivos
# separados para nunca contaminar a população da H3.
PICKS_H5 = ROOT / "data" / "sombra_h5_picks_pinnacle.jsonl"
RESULTS_H5 = ROOT / "data" / "sombra_h5_results_pinnacle.jsonl"
TRIAL_H5 = "h5-ensemble-xg-sombra-pinnacle-2026"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def _append(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _exige_meia_linha(ou_line: float) -> None:
    """O settle da sombra não implementa PUSH: em linha INTEIRA (ex.: 3.0),
    total == linha seria marcado como derrota nos DOIS lados — PNL errado em
    silêncio. As hipóteses pré-registradas (H3/H5) usam 2.5; qualquer outra
    linha inteira no config é erro de configuração e falha em voz alta."""
    if float(ou_line) == int(ou_line):
        sys.exit(f"over_under_line={ou_line} é linha INTEIRA — push não é "
                 "suportado pelo settle da sombra (H3/H5 pré-registradas em 2.5)")


def _odd_valida(o) -> bool:
    """Odd decimal real: finita e > 1.0 (0/negativa/NaN/Inf viram inválidas —
    CLV com odd-lixo do fechamento seria gravado NaN/absurdo no ledger)."""
    return isinstance(o, (int, float)) and math.isfinite(o) and o > 1.0


def _capture_funil(cfg, conn, predictor, picks_path, trial) -> int:
    """Funil pré-registrado (OU2.5, janela [min_edge, max_edge]) sobre jogos
    futuros — genérico na FONTE da probabilidade (`predictor(home, away) -> r`
    no formato de model.predict_match). A janela e o mercado NUNCA variam
    entre populações: é o que mantém H3 e H5 pareadas."""
    bt = cfg["backtest"]
    min_edge, max_edge = float(bt["min_edge"]), float(bt["max_edge"])
    ou_line = float(bt.get("over_under_line", 2.5))
    _exige_meia_linha(ou_line)

    ja = {(p["event_id"], p["selection"]) for p in _load_jsonl(picks_path)}
    now = datetime.now(timezone.utc)
    hoje = now.strftime("%Y-%m-%d")
    bookmaker = os.environ.get("BRASILEIRAO_BOOKMAKER")
    if not bookmaker:
        print("  [coorte prospectiva bloqueada: BRASILEIRAO_BOOKMAKER ausente; "
              "Sofascore agregado não é bookmaker auditável]")
        return 0
    code_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                 text=True, capture_output=True, check=False,
                                 creationflags=_NO_WINDOW).stdout.strip()
    if not code_commit:
        print("  [coorte prospectiva bloqueada: commit Git indisponível]")
        return 0

    # --- preço do BOOK designado (não mais o agregado do Sofascore) ---
    fixtures = [{"event_id": r[0], "home_team": r[1], "away_team": r[2],
                 "kickoff_at": r[3]}
                for r in conn.execute(
                    "SELECT event_id, home_team, away_team, kickoff_at "
                    "FROM sofascore_matches "
                    "WHERE home_score IS NULL AND kickoff_at IS NOT NULL")]
    try:
        api_rows = TheOddsApiProvider().fetch_ou25()
    except DataUnavailableError as exc:
        print(f"  [coorte prospectiva bloqueada: {exc}]")
        return 0
    novos, book_odds, nao_resolvidos = [], {}, {}
    for row in api_rows:
        if row["bookmaker"] != bookmaker:
            continue
        fixture, status = match_fixture(row, fixtures)
        if fixture is None:
            nao_resolvidos[(row.get("home_team"), row.get("away_team"))] = status
            continue
        snap = {"event_id": fixture["event_id"], "market": f"ou{ou_line}",
                "selection": row["selection"], "odd": row["decimal_odds"],
                "odds_captured_at": row["odds_captured_at"], "bookmaker": bookmaker,
                "source": row["source"], "source_event_id": row["source_event_id"],
                "canonical_match_id": row["canonical_match_id"],
                "kickoff_at": fixture["kickoff_at"], "retrieved_at": row["retrieved_at"],
                "raw_payload_hash": row["raw_payload_hash"],
                "adapter_version": row["adapter_version"],
                "identity_status": status, "mapping_version": MAPPING_VERSION}
        novos.append(snap)
        book_odds[(fixture["event_id"], row["selection"])] = snap
    gravados = persist_snapshots(SNAPSHOTS_PATH, novos)
    print(f"  [book {bookmaker}: {len(book_odds)} cotações elegíveis, "
          f"{gravados} snapshot(s) novo(s)]")
    for (h, a), status in sorted(nao_resolvidos.items(), key=lambda kv: str(kv[0])):
        print(f"  [identidade não resolvida: {h} x {a} — {status}]")
    if not book_odds:
        print("  [nenhuma cotação do book designado; nada a capturar]")
        return 0
    # abertura = a PRIMEIRA cotação que observamos deste book, não a do Sofascore
    historico = load_snapshots(SNAPSHOTS_PATH)
    aberturas: dict[tuple, tuple[str, float]] = {}
    for s in historico:
        chave = (s.get("event_id"), s.get("selection"))
        quando = s.get("odds_captured_at") or ""
        if chave not in aberturas or quando < aberturas[chave][0]:
            aberturas[chave] = (quando, s.get("odd"))

    n = 0
    rows = conn.execute(
        "SELECT event_id, date, home_team, away_team, kickoff_at "
        "FROM sofascore_matches WHERE home_score IS NULL AND date >= ? "
        "ORDER BY date", (hoje,)).fetchall()
    capture_turn = os.environ.get("BRASILEIRAO_CAPTURE_TURN", "manual")
    for eid, d, home, away, kickoff_at in rows:
        r = predictor(home, away)
        if r is None:
            continue
        p_over = r["over"].get(ou_line)
        if p_over is None:
            continue
        for sel, p_m in (("over", p_over), ("under", 1.0 - p_over)):
            snap = book_odds.get((eid, sel))
            if (eid, sel) in ja or snap is None:
                continue
            odd = snap["odd"]
            odd_open = aberturas.get((eid, sel), (None, None))[1]
            if not odd or odd <= 1.0:
                continue
            edge = p_m - 1.0 / odd
            if not (min_edge < edge <= max_edge):
                continue
            pick = {
                "pick_id": hashlib.sha256(f"{trial}:{eid}:{sel}".encode()).hexdigest(),
                "trial_id": trial,
                "model_version": str(cfg.get("model", {}).get("version", "frozen-config")),
                "code_commit": code_commit,
                "captured_at": now.isoformat(timespec="seconds"),
                "predicted_at": now.isoformat(timespec="seconds"),
                "kickoff_at": kickoff_at,
                # carimbo do PRÓPRIO book (last_update da cotação), não a hora
                # da nossa execução — é o que torna o pick auditável na origem
                "odds_captured_at": snap["odds_captured_at"],
                "captured_odds": round(odd, 3),
                "bookmaker": bookmaker, "source": snap["source"],
                "source_event_id": snap["source_event_id"],
                "canonical_match_id": snap["canonical_match_id"],
                "closing_definition_version": "closing-v1:last-valid-pre-kickoff-by-bookmaker",
                "data_quality_status": "PROSPECTIVE_ELIGIBLE",
                "capture_turn": capture_turn,
                "odds_source": snap["source"],
                "sofascore_event_id": str(eid),
                "identity_status": snap["identity_status"],
                "mapping_version": snap["mapping_version"],
                "raw_payload_hash": snap["raw_payload_hash"],
                "adapter_version": snap["adapter_version"],
                "event_id": eid, "date": d, "home": home, "away": away,
                "market": f"ou{ou_line}", "selection": sel,
                "odd": round(odd, 3), "odds_captured": round(odd, 3),
                "odds_open": (round(odd_open, 3)
                              if _odd_valida(odd_open) else None),
                "edge": round(edge, 4),
                "model_prob": round(p_m, 4),
                "lambda_home": round(r["lambda_a"], 3),
                "lambda_away": round(r["lambda_b"], 3),
                "trial": trial}
            pick["provenance_hash"] = record_hash(pick)
            invalid = validate_pick(pick)
            if invalid:
                print(f"  [pick rejeitado: {invalid}]")
                continue
            _append(picks_path, pick)
            ja.add((eid, sel))
            n += 1
            print(f"  pick [{trial.split('-')[0]}]: {d} {home} x {away} — "
                  f"{sel} {ou_line} @{odd} (edge {edge:+.1%})")
    return n


def capture(cfg, conn) -> int:
    """H3: baseline puro (mesmo motor desde o registro — imune à flag do
    ensemble por construção)."""
    max_goals = cfg["model"]["max_goals"]
    home_adv = float(cfg["elo"]["home_advantage"])
    elo = db.load_elo(conn)
    prow = db.load_params(conn)
    if not elo or not prow:
        sys.exit("cache vazio — rode python -m src.cron_update_models")
    params = (prow[0], prow[1], prow[2], prow[3])

    def predictor(home, away):
        if home not in elo or away not in elo:
            return None
        return model.predict_match(elo[home], elo[away], params, home_adv,
                                   max_goals=max_goals)

    return _capture_funil(cfg, conn, predictor, PICKS, TRIAL)


def capture_h5(cfg, conn) -> int:
    """H5: ensemble baseline × atk/def-xG (mesma mistura do serving). Roda em
    PARALELO à H3 sobre os mesmos jogos; exige a flag ligada E o cache do
    cron — sem eles, pula com aviso (a H3 não depende disto)."""
    if not (cfg.get("ensemble_xg") or {}).get("enabled"):
        return 0
    from src import xg_model
    row = db.load_xg_params(conn)
    if not row:
        print("  [H5 pulada: ensemble_xg ligado mas sem cache — rode "
              "python -m src.cron_update_models]")
        return 0
    xgp = row[0]
    max_goals = cfg["model"]["max_goals"]
    home_adv = float(cfg["elo"]["home_advantage"])
    w = float(cfg["ensemble_xg"].get("blend_weight", 0.5))
    elo = db.load_elo(conn)
    prow = db.load_params(conn)
    if not elo or not prow:
        sys.exit("cache vazio — rode python -m src.cron_update_models")
    params = (prow[0], prow[1], prow[2], prow[3])

    def predictor(home, away):
        if home not in elo or away not in elo:
            return None
        rb = model.predict_match(elo[home], elo[away], params, home_adv,
                                 max_goals=max_goals)
        rx = xg_model.predict(xgp, home, away, neutral=False,
                              max_goals=max_goals)
        return xg_model.blend(rb, rx, w_base=w)

    return _capture_funil(cfg, conn, predictor, PICKS_H5, TRIAL_H5)


def settle(cfg, conn, picks_path=PICKS, results_path=RESULTS,
           trial=TRIAL) -> int:
    ou_line = float(cfg["backtest"].get("over_under_line", 2.5))
    _exige_meia_linha(ou_line)
    liquidados = {(r["event_id"], r["selection"])
                  for r in _load_jsonl(results_path)}
    # Fechamento vem do histórico do MESMO book que precificou o pick — é o que
    # o campo `closing-v1:last-valid-pre-kickoff-by-bookmaker` sempre prometeu.
    book_snaps = load_snapshots(SNAPSHOTS_PATH)
    n = 0
    for p in _load_jsonl(picks_path):
        key = (p["event_id"], p["selection"])
        if key in liquidados:
            continue
        # dedupe INTRA-execução: pick duplicado no ledger (edição manual,
        # captura concorrente) liquidaria 2x na MESMA passada — o conjunto
        # `liquidados` era congelado na entrada e não via o que esta
        # execução já gravou (auditoria hostil 2026-07-18). PNL dobrado.
        liquidados.add(key)
        row = conn.execute(
            "SELECT home_score, away_score, odds_over, odds_under "
            "FROM sofascore_matches WHERE event_id = ?",
            (p["event_id"],)).fetchone()
        if not row or row[0] is None:
            continue                      # ainda não terminou
        hs, as_, c_over, c_under = row
        close_at = None
        if p.get("pick_id"):
            by_selection = {}
            for selection in ("over", "under"):
                quote = closing_quote(book_snaps, event_id=p["event_id"],
                                      market=p["market"], selection=selection,
                                      kickoff_at=p["kickoff_at"])
                if quote is not None:
                    by_selection[selection] = (quote["odd"], quote["odds_captured_at"])
            if p["selection"] not in by_selection:
                continue  # pending closing: economic cohort must not mature
            selected_close, close_at = by_selection[p["selection"]]
            if not _odd_valida(selected_close):
                continue
            c_over = by_selection.get("over", (None, None))[0]
            c_under = by_selection.get("under", (None, None))[0]
        total = hs + as_
        won = int((total > ou_line) if p["selection"] == "over"
                  else (total < ou_line))
        clv = None
        if _odd_valida(c_over) and _odd_valida(c_under):
            sh, _z, _o = shin_probabilities([c_over, c_under])
            p_close = sh[0] if p["selection"] == "over" else sh[1]
            clv = round(p["odd"] * float(p_close) - 1.0, 4)
        result = {
            "settled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event_id": p["event_id"], "selection": p["selection"],
            "date": p["date"], "home": p["home"], "away": p["away"],
            "odd": p["odd"], "edge": p["edge"], "score": f"{hs}-{as_}",
            "odds_close": (round(c_over, 3) if p["selection"] == "over"
                           and _odd_valida(c_over) else
                           round(c_under, 3) if p["selection"] == "under"
                           and _odd_valida(c_under) else None),
            "odds_close_pair": {
                "over": round(c_over, 3) if _odd_valida(c_over) else None,
                "under": round(c_under, 3) if _odd_valida(c_under) else None,
            },
            "stake_units": 1.0,
            "costs": {"status": "not_applicable_shadow_no_execution",
                      "amount_units": 0.0},
            "won": won, "pnl": round((p["odd"] - 1.0) if won else -1.0, 3),
            "clv": clv, "trial": trial}
        if p.get("pick_id"):
            result.update({"pick_id": p["pick_id"], "source_event_id": p["source_event_id"],
                           "selection": p["selection"], "result": "won" if won else "lost",
                           "settlement_status": "settled", "closing_odds": round(selected_close, 3),
                           "closing_captured_at": close_at,
                           "closing_definition_version": p["closing_definition_version"]})
            result["provenance_hash"] = record_hash(result)
        _append(results_path, result)
        n += 1
        print(f"  settle: {p['home']} {hs}x{as_} {p['away']} — "
              f"{p['selection']} {'GANHOU' if won else 'perdeu'}"
              + (f" | CLV {clv:+.2%}" if clv is not None else ""))
    return n


def _report_populacao(rotulo, picks_path, results_path) -> None:
    res = _load_jsonl(results_path)
    abertos = len(_load_jsonl(picks_path)) - len(res)
    print(f"{rotulo} — {len(res)} liquidados, {abertos} em aberto")
    if not res:
        return
    pnl = [r["pnl"] for r in res]
    clv = [r["clv"] for r in res if r["clv"] is not None]
    print(f"  ROI {st.mean(pnl):+.1%} | acerto {st.mean(r['won'] for r in res):.0%}"
          + (f" | CLV médio {st.mean(clv):+.2%} | bate fechamento "
             f"{st.mean(1 if c > 0 else 0 for c in clv):.0%}" if clv else ""))
    for sel in ("over", "under"):
        b = [r for r in res if r["selection"] == sel]
        if b:
            print(f"  {sel:<6} n={len(b):<4} ROI {st.mean(r['pnl'] for r in b):+.1%}")


def report() -> None:
    _report_populacao("H3 modo sombra (baseline)", PICKS, RESULTS)
    _report_populacao("H5 modo sombra (ensemble xG)", PICKS_H5, RESULTS_H5)

    # confronto pareado por jogo: onde os dois motores compraram, divergiram
    # ou so um entrou no funil (leitura observacional — nao muda gatilho)
    p3 = {p["event_id"]: p for p in _load_jsonl(PICKS)}
    p5 = {p["event_id"]: p for p in _load_jsonl(PICKS_H5)}
    eventos = sorted(set(p3) | set(p5),
                     key=lambda e: (p3.get(e) or p5[e])["date"])
    if eventos:
        print("\nH3 vs H5 por jogo (picks capturados):")
        print(f"  {'data':<10} {'jogo':<32} {'H3 (baseline)':<18} H5 (ensemble)")
        for e in eventos:
            ref = p3.get(e) or p5[e]
            jogo = f"{ref['home']} x {ref['away']}"[:32]
            f3 = (f"{p3[e]['selection']} @{p3[e]['odd']}" if e in p3 else "—")
            f5 = (f"{p5[e]['selection']} @{p5[e]['odd']}" if e in p5 else "—")
            marca = ("=" if e in p3 and e in p5
                     and p3[e]["selection"] == p5[e]["selection"] else
                     "X" if e in p3 and e in p5 else " ")
            print(f"  {ref['date']:<10} {jogo:<32} {f3:<18} {f5}  {marca}")
        print("  (= mesma selecao | X selecoes opostas no mesmo jogo)")

    r3 = {(r["event_id"], r["selection"]): r for r in _load_jsonl(RESULTS)}
    r5 = {(r["event_id"], r["selection"]): r for r in _load_jsonl(RESULTS_H5)}
    comuns = set(r3) & set(r5)
    if comuns:
        d3 = [r3[k]["pnl"] for k in comuns]
        d5 = [r5[k]["pnl"] for k in comuns]
        print(f"\npareado (mesmo jogo E mesma selecao, n={len(comuns)}): "
              f"ROI H3 {st.mean(d3):+.1%} | H5 {st.mean(d5):+.1%}")
    print("  (decisao de cada linha = IC do core sobre a propria populacao "
          "quando n >= 100; criterios no trials.json)")


def main():
    ap = argparse.ArgumentParser(description="Modo sombra da H3 (OU2.5)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--capture", action="store_true")
    g.add_argument("--settle", action="store_true")
    g.add_argument("--report", action="store_true")
    args = ap.parse_args()

    if args.report:
        report()
        return
    cfg = load_config()
    conn = db.connect(str(ROOT / cfg["database"]), read_only=True)
    if args.capture:
        n = capture(cfg, conn)
        print(f"{n} pick(s) novos em {PICKS.name}")
        n5 = capture_h5(cfg, conn)
        if n5:
            print(f"{n5} pick(s) novos em {PICKS_H5.name}")
    else:
        n = settle(cfg, conn)
        print(f"{n} pick(s) liquidados em {RESULTS.name}")
        n5 = settle(cfg, conn, PICKS_H5, RESULTS_H5, TRIAL_H5)
        if n5:
            print(f"{n5} pick(s) liquidados em {RESULTS_H5.name}")


if __name__ == "__main__":
    main()
