from pathlib import Path

import pytest
from pydantic import ValidationError

from brasileirao_predictor.settings import Settings


def _valid(tmp_path: Path) -> dict[str, object]:
    return {
        "REDIS_URL": "redis://redis:6379/0",
        "SPORTS_DB_PATH": tmp_path / "sports.db",
        "MARKET_DB_PATH": tmp_path / "market.db",
        "VORP_ARTIFACT_PATH": tmp_path / "vorp.json",
        "TITULARIDADE_PATH": tmp_path / "titularidade.json",
        "RUNTIME_DIR": tmp_path / "runtime",
    }


def test_settings_require_absolute_isolated_paths(tmp_path: Path) -> None:
    settings = Settings(**_valid(tmp_path))
    assert settings.SPORTS_DB_PATH.is_absolute()
    with pytest.raises(ValidationError, match="must be isolated"):
        Settings(**(_valid(tmp_path) | {"MARKET_DB_PATH": tmp_path / "sports.db"}))
    with pytest.raises(ValidationError, match="absolute"):
        Settings(**(_valid(tmp_path) | {"RUNTIME_DIR": Path("relative/runtime")}))


def test_settings_require_redis_url(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    values = _valid(tmp_path)
    values.pop("REDIS_URL")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
    with pytest.raises(ValidationError, match="redis://"):
        Settings(**(_valid(tmp_path) | {"REDIS_URL": "http://redis:6379"}))
