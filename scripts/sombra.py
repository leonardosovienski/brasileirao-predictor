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


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def _append(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def capture(cfg, conn) -> int:
    bt = cfg["backtest"]
    min_edge, max_edge = float(bt["min_edge"]), float(bt["max_edge"])
    ou_line = float(bt.get("over_under_line", 2.5))
    max_goals = cfg["model"]["max_goals"]
    home_adv = float(cfg["elo"]["home_advantage"])

    elo = db.load_elo(conn)
    prow = db.load_params(conn)
    if not elo or not prow:
        sys.exit("cache vazio — rode python -m src.cron_update_models")
    params = (prow[0], prow[1], prow[2], prow[3])

    ja = {(p["event_id"], p["selection"]) for p in _load_jsonl(PICKS)}
    now = datetime.now(timezone.utc)
    hoje = now.strftime("%Y-%m-%d")

    n = 0
    rows = conn.execute(
        "SELECT event_id, date, home_team, away_team, odds_over, odds_under "
        "FROM sofascore_matches WHERE home_score IS NULL AND date >= ? "
        "AND odds_over IS NOT NULL AND odds_under IS NOT NULL "
        "ORDER BY date", (hoje,)).fetchall()
    for eid, d, home, away, o_over, o_under in rows:
        if home not in elo or away not in elo:
            continue
        r = model.predict_match(elo[home], elo[away], params, home_adv,
                                max_goals=max_goals)
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
            _append(PICKS, {
                "captured_at": now.isoformat(timespec="seconds"),
                "event_id": eid, "date": d, "home": home, "away": away,
                "market": f"ou{ou_line}", "selection": sel,
                "odd": round(odd, 3), "edge": round(edge, 4),
                "model_prob": round(p_m, 4),
                "lambda_home": round(r["lambda_a"], 3),
                "lambda_away": round(r["lambda_b"], 3),
                "trial": "h3-ou25-sombra-2026"})
            ja.add((eid, sel))
            n += 1
            print(f"  pick: {d} {home} x {away} — {sel} {ou_line} @{odd} "
                  f"(edge {edge:+.1%})")
    return n


def settle(cfg, conn) -> int:
    ou_line = float(cfg["backtest"].get("over_under_line", 2.5))
    liquidados = {(r["event_id"], r["selection"]) for r in _load_jsonl(RESULTS)}
    n = 0
    for p in _load_jsonl(PICKS):
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
        _append(RESULTS, {
            "settled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event_id": p["event_id"], "selection": p["selection"],
            "date": p["date"], "home": p["home"], "away": p["away"],
            "odd": p["odd"], "edge": p["edge"], "score": f"{hs}-{as_}",
            "won": won, "pnl": round((p["odd"] - 1.0) if won else -1.0, 3),
            "clv": clv, "trial": "h3-ou25-sombra-2026"})
        n += 1
        print(f"  settle: {p['home']} {hs}x{as_} {p['away']} — "
              f"{p['selection']} {'GANHOU' if won else 'perdeu'}"
              + (f" | CLV {clv:+.2%}" if clv is not None else ""))
    return n


def report() -> None:
    res = _load_jsonl(RESULTS)
    abertos = len(_load_jsonl(PICKS)) - len(res)
    print(f"H3 modo sombra — {len(res)} liquidados, {abertos} em aberto")
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
    print("  (decisão da H3 = IC do core sobre esta população quando n ≥ 100; "
          "critério no trials.json)")


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
    else:
        n = settle(cfg, conn)
        print(f"{n} pick(s) liquidados em {RESULTS.name}")


if __name__ == "__main__":
    main()
