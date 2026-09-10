import json
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_scripts.settle_live_prediction import append_settlement, build_settlement


def inputs():
    return (
        {
            "prediction_id": "synthetic-1",
            "source_event_id": "123",
            "prediction": {"p_home": 0.5, "p_draw": 0.3, "p_away": 0.2},
        },
        {"id": 123, "status": {"type": "finished"}, "homeScore": {"current": 2}, "awayScore": {"current": 1}},
        datetime(2024, 1, 1, tzinfo=UTC),
    )


def test_rejects_wrong_event():
    p, e, at = inputs()
    e["id"] = 124
    with pytest.raises(ValueError, match="identity"):
        build_settlement(p, e, at)


@pytest.mark.parametrize("value", [True, -1])
def test_rejects_invalid_score(value):
    p, e, at = inputs()
    e["homeScore"]["current"] = value
    with pytest.raises(ValueError, match="score"):
        build_settlement(p, e, at)


@pytest.mark.parametrize("value", [float("nan"), -0.1, 1.1, True, 0.2])
def test_rejects_invalid_probability_vector(value):
    p, e, at = inputs()
    p["prediction"]["p_home"] = value
    with pytest.raises(ValueError, match="probab"):
        build_settlement(p, e, at)


def test_retry_retains_first_receipt_and_changed_result_conflicts(tmp_path):
    p, e, at = inputs()
    path = tmp_path / "synthetic.jsonl"
    row = build_settlement(p, e, at)
    assert append_settlement(path, row)
    original = path.read_bytes()
    assert not append_settlement(path, build_settlement(p, e, at + timedelta(minutes=1)))
    assert path.read_bytes() == original
    other = deepcopy(e)
    other["awayScore"]["current"] = 3
    with pytest.raises(ValueError, match="conflict"):
        append_settlement(path, build_settlement(p, other, at))


def test_writer_lock_is_respected(tmp_path):
    from brasileirao_predictor.bet_log import _writer_lock

    path = tmp_path / "synthetic.jsonl"
    with _writer_lock(path), pytest.raises(BlockingIOError):
        append_settlement(path, build_settlement(*inputs()))


def test_cli_retry_reports_persisted_receipt_in_stdout_and_run_log(tmp_path, monkeypatch, capsys):
    from brasileirao_scripts import settle_live_prediction as cli

    prediction, event, at = inputs()
    predictions = tmp_path / "predictions.jsonl"
    settlements = tmp_path / "settlements.jsonl"
    run_log = tmp_path / "run.jsonl"
    predictions.write_text(json.dumps(prediction) + "\n", encoding="utf-8")
    first = build_settlement(prediction, event, at)
    assert append_settlement(settlements, first)
    original = settlements.read_bytes()

    class Client:
        def _get(self, *args, **kwargs):
            return {"event": event}

    monkeypatch.setattr(cli, "Sofascore", lambda **kwargs: Client())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "settlement",
            prediction["prediction_id"],
            "--predictions",
            str(predictions),
            "--settlements",
            str(settlements),
            "--run-log",
            str(run_log),
        ],
    )
    cli.main(now=lambda: at + timedelta(minutes=5))
    reported = json.loads(capsys.readouterr().out)
    assert reported == {"settlement_appended": False, **first}
    assert json.loads(run_log.read_text(encoding="utf-8")) == reported
    assert settlements.read_bytes() == original
