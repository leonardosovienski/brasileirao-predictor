"""One repair of a documented transport reset; original acquisition is immutable."""

import hashlib
import importlib.util
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    acquisition = json.loads((ROOT / "acquisition.json").read_text(encoding="utf-8"))
    if acquisition["status"] != "COMPLETE":
        raise SystemExit("WAIT_FOR_COMPLETED_ACQUISITION")
    path = ROOT / "transport_repair.json"
    if path.exists():
        raise SystemExit("NO_REPEAT")
    candidates = [
        r
        for r in acquisition["records"]
        if r["status"] == "REQUEST_FAILURE" and r.get("error_type") == "ConnectionResetError"
    ]
    if [r["fixture_id"] for r in candidates] != ["id1000032566886550"]:
        raise ValueError("repair_allowlist_mismatch")
    spec = importlib.util.spec_from_file_location("pilot", ROOT / "capture_pilot.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    key = json.loads(helper.PRIVATE.read_text(encoding="utf-8-sig"))["values"]["ODDSPAPI_KEY"]
    opener = urllib.request.build_opener(
        helper.NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
    )
    original = candidates[0]
    row = {
        "fixture_id": original["fixture_id"],
        "parameters": original["parameters"],
        "status": "ATTEMPT_STARTED",
        "requested_at": datetime.now(UTC).isoformat(),
        "original_failure_retained": True,
    }
    state = {"records": [row], "max_requests": 1, "quota_cost_documented": 0}
    helper.save(path, state)
    try:
        req = urllib.request.Request(
            helper.API + "historical-odds?" + urllib.parse.urlencode({**row["parameters"], "apiKey": key}),
            headers={"User-Agent": "brasileirao-transport-repair/1"},
        )
        with opener.open(req, timeout=40) as response:
            raw = response.read(30_000_001)
            row.update(http_status=response.status, received_at=datetime.now(UTC).isoformat())
        if len(raw) > 30_000_000:
            raise ValueError("oversize")
        value = json.loads(raw)
        if value.get("fixtureId") != row["fixture_id"]:
            raise ValueError("identity_mismatch")
        target = ROOT / "raw" / (row["fixture_id"] + ".json")
        with target.open("xb") as stream:
            stream.write(raw)
        row.update(
            status="DOWNLOADED", file="raw/" + target.name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()
        )
    except urllib.error.HTTPError as exc:
        row.update(status="HTTP_FAILURE", http_status=exc.code)
    except Exception as exc:
        row.update(status="REQUEST_FAILURE", error_type=type(exc).__name__)
    row["finished_at"] = datetime.now(UTC).isoformat()
    helper.save(path, state)
    # One final unmetered account check. Only sanitized allowance fields survive.
    receipt = {"endpoint": helper.API + "account", "requested_at": datetime.now(UTC).isoformat()}
    try:
        req = urllib.request.Request(helper.API + "account?" + urllib.parse.urlencode({"apiKey": key}))
        with opener.open(req, timeout=25) as response:
            account = helper.sanitize_account(json.loads(response.read(1_000_000)))
        receipt.update(status="VERIFIED", account=account, received_at=datetime.now(UTC).isoformat())
    except Exception as exc:
        receipt.update(status="CHECK_FAILURE", error_type=type(exc).__name__)
    helper.save(ROOT / "account_final.json", receipt)
    print(json.dumps({"repair": state, "final_account": receipt}))


if __name__ == "__main__":
    main()
