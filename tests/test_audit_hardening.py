import importlib

import pytest

from brasileirao_scripts import evaluate_h14_prospective as h14
from brasileirao_scripts import evaluate_h15_prospective as h15
from brasileirao_scripts.prospective_metrics import holm_family


@pytest.mark.parametrize("prefix", ["h14", "h15"])
def test_duplicate_events_cannot_inflate_sample(prefix, tmp_path, monkeypatch):
    cases = importlib.import_module(f"test_evaluate_{prefix}_prospective")
    database, ledger = cases._seed_db_and_ledger(tmp_path, n=cases.MIN_N)
    first = ledger.read_text(encoding="utf-8").splitlines()[0]
    with ledger.open("a", encoding="utf-8") as stream:
        stream.write(first + "\n")
    registry = tmp_path / "trials.json"
    cases._trials_json(registry)
    def forbidden(*args):
        raise AssertionError("No metric permitted for a duplicated ledger")
    monkeypatch.setattr(cases.job, "_paired_gain", forbidden)
    with pytest.raises(cases.job.EvaluationBlocked, match="Duplicate"):
        cases.job.evaluate(trials_path=registry, ledger_path=ledger,
                           db_path=database, reports_dir=tmp_path / "reports")


@pytest.mark.parametrize("job", [h14, h15])
@pytest.mark.parametrize("interval", [None, [], [1], [1, 2, 3], ["0", 1], [True, 1], [0, float("inf")]])
def test_invalid_primary_cannot_crash_or_approve(job, interval):
    assert job._verdict({"ci95": interval}, {})[0] == "inconclusiva"


@pytest.mark.parametrize("job", [h14, h15])
def test_partially_recorded_score_is_not_completed(job):
    import sqlite3

    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE sofascore_matches(event_id INTEGER, home_score INTEGER, away_score INTEGER)")
        db.executemany("INSERT INTO sofascore_matches VALUES (?, ?, ?)", [(1, 2, None), (2, None, 1), (3, 0, 0)])
        assert job._results_by_event(db) == {3: (0, 0)}


@pytest.mark.parametrize("alpha", [None, "0.05", True, float("nan"), -0.1, 1])
def test_invalid_alpha_is_a_validation_error(alpha):
    with pytest.raises(ValueError):
        holm_family({"A": 0.01, "B": 0.04}, expected_ids=("A", "B"), alpha=alpha)
