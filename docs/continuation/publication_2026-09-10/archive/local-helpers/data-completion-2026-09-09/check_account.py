"""Read-only, unmetered account check; no secrets in output or raw account persistence."""

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRIVATE = Path("C:/BRASILEIRAO/DADOS_PRESERVADOS/migracao/private/ambiente_privado.json")
ENDPOINT = "https://api.oddspapi.io/v4/account"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    out = ROOT / "account_check_01.json"
    if out.exists():
        raise SystemExit("existing_receipt_no_repeat")
    receipt = {
        "endpoint": ENDPOINT,
        "started_at": datetime.now(UTC).isoformat(),
        "method": "GET",
        "quota_cost_documented": 0,
        "raw_account_saved": False,
    }
    out.write_text(json.dumps({**receipt, "status": "ATTEMPT_STARTED"}, indent=2), encoding="utf-8")
    try:
        key = json.loads(PRIVATE.read_text(encoding="utf-8-sig"))["values"]["ODDSPAPI_KEY"]
        if not isinstance(key, str) or not key.strip():
            raise ValueError("missing_key")
        request = urllib.request.Request(
            ENDPOINT + "?" + urllib.parse.urlencode({"apiKey": key}),
            headers={"User-Agent": "brasileirao-research-data-audit/1"},
        )
        opener = urllib.request.build_opener(
            NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
        )
        with opener.open(request, timeout=30) as response:
            receipt["http_status"] = response.status
            account = json.loads(response.read(1_000_000))
        active = [
            s
            for s in account.get("subscriptions", [])
            if s.get("is_active") is True and s.get("subscription_id") == account.get("current_subscription_id")
        ]
        if len(active) != 1:
            raise ValueError("ambiguous_active_subscription")
        sub = active[0]
        fields = (
            "currency",
            "price",
            "valid_from",
            "valid_until",
            "auto_renew",
            "is_active",
            "request_limit",
            "rate_limit",
            "request_count",
            "sport_ids",
            "bookmakers",
        )
        receipt["subscription"] = {f: sub.get(f) for f in fields}
        receipt["status"] = "ACCOUNT_RETRIEVED"
        del key, account, sub, request
    except urllib.error.HTTPError as exc:
        receipt.update(status="HTTP_FAILURE", http_status=exc.code)
    except Exception as exc:
        receipt.update(status="CHECK_FAILURE", error_type=type(exc).__name__)
    receipt["finished_at"] = datetime.now(UTC).isoformat()
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
