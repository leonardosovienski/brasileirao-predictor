from scripts import prospective_readiness


def test_readiness_fails_closed_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.setattr(prospective_readiness, "ROOT", tmp_path)
    result = prospective_readiness.report()
    assert result["h9_can_emit"] is False
    assert result["capital_enabled"] is False
    assert result["bookmaker_persistence_gate"] == "PENDING"
    assert result["collection_runs"] == 0


def test_readiness_does_not_require_unrelated_v3_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("ODDS_API_KEY", "configured")
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    monkeypatch.setattr(prospective_readiness, "ROOT", tmp_path)

    result = prospective_readiness.report()

    assert result["odds_api_configured"] is True
    assert result["api_football_configured"] is False
    assert result["h9_can_emit"] is False  # demais gates continuam fail-closed
