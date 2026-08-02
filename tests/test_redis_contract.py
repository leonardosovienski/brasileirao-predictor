import json
from pathlib import Path

from src import kernel_daemon


def test_shared_schema_is_versioned_and_correlated() -> None:
    schema = json.loads((Path(__file__).parents[1] / "contracts" / "redis-protocol-v1.schema.json").read_text())
    required = set(schema["required"])
    assert {"protocol_version", "job_id", "run_id", "match_id", "idempotency_key"} <= required
    assert schema["properties"]["protocol_version"]["const"] == "brasileirao.redis/1"


def test_golden_pricing_grid_is_preserved() -> None:
    grid = kernel_daemon._compute_grid_jit(1.5, 1.1, 0.1, -0.05, 12)
    odds = kernel_daemon._fair_odds_from_grid(grid)
    assert odds == {"1": 2.2047, "X": 3.7475, "2": 3.5767, "o25": 2.1183, "u25": 1.8942}
