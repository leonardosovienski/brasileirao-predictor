import sqlite3

import pytest

from brasileirao_predictor import db, model, predict, prediction_log


def test_prediction_database_is_physically_read_only(tmp_path, monkeypatch):
    path = tmp_path / "matches.db"
    conn = db.connect(str(path))
    db.save_elo(conn, [("A", 1500), ("B", 1500)])
    db.save_params(conn, 0.2, 0.7, 0.1, -0.03, 0, "signature", "2024-01-01T00:00:00Z")
    conn.close()
    monkeypatch.setattr("brasileirao_predictor.cron_update_models.cache_is_current", lambda *a: True)
    consumer, _, _ = predict.build({"database": str(path)})
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        consumer.execute("DELETE FROM current_elo")
    consumer.close()


@pytest.mark.parametrize(
    "params", [(0.2, 0.7, 0.1, -0.03, 0.5), {"a": 0.2, "b": 0.7, "alpha": 0.1, "rho": -0.03, "theta": 0.5}]
)
def test_extended_model_parameters_can_be_audited_without_loss(tmp_path, params):
    prediction = model.predict_match(1500, 1500, params)
    row = prediction_log.log_prediction(
        "A", "B", True, 1500, 1500, params, prediction, path=tmp_path / "predictions.jsonl"
    )
    assert row["params"]["theta"] == 0.5
