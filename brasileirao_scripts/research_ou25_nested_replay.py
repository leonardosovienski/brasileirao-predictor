"""Run and freeze the leakage-safe nested OU2.5 filter research.

Requires the operator's untracked ``data/matches.db``.  Outputs are written to
an explicit directory so exploratory evidence never silently changes serving.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brasileirao_predictor.ingest import load_config  # noqa: E402
from brasileirao_predictor.research.ou25_nested_replay import (  # noqa: E402
    FilterParameters,
    file_sha256,
    freeze_candidate,
    nested_walk_forward,
)
from brasileirao_scripts import benchmark_predictor as bp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def grid() -> list[FilterParameters]:
    return [
        FilterParameters(edge, maximum, low, high, side, quantile, friction)
        for edge in (-0.02, 0.00, 0.01, 0.02, 0.03, 0.05)
        for maximum in (0.10, 0.15, 0.25)
        for low, high in ((1.40, 1.80), (1.60, 2.10), (1.80, 2.40), (2.00, 3.20), (1.40, 3.20))
        for side in ("both", "over", "under")
        for quantile in (0.80, 0.90, 0.95)
        for friction in (0.01, 0.02)
        if edge <= maximum
    ]


def load_rows(engine: str, retrain_every: int, backfill_db: Path | None = None) -> list[dict]:
    if not bp.DB.exists():
        raise SystemExit(
            f"banco operacional ausente: {bp.DB}. Este arquivo e ignorado pelo Git; "
            "copie o snapshot verificado do operador ou rode a ingestao documentada no README."
        )
    if not backfill_db or not backfill_db.exists():
        raise SystemExit(
            "replay economico bloqueado: odds de sofascore_matches sao agregadas e nao possuem "
            "captured_at/bookmaker point-in-time; forneca uma fonte de snapshots validada "
            "ou mantenha o resultado como diagnostico nao economico"
        )
    price_db = backfill_db
    with sqlite3.connect(f"file:{price_db}?mode=ro", uri=True) as conn:
        if price_db == bp.DB:
            priced = conn.execute(
                "SELECT COUNT(*) FROM sofascore_matches WHERE odds_over IS NOT NULL AND odds_under IS NOT NULL"
            ).fetchone()[0]
            price_rows = {}
        else:
            price_rows = {
                str(event_id): (avg_over, avg_under)
                for event_id, avg_over, avg_under in conn.execute(
                    "SELECT event_id,avg_over,avg_under FROM ou25_historical_backfill"
                )
            }
            priced = len(price_rows)
    if priced == 0:
        raise SystemExit("zero pares OU2.5 no banco; replay economico bloqueado antes do ajuste do modelo")
    observations = bp._load_observations("")
    cfg = load_config()
    predicted, _ev = bp._run_walkforward(observations, 120.0, retrain_every, engine=engine, cfg=cfg)
    rows = []
    kickoff_by_event = {str(o["event_id"]): o["kickoff"].isoformat() for o in observations}
    for row in predicted:
        retrospective = price_rows.get(str(row["event_id"]))
        offered = retrospective or row.get("market_open_odds_ou25") or row.get("market_odds_ou25")
        closing = None if retrospective else row.get("market_odds_ou25")
        if not offered or not all(offered):
            continue
        rows.append(
            {
                "event_id": str(row["event_id"]),
                "kickoff_at": kickoff_by_event[str(row["event_id"])],
                "season": row["season"],
                "p_over": row["p_over"],
                "actual_over": row["actual_over"],
                "offered_odds_ou25": offered,
                "closing_odds_ou25": closing if closing and all(closing) else None,
            }
        )
    if not rows:
        raise SystemExit(
            "nenhum jogo tem par OU2.5 oferecido; ROI, EV e CLV nao podem ser estimados sem preco executavel"
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "research" / "ou25_nested")
    parser.add_argument("--engine", choices=bp.ENGINES, default="serving")
    parser.add_argument("--retrain-every", type=int, default=20)
    parser.add_argument("--minimum-train", type=int, default=760)
    parser.add_argument("--block-size", type=int, default=95)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--backfill-db", type=Path, default=ROOT / "data" / "research" / "ou25_backfill.sqlite")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = load_rows(args.engine, args.retrain_every, args.backfill_db)
    combinations = grid()
    result = nested_walk_forward(
        rows, combinations, minimum_train=args.minimum_train, block_size=args.block_size, seed=args.seed
    )
    result_path = args.output / "nested_replay.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    losses_path = args.output / "individual_losses.csv"
    with losses_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "event_id",
            "kickoff_at",
            "season",
            "side",
            "odd",
            "outcome_probability",
            "market_probability_devig",
            "gross_ev",
            "conservative_ev",
            "indication_strength_0_100",
            "strength_cap_reason",
            "uncertainty_haircut",
            "profit",
            "clv",
            "won",
            "contaminated",
            "outer_fold",
            "config_id",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result["picks"])
    source_hash = file_sha256(result_path)
    freeze_candidate(result, args.output / "frozen_candidate.json", source_hash=source_hash)
    manifest = {
        "schema_version": "ou25-research-manifest/2",
        "research_source_sha256": file_sha256(ROOT / "brasileirao_predictor" / "research" / "ou25_nested_replay.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "git_commit": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "database_sha256": file_sha256(bp.DB),
        "engine": args.engine,
        "retrain_every": args.retrain_every,
        "minimum_train": args.minimum_train,
        "block_size": args.block_size,
        "seed": args.seed,
        "combination_count": len(combinations),
        "backfill_database_sha256": file_sha256(args.backfill_db) if args.backfill_db.exists() else None,
        "price_semantics": "retrospective aggregate; CLV unavailable" if args.backfill_db.exists() else "operational",
        "combination_grid": [asdict(c) for c in combinations],
        "artifacts": {},
        "capital_enabled": False,
    }
    for path in (result_path, losses_path, args.output / "frozen_candidate.json"):
        manifest["artifacts"][path.name] = {"sha256": file_sha256(path), "bytes": path.stat().st_size}
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps({"output": str(args.output), "metrics": result["metrics"], "manifest": str(manifest_path)}, indent=2)
    )


if __name__ == "__main__":
    main()
