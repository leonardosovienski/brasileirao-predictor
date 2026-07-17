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

PICKS = ROOT / "data" / "sombra_picks.jsonl"
RESULTS = ROOT / "data" / "sombra_results.jsonl"
TRIAL = "h3-ou25-sombra-2026"

# H5 (ensemble atk/def-xG): população PARALELA à H3 — mesmos jogos, mesma
# janela de edge, mesmas odds; só muda a probabilidade do modelo. Arquivos
# separados para nunca contaminar a população da H3.
PICKS_H5 = ROOT / "data" / "sombra_h5_picks.jsonl"
RESULTS_H5 = ROOT / "data" / "sombra_h5_results.jsonl"
TRIAL_H5 = "h5-ensemble-xg-sombra-2026"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def _append(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _capture_funil(cfg, conn, predictor, picks_path, trial) -> int:
    """Funil pré-registrado (OU2.5, janela [min_edge, max_edge]) sobre jogos
    futuros — genérico na FONTE da probabilidade (`predictor(home, away) -> r`
    no formato de model.predict_match). A janela e o mercado NUNCA variam
    entre populações: é o que mantém H3 e H5 pareadas."""
    bt = cfg["backtest"]
    min_edge, max_edge = float(bt["min_edge"]), float(bt["max_edge"])
    ou_line = float(bt.get("over_under_line", 2.5))

    ja = {(p["event_id"], p["selection"]) for p in _load_jsonl(picks_path)}
    now = datetime.now(timezone.utc)
    hoje = now.strftime("%Y-%m-%d")

    n = 0
    rows = conn.execute(
        "SELECT event_id, date, home_team, away_team, odds_over, odds_under "
        "FROM sofascore_matches WHERE home_score IS NULL AND date >= ? "
        "AND odds_over IS NOT NULL AND odds_under IS NOT NULL "
        "ORDER BY date", (hoje,)).fetchall()
    for eid, d, home, away, o_over, o_under in rows:
        r = predictor(home, away)
        if r is None:
            continue
        p_over = r["over"].get(ou_line)
        if p_over is None:
            continue
        for sel, p_m, odd in (("over", p_over, o_over),
                              ("under", 1.0 - p_over, o_under)):
            if (eid, sel) in ja or not odd or odd <= 1.0:
                continue
            edge = p_m - 1.0 / odd
            if not (min_edge < edge <= max_edge):
                continue
            _append(picks_path, {
                "captured_at": now.isoformat(timespec="seconds"),
                "event_id": eid, "date": d, "home": home, "away": away,
                "market": f"ou{ou_line}", "selection": sel,
                "odd": round(odd, 3), "edge": round(edge, 4),
                "model_prob": round(p_m, 4),
                "lambda_home": round(r["lambda_a"], 3),
                "lambda_away": round(r["lambda_b"], 3),
                "trial": trial})
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
    liquidados = {(r["event_id"], r["selection"])
                  for r in _load_jsonl(results_path)}
    n = 0
    for p in _load_jsonl(picks_path):
        key = (p["event_id"], p["selection"])
        if key in liquidados:
            continue
        row = conn.execute(
            "SELECT home_score, away_score, odds_over, odds_under "
            "FROM sofascore_matches WHERE event_id = ?",
            (p["event_id"],)).fetchone()
        if not row or row[0] is None:
            continue                      # ainda não terminou
        hs, as_, c_over, c_under = row
        total = hs + as_
        won = int((total > ou_line) if p["selection"] == "over"
                  else (total < ou_line))
        clv = None
        if c_over and c_under:
            sh, _z, _o = shin_probabilities([c_over, c_under])
            p_close = sh[0] if p["selection"] == "over" else sh[1]
            clv = round(p["odd"] * float(p_close) - 1.0, 4)
        _append(results_path, {
            "settled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event_id": p["event_id"], "selection": p["selection"],
            "date": p["date"], "home": p["home"], "away": p["away"],
            "odd": p["odd"], "edge": p["edge"], "score": f"{hs}-{as_}",
            "won": won, "pnl": round((p["odd"] - 1.0) if won else -1.0, 3),
            "clv": clv, "trial": trial})
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
