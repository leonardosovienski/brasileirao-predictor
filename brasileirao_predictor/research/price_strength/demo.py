"""Small manufactured fixture set for exercising the pipeline, never evidence of edge."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from .dynamic_xg import DynamicXGConfig


def demo_inputs() -> dict:
    start = datetime(2030, 1, 1, 18, tzinfo=UTC)
    history, fixtures, quotes = [], [], []
    for i in range(24):
        kickoff = start + timedelta(days=i * 7)
        home, away = ("Synthetic A", "Synthetic B") if i % 2 == 0 else ("Synthetic B", "Synthetic A")
        match_id = f"synthetic-{i:02d}"
        history.append(
            {
                "match_id": match_id,
                "home_team": home,
                "away_team": away,
                "kickoff": kickoff.isoformat(),
                "completed_at": (kickoff + timedelta(hours=2)).isoformat(),
                "available_at": (kickoff + timedelta(hours=3)).isoformat(),
                "home_xg": 1.3 + (i % 3) * 0.2,
                "away_xg": 0.8 + (i % 4) * 0.2,
                "home_goals": 1 + (i % 2),
                "away_goals": i % 3,
            }
        )
        if i < 20:
            continue
        decision = kickoff - timedelta(hours=1)
        fixtures.append(
            {
                "match_id": match_id,
                "home_team": home,
                "away_team": away,
                "kickoff": kickoff.isoformat(),
                "decision_at": decision.isoformat(),
            }
        )
        for book in ("synthetic_reference", "synthetic_offer"):
            for market, odds in {
                "1x2": {"home": 2.2, "draw": 3.3, "away": 3.4},
                "ou25": {"over": 2.0 if book == "synthetic_reference" else 2.15, "under": 1.9},
                "btts": {"yes": 1.9, "no": 2.0},
            }.items():
                snapshot = {
                    "snapshot_id": f"{match_id}-{book}-{market}",
                    "source": "SYNTHETIC_FIXTURE",
                    "source_event_id": match_id,
                    "event_id": match_id,
                    "bookmaker": book,
                    "market": market,
                    "period": "FT",
                    "line": 2.5 if market == "ou25" else None,
                    "kickoff_at": kickoff.isoformat(),
                    "observed_at": (decision - timedelta(seconds=20)).isoformat(),
                    "available_at": (decision - timedelta(seconds=15)).isoformat(),
                    "received_at": (decision - timedelta(seconds=10)).isoformat(),
                    "status": "active",
                    "snapshot_scope": "complete_market",
                    "odds": odds,
                }
                snapshot["raw_payload_hash"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
                quotes.append(snapshot)
    config = DynamicXGConfig(window_matches=4, min_team_matches=2, min_calibration_matches=6)
    protocol = {
        "schema_version": "price-strength-study/1",
        "study_id": "synthetic-demonstration-v1",
        "data_kind": "SYNTHETIC_DEMONSTRATION",
        "hypothesis": "Exercise chronological xG and independent cross-book price comparison on manufactured inputs.",
        "stopping_rule": "Exactly the four supplied synthetic evaluation fixtures; no parameter search.",
        "training_end": (start + timedelta(days=11 * 7 + 1)).isoformat(),
        "calibration_end": (start + timedelta(days=19 * 7 + 1)).isoformat(),
        "evaluation_start": fixtures[0]["decision_at"],
        "evaluation_end": fixtures[-1]["decision_at"],
        "report_as_of": (start + timedelta(days=24 * 7)).isoformat(),
        "xg_config": asdict(config),
        "price_policy": {
            "reference_books": ["synthetic_reference"],
            "max_age_seconds": 120,
            "max_skew_seconds": 30,
            "cost_per_unit": 0.02,
            "commission_on_profit": 0.0,
            "min_reference_books": 1,
            "min_ev": 0.0,
            "max_ev": 0.15,
        },
    }
    return {"protocol.json": protocol, "history.jsonl": history, "fixtures.jsonl": fixtures, "quotes.jsonl": quotes}
