import io
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml
from predictor_core.kernel.obs import emit_event

from . import db
from .net import retry
from .obs import get_logger, setup_logging

log = get_logger()
_DOMAIN = "brasileirao"

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


@retry(attempts=3, base_delay=2.0)
def _download(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8")


def fetch_csv(cfg: dict) -> pd.DataFrame:
    try:
        raw = _download(cfg["source"]["url"])
        df = pd.read_csv(io.StringIO(raw))
        log.info("fonte remota: %d linhas", len(df))
    except Exception as e:
        fallback = ROOT / cfg["source"]["local_fallback"]
        log.warning("fonte remota indisponível (%s); usando fallback %s", e, fallback)
        df = pd.read_csv(fallback)
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["date", "home_team", "away_team"])
    df["neutral"] = df["neutral"].astype(str).str.upper().isin(["TRUE", "1"]).astype(int)
    for col in ("home_score", "away_score"):
        numeric = cast(pd.Series, pd.to_numeric(cast(pd.Series, df[col]), errors="coerce"))
        df[col] = numeric.astype("Int64")
    df = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="last")
    return cast(
        pd.DataFrame,
        df[
            [
                "date",
                "home_team",
                "away_team",
                "home_score",
                "away_score",
                "tournament",
                "city",
                "country",
                "neutral",
            ]
        ],
    )


def run() -> None:
    cfg = load_config()
    setup_logging(ROOT / "data")
    t0 = time.monotonic()
    df = normalize(fetch_csv(cfg))
    conn = db.connect(str(ROOT / cfg["database"]))
    rows = []
    for values in df.itertuples(index=False, name=None):
        date_, home, away, home_score, away_score, tournament, city, country, neutral = cast(tuple[Any, ...], values)
        rows.append(
            (
                date_,
                home,
                away,
                None if pd.isna(home_score) else int(home_score),
                None if pd.isna(away_score) else int(away_score),
                tournament,
                city,
                country,
                int(neutral),
            )
        )
    db.upsert_matches(conn, rows)
    played = conn.execute("SELECT COUNT(*) FROM matches WHERE home_score IS NOT NULL").fetchone()[0]
    fixtures = conn.execute("SELECT COUNT(*) FROM matches WHERE home_score IS NULL").fetchone()[0]
    log.info("banco: %d partidas jogadas, %d fixtures futuros", played, fixtures)
    emit_event(
        _DOMAIN,
        "ingest_done",
        metrics={
            "records": float(len(rows)),
            "played": float(played),
            "fixtures": float(fixtures),
            "duration_sec": round(time.monotonic() - t0, 2),
        },
        metadata={"source": "results_csv"},
    )


if __name__ == "__main__":
    sys.exit(run())
