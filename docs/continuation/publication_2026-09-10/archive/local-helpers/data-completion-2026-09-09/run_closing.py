"""Freeze prices before interpreting 2025 labels; conditional closing replay only."""

import csv
import hashlib
import io
import json
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path("C:/BRASILEIRAO/brasileirao-predictor")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main():
    out = ROOT / "closing-01"
    out.mkdir(exist_ok=False)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(REPO))
    for name in list(os.environ):
        if name.upper() not in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}:
            del os.environ[name]

    def guard(event, args):
        if event.startswith(("socket.", "sqlite3.", "subprocess.", "os.system")):
            raise PermissionError("network_database_subprocess_forbidden")
        if event == "open" and isinstance(args[0], str | bytes | os.PathLike):
            p = Path(os.fsdecode(args[0])).resolve()
            mode, flags = args[1] or "", args[2] or 0
            writing = any(c in mode for c in "wax+") or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
            if writing and not p.is_relative_to(out):
                raise PermissionError("write_outside_output")
            if (
                p.is_relative_to(Path("C:/BRASILEIRAO/DADOS_PRESERVADOS"))
                or p.is_relative_to(REPO / "data")
                or p.name == ".env"
            ):
                raise PermissionError("private_or_protected_input")

    sys.addaudithook(guard)
    from brasileirao_predictor.research.price_strength.closing_scenario import freeze_choices, settle_frozen

    raw = (ROOT / "public_sources/football_data_bra_origin_csv.csv").read_bytes()
    manifest = json.loads((ROOT / "public_sources/manifest.json").read_text(encoding="utf-8"))
    expected = next(r["sha256"] for r in manifest if r["source"] == "football_data_bra_origin_csv")
    if sha(raw) != expected:
        raise ValueError("source_hash_mismatch")

    def identity(row):
        day = datetime.strptime(row["Date"], "%d/%m/%Y").date().isoformat()
        return day + "|" + row["Home"] + "|" + row["Away"], day

    rows = []
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        if row.get("Season") != "2025":
            continue
        if row["Country"] != "Brazil" or row["League"] != "Serie A":
            raise ValueError("unexpected_competition")
        fid, day = identity(row)
        pair = [("home", "H"), ("draw", "D"), ("away", "A")]
        rows.append(
            {
                "event_id": fid,
                "date": day,
                "offer": {s: row["B365C" + c] for s, c in pair},
                "reference": {s: row["PSC" + c] for s, c in pair},
            }
        )
    if len(rows) != 380:
        raise ValueError("wrong_universe")
    frozen = freeze_choices(rows)
    save(out / "frozen_choices.json", frozen)
    frozen_hash = sha((out / "frozen_choices.json").read_bytes())
    receipt = {
        "frozen_at": datetime.now(UTC).isoformat(),
        "input_sha256": expected,
        "choices_sha256": frozen_hash,
        "labels_interpreted_before_freeze": False,
        "python": sys.version,
        "protocol_sha256": sha((REPO / "docs/continuation/price_feasibility_2026-09-09/PROTOCOL.md").read_bytes()),
        "addendum_sha256": sha(
            (REPO / "docs/continuation/data_completion_2026-09-09/ACQUISITION_ADDENDUM.md").read_bytes()
        ),
    }
    save(out / "freeze_receipt.json", receipt)
    labels = {}
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        if row.get("Season") == "2025":
            fid, _ = identity(row)
            labels[fid] = {"home_goals": row["HG"], "away_goals": row["AG"], "result": row["Res"]}
    if sha((out / "frozen_choices.json").read_bytes()) != frozen_hash:
        raise ValueError("choices_changed")
    result = settle_frozen(frozen, labels)
    events = result.pop("events")
    result["price_abstention_reasons"] = dict(Counter(r["reason"] for r in frozen if r["status"] == "ABSTAIN"))
    settled = [r for r in events if r["status"] == "SETTLED"]
    weekly, monthly = defaultdict(lambda: [0.0, 0.0]), defaultdict(lambda: [0, 0.0])
    for event in events:
        week = datetime.fromisoformat(event["date"]).isocalendar()[:2]
        weekly[week][1] += float(event.get("stake", 0))
        if event["status"] == "SETTLED":
            weekly[week][0] += float(event["net_pnl"])
            monthly[event["date"][:7]][0] += 1
            monthly[event["date"][:7]][1] += float(event["net_pnl"])
    result["monthly_bets_pnl"] = dict(sorted(monthly.items()))
    if settled and not result["unsettled"]:
        rng = random.Random(20260909)
        blocks, rois = list(weekly.values()), []
        for _ in range(2000):
            sample = rng.choices(blocks, k=len(blocks))
            stakes = sum(b[1] for b in sample)
            if stakes:
                rois.append(sum(b[0] for b in sample) / stakes)
        rois.sort()
        result["weekly_bootstrap"] = {
            "seed": 20260909,
            "replicates": 2000,
            "defined": len(rois),
            "weeks": len(blocks),
            "unit": "ISO_week_all_universe_including_abstentions",
            "percentile_95_roi": [rois[int((len(rois) - 1) * q)] for q in (0.025, 0.975)],
        }
        bins = defaultdict(list)
        for r in settled:
            bins[min(9, int(float(r["probability"]) * 10))].append(r)
        result["selected_calibration"] = {
            "n": len(settled),
            "mean_q": sum(float(r["probability"]) for r in settled) / len(settled),
            "win_rate": sum(r["won"] for r in settled) / len(settled),
            "binary_brier": sum((float(r["probability"]) - float(r["won"])) ** 2 for r in settled) / len(settled),
            "bins": [
                {
                    "decile": b,
                    "n": len(rs),
                    "mean_q": sum(float(r["probability"]) for r in rs) / len(rs),
                    "win_rate": sum(r["won"] for r in rs) / len(rs),
                }
                for b, rs in sorted(bins.items())
            ],
        }
        wins = sorted((float(r["net_pnl"]) for r in settled if r["won"]), reverse=True)
        result["concentration"] = {
            "wins": len(wins),
            "top_five_winning_net": wins[:5],
            "net_without_largest_win": float(result["net_realized_pnl"]) - (wins[0] if wins else 0),
        }
    result["fixed_selection_cost_sensitivity"] = (
        [
            {
                "cost_per_stake": str(c),
                "conditional_net_pnl": str(
                    Decimal(result["prizes_including_principal"]) - Decimal(result["total_stakes"]) * (1 + c)
                ),
                "same_selections": True,
            }
            for c in map(Decimal, ("0", "0.01", "0.02", "0.03", "0.05"))
        ]
        if not result["unsettled"]
        else []
    )
    result["comparator"] = {"policy": "abstention", "stakes": 0, "variable_pnl": 0, "fixed_costs": None}
    result["unknown_actual_costs"] = [
        "tax",
        "commission",
        "slippage",
        "rejections",
        "data",
        "infrastructure",
        "maintenance",
    ]
    result["limitations"] = [
        "closing_not_T_minus_60",
        "no_per_quote_clocks",
        "no_accepted_fills",
        "generic_bookmaker_region_unverified",
        "2025_previously_exploratory",
        "2_percent_hypothetical_cost",
    ]
    save(out / "events.json", events)
    save(out / "summary.json", result)
    save(
        out / "manifest.json",
        {
            **receipt,
            "completed_at": datetime.now(UTC).isoformat(),
            "outputs": {p.name: sha(p.read_bytes()) for p in out.iterdir() if p.is_file()},
            "isolation": "network_sqlite_subprocess_private_protected_denied",
        },
    )
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("selected_calibration", "monthly_bets_pnl", "limitations")}
        )
    )


if __name__ == "__main__":
    main()
