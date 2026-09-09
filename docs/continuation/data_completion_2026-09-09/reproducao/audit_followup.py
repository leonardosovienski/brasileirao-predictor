"""Offline follow-up audit, in a separate credential-free process."""

import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path("C:/BRASILEIRAO/brasileirao-predictor")
INPUT = ROOT / "followup"
OUTPUT = ROOT / "followup_audit"


def main():
    if not (INPUT / "capture.json").exists():
        print("NO_CAPTURE_TO_AUDIT")
        return
    if (OUTPUT / "audit.json").exists():
        print("ALREADY_AUDITED")
        return
    OUTPUT.mkdir(exist_ok=True)
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
            if (
                any(c in mode for c in "wax+") or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
            ) and not p.is_relative_to(OUTPUT):
                raise PermissionError("write_outside_output")
            if (
                p.is_relative_to(Path("C:/BRASILEIRAO/DADOS_PRESERVADOS"))
                or p.is_relative_to(REPO / "data")
                or p.name == ".env"
            ):
                raise PermissionError("private_protected_input")

    sys.addaudithook(guard)
    from brasileirao_predictor.research.price_strength.live_capture_admission import audit_capture

    raw = (INPUT / "capture.json").read_bytes()
    reason = "invalid_receipt_json_or_schema"
    try:
        state = json.loads((INPUT / "receipt.json").read_text(encoding="utf-8"))
        receipts = [r for r in state["requests"] if r.get("file") == "capture.json"]
        reason = "receipt_contract_mismatch"
        if len(receipts) != 1:
            raise ValueError(reason)
        receipt = receipts[0]
        expected_parameters = {
            "fixtureId": "id1000032566887012",
            "bookmakers": "pinnacle,bet365.bet.br",
            "oddsFormat": "decimal",
        }
        if (
            receipt.get("endpoint") != "https://api.oddspapi.io/v4/odds"
            or receipt.get("parameters") != expected_parameters
            or type(receipt.get("http_status")) is not int
            or receipt["http_status"] != 200
            or receipt.get("status") != "SAVED"
        ):
            raise ValueError(reason)
        reason = "receipt_or_hash_mismatch"
        if hashlib.sha256(raw).hexdigest() != receipt.get("sha256"):
            raise ValueError(reason)
        reason = "invalid_payload_or_clock"
        payload = json.loads(raw)
        audit = audit_capture(payload, receipt, "id1000032566887012")
        received = datetime.fromisoformat(receipt["received_at"])
        decision = datetime(2026, 9, 11, 23, tzinfo=UTC)
        audit["frozen_decision_clock_admitted"] = 0 <= (decision - received).total_seconds() <= 120
        audit["frozen_kickoff_unchanged"] = datetime.fromisoformat(
            payload["startTime"].replace("Z", "+00:00")
        ) == datetime(2026, 9, 12, tzinfo=UTC)
        audit["prospective_price_observation_admitted"] = bool(
            audit.get("pair_api_state_admitted", False)
            and audit["frozen_decision_clock_admitted"]
            and audit["frozen_kickoff_unchanged"]
        )
        audit["status"] = "OBSERVATION_AUDITED"
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, OSError) as exc:
        audit = {
            "fixture_id": "id1000032566887012",
            "status": "REJECTED_INVALID_INPUT",
            "reason": reason,
            "error_type": type(exc).__name__,
            "execution_admitted": False,
            "prospective_price_observation_admitted": False,
        }
    audit["source_hash"] = hashlib.sha256(raw).hexdigest()
    audit["completed_at"] = datetime.now(UTC).isoformat()
    temporary = OUTPUT / "audit.json.tmp"
    temporary.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT / "audit.json")
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
