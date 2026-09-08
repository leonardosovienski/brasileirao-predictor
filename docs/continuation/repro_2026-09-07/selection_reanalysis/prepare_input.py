"""Prepare already consumed 2021–2025 history; read-only SQL boundary."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")

plan = {
    "id": "DISCOVERY-SELECTIVE-MULTIMARKET-20260907",
    "mode": "CONTRAFACTUAL_WITH_RETROSPECTIVE_PRICES",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "status": "EXPLORATORY_NOT_A_CONFIRMATORY_TRIAL",
    "question": "Does selective abstention and cross-market choice improve the observed historical decisions?",
    "period": ["2021-01-01", "2025-12-31"],
    "decision_evaluation_years": [2023, 2024, 2025],
    "markets": ["1x2", "ou25", "btts"],
    "decision_before_kickoff_hours": 1,
    "historical_result_buffer_hours": 48,
    "forecast_min_history": 200,
    "forecast_refit_every": 100,
    "max_goals": 12,
    "calibration": {
        "frequency": "calendar_month; all training before first decision cutoff of month",
        "min_games_per_market": 200,
        "market_reference": "proportional devig of same complete retrospective vector",
        "learned_blend": "Brier optimum, weight clipped to [0,1], learned on past only",
        "residual": "softmax(log(q) + w*(log(p)-log(q)) + class_bias), L2 mean penalty 0.01, w in [-1,1], each bias in [-0.35,0.35], final class bias fixed zero",
    },
    "odds_gates": {"1x2": [1.05,20.0], "ou25": [1.20,5.0], "btts": [1.20,5.0], "complete_vector_overround": [1.0,1.30]},
    "additional_cost_per_unit": 0.02,
    "net_ev_threshold": 0.02,
    "conservative_probability_subtraction": 0.03,
    "policies": [
        "no_bet", "confidence_60", "confidence_70", "raw_ev",
        "half_market_blend", "learned_market_blend", "calibrated_residual",
        "conservative_residual", "residual_1x2_only", "residual_ou25_only",
        "residual_btts_only", "hash_placebo",
    ],
    "max_unit_bets_per_event": 1,
    "tie_break": "score descending, market name ascending, selection index ascending",
    "stress": {"additional_cost_rates": [0.0,0.02,0.05], "proportional_odds_reduction": [0.0,0.01,0.03]},
    "bootstrap": {"scheme": "noncircular moving blocks of 4 consecutive ISO calendar weeks; all arms shared", "replicates": 2000, "seed": 20260907, "interval": "descriptive percentile 95%; not selection-adjusted; no confirmation"},
    "stopping": "Publish all frozen arms and yearly results once; no threshold search after results; no capital promotion.",
    "search_history": "Existing project search includes 29 ledger trials and extensive OU25 threshold exploration; new namespace does not reset multiplicity. Historical 2024/2025 already examined.",
    "limitations": ["Odds are retrospective aggregates without named bookmaker or observed_at; no executable profit or CLV claim", "48h result buffer is an assumption, not proof of historical publication/ingestion times", "Hypothesis design itself informed by already examined historical results"],
}
plan_path = ROOT / "analysis_plan.json"
if plan_path.exists():
    raise SystemExit("Plan already frozen; do not silently overwrite")
plan_raw = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode()
plan_path.write_bytes(plan_raw)
(ROOT / "config_frozen.yaml").write_bytes((REPO / "config.yaml").read_bytes())

conn = sqlite3.connect((REPO / "data" / "matches.db").as_uri() + "?mode=ro", uri=True)
conn.execute("PRAGMA query_only=ON")
conn.row_factory = sqlite3.Row
rows = conn.execute("""
SELECT m.date, m.home_team, m.away_team, m.home_score, m.away_score,
       s.kickoff_at, m.tournament, m.city, m.neutral, m.event_id,
       s.home_xg, s.away_xg, s.odds_home, s.odds_draw, s.odds_away,
       s.odds_over, s.odds_under, s.odds_btts_yes, s.odds_btts_no
FROM matches m JOIN sofascore_matches s ON s.event_id=m.event_id
WHERE m.date >= '2021-01-01' AND m.date < '2026-01-01'
  AND s.date >= '2021-01-01' AND s.date < '2026-01-01'
  AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL
ORDER BY s.kickoff_at, m.event_id
""").fetchall()
conn.close()
events = []
for row in rows:
    if row["kickoff_at"] is None:
        raise ValueError("Missing kickoff: never invent intraday ordering")
    events.append({
        "event_id": row["event_id"], "home": row["home_team"], "away": row["away_team"],
        "kickoff": row["kickoff_at"], "date": row["date"], "tournament": row["tournament"],
        "city": row["city"], "neutral": int(row["neutral"] or 0),
        "result": {"home_goals": row["home_score"], "away_goals": row["away_score"], "home_xg": row["home_xg"], "away_xg": row["away_xg"]},
        "odds": {"1x2": [row["odds_home"],row["odds_draw"],row["odds_away"]], "ou25": [row["odds_over"],row["odds_under"]], "btts": [row["odds_btts_yes"],row["odds_btts_no"]]},
    })
assert len(events) == len({row["event_id"] for row in events})
assert all("2021-01-01" <= row["date"] <= "2025-12-31" for row in events)
raw = (json.dumps(events, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
(ROOT / "historical_input.json").write_bytes(raw)
manifest = {"input_events": len(events), "input_sha256": hashlib.sha256(raw).hexdigest(), "plan_sha256": hashlib.sha256(plan_raw).hexdigest(), "config_sha256": hashlib.sha256((ROOT / "config_frozen.yaml").read_bytes()).hexdigest(), "sql_boundary": "2021 <= year < 2026, both joined tables", "scientific_runtime_mutated": False}
(ROOT / "input_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest))
