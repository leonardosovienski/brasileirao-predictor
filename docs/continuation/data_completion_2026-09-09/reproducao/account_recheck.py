"""Final unmetered check using the original client's explicit research identity."""

import importlib.util
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "account_final_recheck.json"
if OUT.exists():
    raise SystemExit("NO_REPEAT")
spec = importlib.util.spec_from_file_location("pilot", ROOT / "capture_pilot.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
receipt = {
    "endpoint": module.API + "account",
    "requested_at": datetime.now(UTC).isoformat(),
    "quota_cost_documented": 0,
    "prior_check_failure_preserved": True,
}
module.save(OUT, {**receipt, "status": "ATTEMPT_STARTED"})
try:
    key = json.loads(module.PRIVATE.read_text(encoding="utf-8-sig"))["values"]["ODDSPAPI_KEY"]
    opener = urllib.request.build_opener(
        module.NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
    )
    request = urllib.request.Request(
        module.API + "account?" + urllib.parse.urlencode({"apiKey": key}),
        headers={"User-Agent": "brasileirao-independent-price-measurement/1"},
    )
    with opener.open(request, timeout=30) as response:
        value = module.sanitize_account(json.loads(response.read(1_000_000)))
        receipt.update(status="VERIFIED", http_status=response.status, account=value)
except urllib.error.HTTPError as exc:
    receipt.update(status="HTTP_FAILURE", http_status=exc.code)
except Exception as exc:
    receipt.update(status="CHECK_FAILURE", error_type=type(exc).__name__)
receipt["finished_at"] = datetime.now(UTC).isoformat()
module.save(OUT, receipt)
print(json.dumps(receipt))
