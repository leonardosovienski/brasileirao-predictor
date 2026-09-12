"""Scores are counts: invalid input must not be silently recorded as a result."""

import pytest

from brasileirao_predictor.settle import grade, record_result


@pytest.mark.parametrize("score", [True, False, 1.9, -0.5, float("nan"), float("inf")])
def test_invalid_score_never_creates_result(tmp_path, score):
    destination = tmp_path / "results.jsonl"
    with pytest.raises(ValueError, match="placar"):
        record_result("A", "B", score, 0, path=destination, pred_path=tmp_path / "absent.jsonl")
    assert not destination.exists()


@pytest.mark.parametrize("score", [True, 1.9, -0.5])
def test_grading_validates_score_before_prediction(score):
    with pytest.raises(ValueError, match="placar"):
        grade({}, 0, score)


def test_missing_explicit_prediction_never_creates_result(tmp_path):
    destination = tmp_path / "results.jsonl"
    with pytest.raises(ValueError, match="prediction_id not found"):
        record_result("A", "B", 1, 0, prediction_id="absent", path=destination, pred_path=tmp_path / "absent.jsonl")
    assert not destination.exists()
