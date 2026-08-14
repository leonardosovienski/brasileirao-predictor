"""settle_h9_shadow — liquida decisões H9 abertas contra o placar final e o
fechamento (mesma casa, última cotação pré-apito).

Re-resolve a identidade da mesma forma que `emit_h9_shadow.py` a estabeleceu:
o ledger H9 guarda `event_id` no espaço da COTAÇÃO (source_event_id do
provider), não o event_id numérico do Sofascore — então usa a primeira
cotação já vista daquele source_event_id em market_observations.jsonl (tem
home_team/away_team/kickoff_at) e `match_fixture` pra achar o placar. Sem
histórico de cotação daquele evento, ou sem fixture resolvida, a decisão
fica pendente (não é erro — só falta dado).

`market_observations.jsonl` serve tanto pra decisão quanto pra fechamento:
scripts/record_h9_closing_snapshots.py amostra com mais frequência perto do
apito na MESMA fonte; `h9_shadow.settle()` já escolhe a última cotação válida
pré-apito entre todas as linhas daquele evento/casa/mercado/seleção.

Uso (Task Scheduler, após cada ingestão de resultados):
    python scripts/settle_h9_shadow.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import db  # noqa: E402
from src.data.bookmaker_odds import match_fixture  # noqa: E402
from src.ingest import load_config  # noqa: E402
from src.research.h9_shadow import settle  # noqa: E402

MARKET_OBS_PATH = ROOT / "data" / "research" / "market_observations.jsonl"
LEDGER_PATH = ROOT / "data" / "research" / "h9_shadow.jsonl"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _open_decisions(ledger_path: Path) -> list[dict[str, Any]]:
    rows = _load_jsonl(ledger_path)
    settled_ids = {r["decision_id"] for r in rows if r.get("kind") == "settlement"}
    return [r for r in rows if r.get("kind") == "decision" and r["decision_id"] not in settled_ids]


def run(
    *,
    now: datetime | None = None,
    db_path: Path | None = None,
    market_obs_path: Path = MARKET_OBS_PATH,
    ledger_path: Path = LEDGER_PATH,
) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    open_decisions = _open_decisions(ledger_path)
    if not open_decisions:
        return []

    quotes_all = _load_jsonl(market_obs_path)
    quote_by_event: dict[str, dict[str, Any]] = {}
    for q in quotes_all:
        sid = q.get("source_event_id")
        if sid and sid not in quote_by_event:
            quote_by_event[sid] = q

    cfg = load_config()
    conn = db.connect(str(db_path or (ROOT / cfg["database"])), read_only=True)
    try:
        all_rows = conn.execute(
            "SELECT event_id, home_team, away_team, kickoff_at, home_score, away_score FROM sofascore_matches"
        ).fetchall()
    finally:
        conn.close()
    fixtures = [{"event_id": r[0], "home_team": r[1], "away_team": r[2], "kickoff_at": r[3]} for r in all_rows]
    scores = {r[0]: (r[4], r[5]) for r in all_rows}

    outcomes = []
    for decision in open_decisions:
        event_id = decision["event_id"]
        representative = quote_by_event.get(event_id)
        if representative is None:
            outcomes.append({"event_id": event_id, "status": "QUOTE_HISTORY_MISSING"})
            continue
        matched, status = match_fixture(representative, fixtures)
        if matched is None:
            outcomes.append({"event_id": event_id, "status": "FIXTURE_NOT_RESOLVED", "reason": status})
            continue
        home_score, away_score = scores.get(matched["event_id"], (None, None))
        if home_score is None or away_score is None:
            outcomes.append({"event_id": event_id, "status": "PENDING_RESULT"})
            continue
        closing_quotes = [q for q in quotes_all if q.get("source_event_id") == event_id]
        try:
            result = settle(
                event_id=event_id,
                home_goals=home_score,
                away_goals=away_score,
                result_published_at=now.isoformat(timespec="seconds"),
                closing_quotes=closing_quotes,
                ledger=ledger_path,
                recorded_at=now.isoformat(timespec="seconds"),
            )
        except ValueError as exc:
            result = {"status": "SETTLEMENT_BLOCKED", "reason": str(exc)}
        outcomes.append({"event_id": event_id, **result})
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    outcomes = run()
    summary = {
        "evaluated": len(outcomes),
        "settled": sum(1 for o in outcomes if o["status"] == "SETTLED"),
        "outcomes": outcomes,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
