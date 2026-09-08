"""Read-only presence and numeric quality; no imputation or provenance claim."""

import sqlite3
from typing import Any

from .xg_quality import classify_xg_pair, is_numeric_xg

_COUNTS = (
    "played",
    "home_xg_present",
    "away_xg_present",
    "paired_xg_present",
    "home_xg_numeric",
    "away_xg_numeric",
    "paired_xg_numeric",
    "zero_pair_unattested",
    "numeric_nonzero_pair",
    "missing_pair",
    "partial_pair",
    "invalid_pair",
)


def _summary(counts: dict[str, int]) -> dict[str, Any]:
    played = counts["played"]
    present = counts["paired_xg_present"]
    return {
        **counts,
        # Backward-compatible aliases mean presence only, as in schema v1.
        "home_xg_valid": counts["home_xg_present"],
        "away_xg_valid": counts["away_xg_present"],
        "paired_xg_valid": present,
        "paired_coverage": present / played if played else 0.0,
        "paired_numeric_coverage": counts["paired_xg_numeric"] / played if played else 0.0,
        "numeric_nonzero_pair_coverage": counts["numeric_nonzero_pair"] / played if played else 0.0,
        "all_reported_pairs_zero": bool(present and counts["zero_pair_unattested"] == present),
    }


def xg_coverage(conn: sqlite3.Connection) -> dict[str, Any]:
    """Inspect a supplied connection. Presence and finite numbers are not proof of source coverage."""
    rows = conn.execute(
        """SELECT COALESCE(season, 'unknown'), home_xg, away_xg
           FROM sofascore_matches
           WHERE home_score IS NOT NULL AND away_score IS NOT NULL"""
    )
    seasons: dict[str, dict[str, int]] = {}
    for season, home, away in rows:
        counts = seasons.setdefault(str(season), dict.fromkeys(_COUNTS, 0))
        category = classify_xg_pair(home, away)
        home_numeric, away_numeric = is_numeric_xg(home), is_numeric_xg(away)
        updates = {
            "played": 1,
            "home_xg_present": home is not None,
            "away_xg_present": away is not None,
            "paired_xg_present": home is not None and away is not None,
            "home_xg_numeric": home_numeric,
            "away_xg_numeric": away_numeric,
            "paired_xg_numeric": home_numeric and away_numeric,
            "zero_pair_unattested": category == "ZERO_PAIR_UNATTESTED",
            "numeric_nonzero_pair": category == "NUMERIC_PAIR",
            "missing_pair": category == "MISSING_PAIR",
            "partial_pair": category == "PARTIAL_PAIR",
            "invalid_pair": category == "INVALID_PAIR",
        }
        for key, value in updates.items():
            counts[key] += int(value)
    return {
        "schema_version": "xg-missingness-audit/v2",
        "source_provenance_attested": False,
        "semantics": {
            "observed_xg": "reported presence only; source and availability are not attested",
            "legacy_valid_aliases": "*_xg_valid and paired_coverage mean v1 presence counts, not certified quality",
            "numeric_xg": "finite nonnegative numeric value, including zero; not proof of provider coverage",
            "zero_pair_unattested": "both values exactly zero; ambiguous until checked against source evidence",
            "numeric_nonzero_pair": "numeric pair with at least one positive value; still not authenticated",
            "legacy_xg_model_fallback": "missing provider xG replaced by realized goals in frozen xg_model lineage",
            "feature_builder_policy": "missing xG remains None and is never zero-imputed",
        },
        "seasons": [{"season": key, **_summary(value)} for key, value in sorted(seasons.items())],
        "total": _summary({key: sum(counts[key] for counts in seasons.values()) for key in _COUNTS}),
    }
