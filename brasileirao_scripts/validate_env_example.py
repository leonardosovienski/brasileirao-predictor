"""Fail when .env.example drifts from the operational settings schema."""

from pathlib import Path

from dotenv import dotenv_values

from brasileirao_predictor.settings import Settings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    values = {key: value for key, value in dotenv_values(root / ".env.example").items() if value}
    Settings.model_validate(values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
