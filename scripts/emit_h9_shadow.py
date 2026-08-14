"""emit_h9_shadow — funil de decisão da H9 (h9-ou25-prospective-replication).

Roda sobre jogos que ENTRARAM na janela de decisão do contrato (kickoff - 90min
- 15min de folga, até o apito), casando cotações já coletadas com fixtures do
Sofascore e chamando `src.research.h9_shadow.emit` — no máximo 1 pick por jogo,
idempotente por construção (`emit` recusa duplicata via o próprio ledger).

Duas fontes deliberadamente distintas:
    - Elo por time: VIVO, do cache do cron (`db.load_elo` — current_elo, a
      força de cada time É pra acompanhar o presente).
    - a/b/alpha/rho/max_goals: CONGELADOS no registro da trial em
      data/trials.json (params.model) — NUNCA o que `cron_update_models`
      tiver recalibrado depois do registro (2026-08-09). O cron reajusta
      esses 4 números toda vez que roda; ler o cache ao vivo aqui violaria
      "parameter_changes_create_new_trial": true sem abrir trial nova.

Cotações vêm de data/research/market_observations.jsonl, já coletadas pelo
job `brasileirao-market-research` (scripts/collect_market_research.py) — este
script NÃO bate na API, só consome o que já foi coletado. O bookmaker
aprovado vem do ledger de estabilidade vivo (mesma lógica de
scripts/prospective_readiness.py); sem casa estável, `emit` bloqueia sozinho.

Uso (Task Scheduler, cadência sugerida: a cada 15 minutos):
    python scripts/emit_h9_shadow.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry  # noqa: E402

from src import db, model  # noqa: E402
from src.data.bookmaker_odds import match_fixture  # noqa: E402
from src.data.bookmaker_stability import stability_report  # noqa: E402
from src.ingest import load_config  # noqa: E402
from src.research.h9_shadow import HORIZON, TRIAL, emit  # noqa: E402

TRIALS_PATH = ROOT / "data" / "trials.json"
STABILITY_PATH = ROOT / "data" / "research" / "bookmaker_stability.jsonl"
MARKET_OBS_PATH = ROOT / "data" / "research" / "market_observations.jsonl"
LEDGER_PATH = ROOT / "data" / "research" / "h9_shadow.jsonl"

WINDOW_SLACK = timedelta(minutes=15)
OU_LINE = 2.5


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def frozen_model_params(trials_path: Path = TRIALS_PATH) -> tuple[tuple[float, float, float, float], int]:
    trial = next((t for t in TrialRegistry(trials_path).load() if t["name"] == TRIAL), None)
    if trial is None:
        sys.exit(f"trial {TRIAL!r} não registrada — rode scripts/register_h9_prospective.py antes")
    m = trial["params"]["model"]
    return (float(m["a"]), float(m["b"]), float(m["alpha"]), float(m["rho"])), int(m["max_goals"])


def approved_bookmaker(stability_path: Path = STABILITY_PATH) -> str | None:
    return stability_report(stability_path).get("recommended_bookmaker")


def _upcoming_fixtures(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT event_id, home_team, away_team, kickoff_at FROM sofascore_matches "
        "WHERE home_score IS NULL AND kickoff_at IS NOT NULL"
    ).fetchall()
    return [
        {"event_id": eid, "home_team": home, "away_team": away, "kickoff_at": kickoff_at}
        for eid, home, away, kickoff_at in rows
    ]


def _in_decision_window(kickoff_at: str, now: datetime) -> bool:
    try:
        kickoff = datetime.fromisoformat(str(kickoff_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if kickoff.tzinfo is None:
        return False
    return kickoff - HORIZON - WINDOW_SLACK <= now < kickoff


def run(
    *,
    now: datetime | None = None,
    trials_path: Path = TRIALS_PATH,
    stability_path: Path = STABILITY_PATH,
    market_obs_path: Path = MARKET_OBS_PATH,
    ledger_path: Path = LEDGER_PATH,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    cfg = load_config()
    params, max_goals = frozen_model_params(trials_path)
    home_adv = float(cfg["elo"]["home_advantage"])
    bookmaker = approved_bookmaker(stability_path)

    conn = db.connect(str(db_path or (ROOT / cfg["database"])), read_only=True)
    try:
        elo = db.load_elo(conn)
        fixtures = _upcoming_fixtures(conn)
    finally:
        conn.close()
    if not elo:
        sys.exit("cache Elo vazio — rode python -m src.cron_update_models")

    in_window = {f["event_id"] for f in fixtures if _in_decision_window(f["kickoff_at"], now)}

    quotes_ou25 = [
        q
        for q in _load_jsonl(market_obs_path)
        if q.get("market") == f"ou{OU_LINE:g}" and q.get("selection") in ("over", "under")
    ]
    by_source_event: dict[str, dict[str, Any]] = {}
    for q in quotes_ou25:
        sid = q.get("source_event_id")
        if sid and sid not in by_source_event:
            by_source_event[sid] = q

    outcomes = []
    for source_event_id, representative in by_source_event.items():
        matched, status = match_fixture(representative, fixtures)
        if matched is None or matched["event_id"] not in in_window:
            continue
        home, away = matched["home_team"], matched["away_team"]
        if home not in elo or away not in elo:
            continue
        prediction_full = model.predict_match(elo[home], elo[away], params, home_adv, max_goals=max_goals)
        p_over = prediction_full["over"].get(OU_LINE)
        if p_over is None:
            continue
        prediction = {
            "event_id": source_event_id,
            "kickoff_at": matched["kickoff_at"],
            "predicted_at": now.isoformat(timespec="seconds"),
            "p_over": p_over,
        }
        result = emit(prediction=prediction, quotes=quotes_ou25, approved_bookmaker=bookmaker, ledger=ledger_path)
        outcomes.append({"sofascore_event_id": matched["event_id"], "home": home, "away": away, **result})
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    outcomes = run()
    summary = {
        "trial": TRIAL,
        "evaluated": len(outcomes),
        "emitted": sum(1 for o in outcomes if o["status"] == "EMITTED"),
        "outcomes": outcomes,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
