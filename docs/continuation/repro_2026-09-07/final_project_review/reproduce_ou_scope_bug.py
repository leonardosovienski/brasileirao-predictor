import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, "C:/Users/Superleo13/projetos/brasileirao-predictor")
from brasileirao_predictor.ingest_sofascore import parse_ou


def market(name, market_id, over, under):
    return {"marketName": name, "marketId": market_id, "choiceGroup": "2.5", "choices": [
        {"name": "Over", "decimalValue": over}, {"name": "Under", "decimalValue": under}
    ]}


cases = {
    "corners_before_goals": {"markets": [market("Total corners", 21, 4.0, 1.1), market("Match goals", 9, 1.8, 2.0)]},
    "first_half_only": {"markets": [market("1st half total goals", 9, 4.0, 1.1)]},
    "conflicting_goal_markets": {"markets": [market("Match goals", 9, 1.8, 2.0), market("Match goals", 9, 2.1, 1.7)]},
}
result = {key: {"actual_before_fix": list(parse_ou(value)), "payload": value} for key, value in cases.items()}
destination = ROOT / "ou_scope_bug_before.json"
if destination.exists():
    raise SystemExit("Do not overwrite the pre-fix reproduction")
destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v["actual_before_fix"] for k,v in result.items()}))
