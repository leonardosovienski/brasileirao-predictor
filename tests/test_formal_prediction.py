import json

import pytest
from test_prediction_log import _PARAMS, _PRED
from test_prediction_protocol import NOW, candidate

from brasileirao_predictor.formal_prediction import prepare_context
from brasileirao_predictor.identity import CanonicalTeamResolver
from brasileirao_predictor.prediction_log import log_prediction
from brasileirao_predictor.settle import record_result


@pytest.fixture
def resolver(tmp_path):
    aliases = tmp_path / "aliases.json"
    teams = tmp_path / "teams.json"
    aliases.write_text(json.dumps({"mapping_version": "synthetic/1", "aliases": {}}))
    teams.write_text(json.dumps({"teams": {"A": {"slug": "a"}, "B": {"slug": "b"}}}))
    return CanonicalTeamResolver(aliases, teams)


def context(**changes):
    return {"readiness": candidate(home="a", away="b", **changes), "quote": None}


def test_formal_context_refuses_unknown_identity_or_wrong_date(resolver):
    with pytest.raises(ValueError, match="canonical"):
        prepare_context(context(), "unknown", "B", "2026-08-22", resolver)
    with pytest.raises(ValueError, match="kickoff date"):
        prepare_context(context(), "A", "B", "2026-08-23", resolver)


def test_quote_cannot_be_borrowed_from_another_event(resolver):
    item = context(odds_captured_at=NOW)
    item["quote"] = {"quote_id": "quote-1", "event_id": "other-match", "captured_at": NOW.isoformat(), "market": {}}
    with pytest.raises(ValueError, match="another event"):
        prepare_context(item, "A", "B", "2026-08-22", resolver)


def test_gate_blocks_before_model_is_called(resolver, monkeypatch):
    from brasileirao_predictor import predict

    monkeypatch.setattr(predict.model, "predict_match", lambda *args, **kwargs: pytest.fail("model ran"))
    with pytest.raises(ValueError, match="readiness blocked"):
        predict.show(
            "A",
            "B",
            {},
            {},
            {},
            False,
            match_date="2026-08-22",
            formal_context=context(capital_enabled=True),
            identity_resolver=resolver,
        )


def test_formal_settlement_selects_exact_prediction_among_repeated_matches(resolver, tmp_path):
    predictions = tmp_path / "predictions.jsonl"
    first = log_prediction(
        "A",
        "B",
        False,
        1500,
        1500,
        _PARAMS,
        _PRED,
        match_date="2026-08-22",
        path=predictions,
        formal_context=prepare_context(context(), "A", "B", "2026-08-22", resolver),
    )
    log_prediction("A", "B", False, 1500, 1500, _PARAMS, _PRED, match_date="2026-09-22", path=predictions)
    result = record_result(
        "A", "B", 1, 0, prediction_id=first["prediction_id"], pred_path=predictions, path=tmp_path / "result.jsonl"
    )
    assert result["match_date"] == "2026-08-22"
    assert result["event_id"] == "123"
    with pytest.raises(ValueError, match="not found"):
        record_result(
            "A", "B", 1, 0, prediction_id="missing", pred_path=predictions, path=tmp_path / "must-not-exist.jsonl"
        )
    assert not (tmp_path / "must-not-exist.jsonl").exists()
