"""Validated operational settings; scientific configuration remains in config.yaml."""
# pyright: strict

from pathlib import Path, PurePosixPath

from pydantic import AnyUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    REDIS_URL: AnyUrl
    SPORTS_DB_PATH: Path
    MARKET_DB_PATH: Path
    VORP_ARTIFACT_PATH: Path
    TITULARIDADE_PATH: Path
    RUNTIME_DIR: Path
    LOG_LEVEL: str = "INFO"
    THE_ODDS_API_KEY: str | None = None
    API_FOOTBALL_KEY: str | None = None
    SPORTMONKS_API_TOKEN: str | None = None
    EXCHANGE_WEBSOCKET_URL: AnyUrl | None = None
    EXCHANGE_API_KEY: str | None = None

    @field_validator("REDIS_URL")
    @classmethod
    def redis_scheme(cls, value: AnyUrl) -> AnyUrl:
        if value.scheme not in {"redis", "rediss"}:
            raise ValueError("REDIS_URL must use redis:// or rediss://")
        return value

    @field_validator(
        "SPORTS_DB_PATH",
        "MARKET_DB_PATH",
        "VORP_ARTIFACT_PATH",
        "TITULARIDADE_PATH",
        "RUNTIME_DIR",
        mode="before",
    )
    @classmethod
    def absolute_path(cls, value: object) -> object:
        if not Path(str(value)).is_absolute() and not PurePosixPath(str(value)).is_absolute():
            raise ValueError("production paths must be absolute")
        return value

    @model_validator(mode="after")
    def isolated_databases(self) -> "Settings":
        if self.SPORTS_DB_PATH.resolve() == self.MARKET_DB_PATH.resolve():
            raise ValueError("SPORTS_DB_PATH and MARKET_DB_PATH must be isolated")
        return self
