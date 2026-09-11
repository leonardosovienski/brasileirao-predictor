"""One independent pre-decision API capture, idempotent and bounded by UTC clocks."""

import hashlib
import importlib.util
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path("C:/BRASILEIRAO/brasileirao-predictor")
FIXTURE = "id1000032566887012"
KICKOFF = datetime(2026, 9, 12, tzinfo=UTC)
DECISION = KICKOFF - timedelta(hours=1)
TARGET = DECISION - timedelta(seconds=90)


def window_status(now):
    if now.tzinfo is None:
        raise ValueError("timezone_required")
    if now < DECISION - timedelta(minutes=5):
        return "WAITING"
    if now >= DECISION - timedelta(seconds=45):
        return "WINDOW_MISSED"
    return "DUE"


def main():
    now = datetime.now(UTC)
    status = window_status(now)
    if (ROOT / "followup/attempt.json").exists():
        print(json.dumps({"status": "ALREADY_ATTEMPTED", "directory": str(ROOT / "followup")}))
        return
    if status != "DUE":
        print(json.dumps({"status": status, "decision_at": DECISION.isoformat(), "target_at": TARGET.isoformat()}))
        return
    out = ROOT / "followup"
    out.mkdir(exist_ok=True)
    with (out / "attempt.json").open("x", encoding="utf-8") as stream:
        json.dump({"started_at": now.isoformat(), "fixture_id": FIXTURE, "max_metered_calls": 1}, stream)
    state = {
        "status": "IN_PROGRESS",
        "requests": [],
        "fixture_id": FIXTURE,
        "decision_at": DECISION.isoformat(),
        "picks": False,
        "protected_cohorts_used": False,
        "max_metered_calls": 1,
    }
    try:
        spec = importlib.util.spec_from_file_location("pilot_helpers", ROOT / "capture_pilot.py")
        if spec is None or spec.loader is None:
            raise ImportError("capture_helper_missing")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        key = json.loads(helper.PRIVATE.read_text(encoding="utf-8-sig"))["values"]["ODDSPAPI_KEY"]
        if not isinstance(key, str) or not key.strip():
            raise ValueError("invalid_data_api_key")
        opener = urllib.request.build_opener(
            helper.NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
        )
    except Exception as exc:
        state.update(
            status="STOPPED",
            reason="ACQUISITION_SETUP_FAILED",
            error_type=type(exc).__name__,
            finished_at=datetime.now(UTC).isoformat(),
        )
        (out / "receipt.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in state.items() if k != "requests"}))
        return

    def get(endpoint, params, label):
        record = {
            "endpoint": helper.API + endpoint,
            "parameters": params,
            "requested_at": datetime.now(UTC).isoformat(),
            "status": "ATTEMPT_STARTED",
        }
        state["requests"].append(record)
        helper.save(out / "receipt.json", state)
        try:
            request = urllib.request.Request(
                helper.API + endpoint + "?" + urllib.parse.urlencode({**params, "apiKey": key}),
                headers={"User-Agent": "brasileirao-independent-followup/1"},
            )
            with opener.open(request, timeout=25) as response:
                raw = response.read(30_000_001)
                record.update(
                    received_at=datetime.now(UTC).isoformat(),
                    http_status=response.status,
                    date_header=response.headers.get("Date"),
                )
            if len(raw) > 30_000_000:
                raise ValueError("oversize")
            if endpoint != "account":
                # Preserve even malformed public price bodies before attempting to parse them.
                (out / (label + ".json")).write_bytes(raw)
                record.update(file=label + ".json", sha256=hashlib.sha256(raw).hexdigest())
            value = json.loads(raw)
            if endpoint == "account":
                value = helper.sanitize_account(value)
                helper.save(out / (label + ".json"), value)
            record["status"] = "SAVED"
            helper.save(out / "receipt.json", state)
            return value, record
        except urllib.error.HTTPError as exc:
            record.update(status="HTTP_FAILURE", http_status=exc.code)
            raise RuntimeError("HTTP_FAILURE") from None
        except Exception as exc:
            record.update(status="FAILURE", error_type=type(exc).__name__)
            raise RuntimeError("REQUEST_FAILURE") from None

    try:
        account, _ = get("account", {}, "account_before")
        if (
            account["is_active"] is not True
            or account["request_limit"] != 250
            or account["auto_renew"] is not False
            or account["price"] not in (None, 0)
            or account["request_limit"] - account["request_count"] < 21
        ):
            raise RuntimeError("ACCOUNT_OR_RESERVE_BLOCKED")
        while datetime.now(UTC) < TARGET:
            time.sleep(min(10, max(0, (TARGET - datetime.now(UTC)).total_seconds())))
        if window_status(datetime.now(UTC)) != "DUE":
            raise RuntimeError("WINDOW_MISSED_AFTER_ACCOUNT")
        payload, receipt = get(
            "odds", {"fixtureId": FIXTURE, "bookmakers": "pinnacle,bet365.bet.br", "oddsFormat": "decimal"}, "capture"
        )
        state["status"] = "CAPTURED_REQUIRES_OFFLINE_AUDIT"
    except Exception as exc:
        state.update(status="STOPPED", error_type=type(exc).__name__)
        if type(exc) is RuntimeError:
            state["reason"] = str(exc)
    finally:
        try:
            account, _ = get("account", {}, "account_after")
            state["quota_after"] = account
        except Exception:
            state["account_after_failed"] = True
        state["finished_at"] = datetime.now(UTC).isoformat()
        helper.save(out / "receipt.json", state)
        print(json.dumps({k: v for k, v in state.items() if k != "requests"}))


if __name__ == "__main__":
    main()
