"""Five-request maximum independent measurement pilot; no picks or outcomes."""

import hashlib
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = Path("C:/BRASILEIRAO")
API = "https://api.oddspapi.io/v4/"
PRIVATE = BASE / "DADOS_PRESERVADOS/migracao/private/ambiente_privado.json"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sanitize_account(payload):
    rows = [
        s
        for s in payload["subscriptions"]
        if s.get("is_active") is True and s.get("subscription_id") == payload["current_subscription_id"]
    ]
    if len(rows) != 1:
        raise ValueError("account_ambiguous")
    sub = rows[0]
    return {f: sub.get(f) for f in ("price", "currency", "is_active", "auto_renew", "request_limit", "request_count")}


def main():
    out = ROOT / "prospective_pilot"
    out.mkdir(exist_ok=False)
    key = json.loads(PRIVATE.read_text(encoding="utf-8-sig"))["values"]["ODDSPAPI_KEY"]
    opener = urllib.request.build_opener(
        NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
    )
    addendum = BASE / "brasileirao-predictor/docs/continuation/data_completion_2026-09-09/ACQUISITION_ADDENDUM.md"
    state = {
        "started_at": datetime.now(UTC).isoformat(),
        "status": "IN_PROGRESS",
        "addendum_sha256": hashlib.sha256(addendum.read_bytes()).hexdigest(),
        "maximum_metered_requests": 5,
        "metered_attempts": 0,
        "minimum_reserve": 20,
        "picks": False,
        "settlement": False,
        "protected_inputs": False,
        "requests": [],
    }
    save(out / "receipt.json", state)

    def get(endpoint, params, label, metered=False):
        if metered and state["metered_attempts"] >= 5:
            raise ValueError("budget_exhausted")
        row = {
            "endpoint": API + endpoint,
            "parameters": params,
            "requested_at": datetime.now(UTC).isoformat(),
            "status": "ATTEMPT_STARTED",
            "metered": metered,
        }
        state["requests"].append(row)
        if metered:
            state["metered_attempts"] += 1
        save(out / "receipt.json", state)
        try:
            req = urllib.request.Request(
                API + endpoint + "?" + urllib.parse.urlencode({**params, "apiKey": key}),
                headers={"User-Agent": "brasileirao-independent-price-measurement/1"},
            )
            with opener.open(req, timeout=40) as response:
                raw = response.read(30_000_001)
                row.update(
                    http_status=response.status,
                    received_at=datetime.now(UTC).isoformat(),
                    response_headers={h: response.headers.get(h) for h in ("Date", "Content-Type", "ETag")},
                )
            if len(raw) > 30_000_000:
                raise ValueError("oversize_payload")
            value = json.loads(raw)
            if endpoint == "account":
                value = sanitize_account(value)
                save(out / (label + ".json"), value)
                row["raw_account_saved"] = False
            else:
                (out / (label + ".json")).write_bytes(raw)
                row.update(file=label + ".json", sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
            row["status"] = "SAVED"
            save(out / "receipt.json", state)
            return value
        except urllib.error.HTTPError as exc:
            row.update(status="HTTP_FAILURE", http_status=exc.code)
            save(out / "receipt.json", state)
            raise RuntimeError("http_failure") from None
        except Exception as exc:
            row.update(status="FAILURE", error_type=type(exc).__name__)
            save(out / "receipt.json", state)
            raise RuntimeError("request_failure") from None

    try:
        account = get("account", {}, "account_before")
        if (
            account["request_limit"] != 250
            or account["is_active"] is not True
            or account["auto_renew"] is not False
            or account["price"] not in (None, 0)
            or account["request_limit"] - account["request_count"] - 5 < 20
        ):
            raise ValueError("free_plan_or_reserve_not_confirmed")
        books = get("bookmakers", {}, "bookmaker_catalog", True)
        if not isinstance(books, list):
            raise ValueError("bookmaker_catalog_schema")
        selected_books = {b["slug"]: b for b in books if b.get("slug") in ("pinnacle", "bet365.bet.br", "bet365")}
        save(out / "bookmaker_identity.json", selected_books)
        if not {"pinnacle", "bet365.bet.br"} <= set(selected_books):
            raise ValueError("regional_book_missing")
        if any(selected_books[b].get("cloneOf") for b in ("pinnacle", "bet365.bet.br")):
            raise ValueError("clone_mapping_requires_review")
        now = datetime.now(UTC)
        params = {
            "sportId": 10,
            "tournamentId": 325,
            "statusId": 0,
            "from": now.date().isoformat(),
            "to": (now + timedelta(days=14)).date().isoformat(),
        }
        fixtures = get("fixtures", params, "fixture_catalog", True)
        if not isinstance(fixtures, list):
            raise ValueError("fixture_catalog_schema")
        choices = []
        for event in fixtures:
            at = datetime.fromisoformat(event["startTime"].replace("Z", "+00:00"))
            if (
                event.get("statusId") == 0
                and event.get("tournamentId") == 325
                and at.tzinfo
                and now + timedelta(minutes=65) < at <= now + timedelta(days=14)
            ):
                choices.append((at, event["fixtureId"], event))
        choices.sort(key=lambda x: (x[0], x[1]))
        if not choices:
            raise ValueError("no_eligible_future_fixture")
        at, fid, event = choices[0]
        selected = {
            "fixture_id": fid,
            "kickoff_at": at.isoformat(),
            "home": event.get("participant1Name"),
            "away": event.get("participant2Name"),
            "frozen_at": datetime.now(UTC).isoformat(),
            "books": ["pinnacle", "bet365.bet.br"],
            "market": "1x2",
            "period": "FT",
            "line": None,
            "selection_rule": "earliest_pre_game_kickoff_more_than_65min_within_14days",
            "eligible_fixture_count": len(choices),
            "purpose": "CLOCK_AND_IDENTITY_MEASUREMENT_NO_PICKS",
        }
        save(out / "selected_fixture.json", selected)
        for i in range(3):
            raw = get(
                "odds",
                {"fixtureId": fid, "bookmakers": "pinnacle,bet365.bet.br", "oddsFormat": "decimal"},
                f"capture_{i + 1:02d}",
                True,
            )
            if raw.get("fixtureId") != fid:
                raise ValueError("capture_identity_mismatch")
            print(json.dumps({"capture": i + 1, "status": "SAVED", "fixture_id": fid}), flush=True)
            if i < 2:
                time.sleep(30)
        state["status"] = "CAPTURED_REQUIRES_AUDIT"
    except Exception as exc:
        state.update(status="STOPPED", error_type=type(exc).__name__)
        # Only locally assigned ValueError codes are printed; request exceptions are sanitized.
        if type(exc) is ValueError:
            state["reason"] = str(exc)
    finally:
        try:
            after = get("account", {}, "account_after")
            state["quota_after"] = after
        except Exception:
            state["account_after_failed"] = True
        state["finished_at"] = datetime.now(UTC).isoformat()
        save(out / "receipt.json", state)
        print(json.dumps({k: v for k, v in state.items() if k != "requests"}), flush=True)


if __name__ == "__main__":
    main()
