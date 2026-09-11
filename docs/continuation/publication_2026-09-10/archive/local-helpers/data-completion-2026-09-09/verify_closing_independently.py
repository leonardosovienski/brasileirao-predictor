"""Separate rational-arithmetic implementation; no production-module imports."""

import csv
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "closing_independent_check.json"
if OUT.exists():
    raise SystemExit("NO_OVERWRITE")
for name in list(os.environ):
    if name.upper() not in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}:
        del os.environ[name]


def guard(event, args):
    if event.startswith(("socket.", "sqlite3.", "subprocess.", "os.system")):
        raise PermissionError("offline_only")
    if event == "open" and isinstance(args[0], str | bytes | os.PathLike):
        p = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1] or "", args[2] or 0
        if (any(c in mode for c in "wax+") or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)) and p != OUT:
            raise PermissionError("single_receipt_write_only")
        if p.is_relative_to(Path("C:/BRASILEIRAO/DADOS_PRESERVADOS")) or p.name == ".env":
            raise PermissionError("private_protected_input")


sys.addaudithook(guard)
prices = ROOT / "public_sources/football_data_bra_origin_csv.csv"
source = list(csv.DictReader(prices.open(encoding="utf-8-sig", newline="")))
source = [r for r in source if r["Season"] == "2025"]
choices = {}
net = Fraction(0)
prizes = Fraction(0)
missing = 0
for r in source:
    day = datetime.strptime(r["Date"], "%d/%m/%Y").date().isoformat()
    fid = day + "|" + r["Home"] + "|" + r["Away"]
    try:
        ref = {s: Fraction(r["PSC" + c]) for s, c in [("away", "A"), ("draw", "D"), ("home", "H")]}
        offer = {s: Fraction(r["B365C" + c]) for s, c in [("away", "A"), ("draw", "D"), ("home", "H")]}
        if min(*ref.values(), *offer.values()) <= 1:
            raise ValueError("invalid")
    except (ValueError, ZeroDivisionError):
        missing += 1
        continue
    total = sum(1 / p for p in ref.values())
    if total <= 1:
        continue
    ev = {s: 1 / ref[s] / total * offer[s] - Fraction(102, 100) for s in ref}
    candidates = sorted((-v, s) for s, v in ev.items() if 0 < v <= Fraction(15, 100))
    if not candidates:
        continue
    side = candidates[0][1]
    choices[fid] = side
    hg, ag = int(r["HG"]), int(r["AG"])
    outcome = "home" if hg > ag else "away" if hg < ag else "draw"
    if r["Res"] != {"home": "H", "away": "A", "draw": "D"}[outcome]:
        raise ValueError("score_conflict")
    returned = offer[side] if side == outcome else 0
    prizes += returned
    net += returned - Fraction(102, 100)
frozen = json.loads((ROOT / "closing-01/frozen_choices.json").read_text(encoding="utf-8"))
observed = {r["event_id"]: r["selection"] for r in frozen if r["status"] == "CONDITIONAL_PICK"}
summary = json.loads((ROOT / "closing-01/summary.json").read_text(encoding="utf-8"))
assert choices == observed
assert net == Fraction(summary["net_realized_pnl"])
assert prizes == Fraction(summary["prizes_including_principal"])
assert Fraction(100) + net == Fraction(summary["final_cash"])
assert len(source) == summary["universe_n"]
assert len(choices) == summary["conditional_bets"]
receipt = {
    "status": "PASS",
    "implementation": "independent_Fraction_no_production_import",
    "independent_reviewer": False,
    "same_researcher": True,
    "universe": len(source),
    "same_choices": len(choices),
    "missing_pairs": missing,
    "net_pnl_rational": str(net),
    "prizes_rational": str(prizes),
    "source_sha256": hashlib.sha256(prices.read_bytes()).hexdigest(),
    "completed_at": datetime.now(UTC).isoformat(),
    "economic_validation": False,
}
OUT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt))
