"""Annual OU2.5 ledgers under the frozen v2 governance contract.

The governed policy is NO_BET until prospective A1 gates are met.  For each
season this script also reports the same non-tuned counterfactual baseline:
one unit on whichever OU2.5 side has the largest sports-model gross EV.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from scripts.research_ou25_nested_replay import ROOT, load_rows
from src.research.ou25_nested_replay import (
    _metrics,
    _normal_p_greater,
    devig_proportional,
    file_sha256,
    holm_adjust,
)

SEASONS = tuple(str(year) for year in range(2021, 2027))


def _valid_price_pair(pair: tuple[float, float] | list[float]) -> bool:
    """Reject obvious placeholder/corrupt totals quotes before economics."""
    over, under = map(float, pair)
    return 1.20 <= over <= 5.00 and 1.20 <= under <= 5.00 and 1.00 <= (1 / over + 1 / under) <= 1.30


def _annual_baseline(rows: list[dict], season: str, seed: int) -> tuple[list[dict], dict]:
    picks = []
    model_errors = []
    market_errors = []
    for row in rows:
        if str(row["season"]) != season:
            continue
        if not _valid_price_pair(row["offered_odds_ou25"]):
            continue
        over_odd, under_odd = map(float, row["offered_odds_ou25"])
        market_over, _market_under = devig_proportional(over_odd, under_odd)
        actual = int(row["actual_over"])
        model_errors.append((float(row["p_over"]) - actual) ** 2)
        market_errors.append((market_over - actual) ** 2)
        choices = (
            (float(row["p_over"]) * over_odd - 1, "over", over_odd),
            ((1 - float(row["p_over"])) * under_odd - 1, "under", under_odd),
        )
        gross_ev, side, odd = max(choices)
        won = bool(row["actual_over"]) == (side == "over")
        closing = row.get("closing_odds_ou25")
        close_probability = None
        if closing and all(closing):
            close_probability = devig_proportional(*map(float, closing))[0 if side == "over" else 1]
        picks.append(
            {
                "event_id": row["event_id"],
                "kickoff_at": row["kickoff_at"],
                "season": season,
                "side": side,
                "odd": odd,
                "model_probability": float(row["p_over"] if side == "over" else 1 - row["p_over"]),
                "market_probability_devig": market_over if side == "over" else 1 - market_over,
                "gross_ev": gross_ev,
                "won": won,
                "profit": odd - 1 if won else -1.0,
                "clv": odd * close_probability - 1 if close_probability is not None else None,
            }
        )
    metrics = _metrics(picks, seed=seed)
    metrics["profit_units"] = sum(float(pick["profit"]) for pick in picks)
    metrics["model_brier"] = sum(model_errors) / len(model_errors) if model_errors else None
    metrics["market_devig_brier"] = sum(market_errors) / len(market_errors) if market_errors else None
    return picks, metrics


def _coverage() -> dict[str, dict]:
    output = {season: {"finished_games": 0, "flat_ou25_pairs": 0} for season in SEASONS}
    with sqlite3.connect(f"file:{ROOT / 'data' / 'matches.db'}?mode=ro", uri=True) as connection:
        for season, finished, priced in connection.execute(
            "SELECT season, SUM(home_score IS NOT NULL), "
            "SUM(home_score IS NOT NULL AND odds_over IS NOT NULL AND odds_under IS NOT NULL) "
            "FROM sofascore_matches WHERE superseded_by_event_id IS NULL GROUP BY season"
        ):
            if str(season) in output:
                output[str(season)] = {"finished_games": int(finished or 0), "flat_ou25_pairs": int(priced or 0)}
    return output


def main() -> None:
    output = ROOT / "data" / "research" / "ou25_annual_2021_2026"
    output.mkdir(parents=True, exist_ok=True)
    backfill = ROOT / "data" / "research" / "ou25_backfill.sqlite"
    rows = load_rows("serving", 20, backfill)
    coverage = _coverage()
    annual = {}
    raw_p = {}
    annual_picks = {}
    for index, season in enumerate(SEASONS):
        picks, baseline = _annual_baseline(rows, season, 20260827 + index * 10)
        raw_season_rows = [row for row in rows if str(row["season"]) == season]
        annual_picks[season] = picks
        raw_p[season] = _normal_p_greater([float(pick["profit"]) for pick in picks])
        source = "retrospective_multi_book_aggregate" if season <= "2023" else "retrospective_sofascore_aggregate"
        annual[season] = {
            "schema_version": "ou25-annual-ledger/1",
            "season": season,
            "as_of": "2026-08-27" if season == "2026" else None,
            "status": "PARTIAL_CONTAMINATED"
            if season == "2026"
            else ("OBSERVED_CONTAMINATED" if season >= "2024" else "RETROSPECTIVE_EXPLORATORY"),
            "price_source": source,
            "price_is_prospective_a1": False,
            "coverage": {
                **coverage[season],
                "priced_walkforward_games_before_quality_gate": len(raw_season_rows),
                "priced_walkforward_games": len(picks),
                "rejected_invalid_price_pairs": len(raw_season_rows) - len(picks),
            },
            "governed_v2_policy": {
                "action": "NO_BET",
                "bets": 0,
                "profit_units": 0.0,
                "roi": 0.0,
                "capital_enabled": False,
                "maximum_indication_score": 40,
                "reason": "no frozen candidate passed prospective A1 activation gates",
            },
            "always_bet_counterfactual": baseline,
            "interpretation": "counterfactual only; not a recommendation and not evidence of executable profit",
        }
    adjusted = holm_adjust(raw_p)
    for season in SEASONS:
        annual[season]["always_bet_counterfactual"]["p_raw_one_sided"] = raw_p[season]
        annual[season]["always_bet_counterfactual"]["p_holm_across_six_seasons"] = adjusted[season]
        json_path = output / f"ou25_{season}.json"
        csv_path = output / f"ou25_{season}_individual_losses.csv"
        json_path.write_text(
            json.dumps(annual[season], indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
        )
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            fields = list(annual_picks[season][0]) if annual_picks[season] else ["event_id"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(annual_picks[season])
    summary = {
        "schema_version": "ou25-annual-comparison/1",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "seasons": annual,
        "governed_total_profit_units": 0.0,
        "governed_total_bets": 0,
        "always_bet_total_profit_units": sum(
            float(annual[s]["always_bet_counterfactual"]["profit_units"]) for s in SEASONS
        ),
        "always_bet_total_bets": sum(int(annual[s]["always_bet_counterfactual"]["n"]) for s in SEASONS),
        "side_counts": Counter(p["side"] for picks in annual_picks.values() for p in picks),
        "multiplicity": "Holm across the six annual always-bet counterfactual tests",
        "observed_contaminated_seasons": ["2024", "2025", "2026"],
        "capital_enabled": False,
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "ou25-annual-manifest/1",
        "database_sha256": file_sha256(ROOT / "data" / "matches.db"),
        "backfill_sha256": file_sha256(backfill),
        "runner_sha256": file_sha256(Path(__file__)),
        "artifacts": {},
        "capital_enabled": False,
    }
    for path in [*sorted(output.glob("ou25_*")), summary_path]:
        manifest["artifacts"][path.name] = {"sha256": file_sha256(path), "bytes": path.stat().st_size}
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=dict))


if __name__ == "__main__":
    main()
