"""Verify hashes and temporal admission of acquired research data, offline."""

import hashlib
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path("C:/BRASILEIRAO/brasileirao-predictor")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    out = ROOT / "admission-01"
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
                raise PermissionError("protected_private_input")

    sys.addaudithook(guard)
    from brasileirao_predictor.research.price_strength.historical_admission import audit_history
    from brasileirao_predictor.research.price_strength.live_capture_admission import audit_capture

    acquisition = json.loads((ROOT / "acquisition.json").read_text(encoding="utf-8"))
    if acquisition["status"] not in ("COMPLETE", "STOPPED"):
        raise ValueError("acquisition_still_running")
    records = {r["fixture_id"]: r for r in acquisition["records"]}
    if (ROOT / "transport_repair.json").exists():
        for r in json.loads((ROOT / "transport_repair.json").read_text(encoding="utf-8"))["records"]:
            if r["status"] == "DOWNLOADED":
                records[r["fixture_id"]] = r
    universe_raw = (ROOT / "universe.json").read_bytes()
    if sha(universe_raw) != acquisition["universe_sha256"]:
        raise ValueError("universe_hash_mismatch")
    universe = json.loads(universe_raw)
    audits = []
    raw_bytes = 0
    for fixture in universe:
        record = records.get(fixture["fixture_id"])
        if not record or record["status"] not in ("DOWNLOADED", "REUSED_VERIFIED"):
            audits.append(
                {
                    "fixture_id": fixture["fixture_id"],
                    "execution_admitted": False,
                    "reason": "acquisition_missing",
                    "conditional_selection": None,
                    "bookmakers": {},
                }
            )
            continue
        raw = (ROOT / record["file"]).read_bytes()
        if sha(raw) != record["sha256"]:
            raise ValueError("raw_hash_mismatch")
        raw_bytes += len(raw)
        audits.append(audit_history(json.loads(raw), fixture, record["received_at"]))
    summary = {
        "universe_n": len(universe),
        "history_files_verified": sum(r["reason"] != "acquisition_missing" for r in audits),
        "raw_bytes_verified": raw_bytes,
        "execution_admitted": sum(r["execution_admitted"] for r in audits),
        "conditional_selections": sum(r["conditional_selection"] is not None for r in audits),
        "reasons": dict(Counter(r["reason"] for r in audits)),
        "per_book": {
            b: {
                "complete_active_T60": sum(
                    r.get("bookmakers", {}).get(b, {}).get("complete_active", False) for r in audits
                ),
                "latest_changes_within_120s": sum(
                    r.get("bookmakers", {}).get(b, {}).get("within_120s", False) for r in audits
                ),
            }
            for b in ("pinnacle", "bet365")
        },
        "no_results_or_protected_cohorts_used": True,
        "profitability_established": False,
    }
    save(out / "historical_events.json", audits)
    save(out / "historical_summary.json", summary)
    pilot = ROOT / "prospective_pilot"
    receipt = json.loads((pilot / "receipt.json").read_text(encoding="utf-8"))
    selection = json.loads((pilot / "selected_fixture.json").read_text(encoding="utf-8"))
    capture_audits = []
    for r in receipt["requests"]:
        if r["endpoint"].endswith("/odds") and r["status"] == "SAVED":
            raw = (pilot / r["file"]).read_bytes()
            if sha(raw) != r["sha256"]:
                raise ValueError("capture_hash_mismatch")
            a = audit_capture(json.loads(raw), r, selection["fixture_id"])
            a["file"] = r["file"]
            capture_audits.append(a)
    pilot_summary = {
        "captures": len(capture_audits),
        "independent_fixtures": 1,
        "pair_api_state_admitted": sum(r.get("pair_api_state_admitted", False) for r in capture_audits),
        "execution_admitted": 0,
        "reasons": dict(Counter(r["reason"] for r in capture_audits)),
        "quota_requests": receipt["metered_attempts"],
        "quota_count_after": receipt["quota_after"]["request_count"],
        "round_trip_seconds": [r["round_trip_seconds"] for r in capture_audits],
        "kickoff_at": selection["kickoff_at"],
    }
    save(out / "pilot_events.json", capture_audits)
    save(out / "pilot_summary.json", pilot_summary)
    closing = json.loads((ROOT / "closing-01/frozen_choices.json").read_text(encoding="utf-8"))
    chosen = [r for r in closing if r["status"] == "CONDITIONAL_PICK"]
    quality = {
        "source": "https://football-data.co.uk/data",
        "warning_start": "2025-07-23",
        "found_after_conditional_result": True,
        "frozen_selections_unchanged": True,
        "selected_n": len(chosen),
        "selected_after_warning_start": sum(r["date"] >= "2025-07-23" for r in chosen),
        "interpretation": "ARITHMETIC_SCENARIO_WITH_COMPROMISED_REFERENCE_NOT_ECONOMIC_VALIDATION",
        "reestimate_on_retrospectively_filtered_subset": False,
    }
    save(out / "closing_source_quality.json", quality)
    save(
        out / "manifest.json",
        {
            "completed_at": datetime.now(UTC).isoformat(),
            "acquisition_sha256": sha((ROOT / "acquisition.json").read_bytes()),
            "outputs": {p.name: sha(p.read_bytes()) for p in out.iterdir()},
            "source_modules": {
                p.name: sha(p.read_bytes())
                for p in (REPO / "brasileirao_predictor/research/price_strength").glob("*admission.py")
            },
            "isolation": "network_sqlite_subprocess_private_protected_denied",
        },
    )
    print(json.dumps({"historical": summary, "pilot": pilot_summary, "closing_quality": quality}))


if __name__ == "__main__":
    main()
