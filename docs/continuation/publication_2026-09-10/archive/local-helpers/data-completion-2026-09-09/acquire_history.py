"""Bounded, resumable public-data acquisition; only unmetered OddsPapi endpoints."""

import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = Path("C:/BRASILEIRAO")
OLD = (
    BASE / "DADOS_PRESERVADOS/projetos/brasileirao-predictor-sessoes/2026-09-07/work/selection_reanalysis/price_history"
)
PROTOCOL = BASE / "brasileirao-predictor/docs/continuation/data_completion_2026-09-09/PROTOCOL.md"
PROTOCOL_HASH = "40b45152f77db425787739136a7092ee375a3ce0f34e07457b5cf43b6c10de21"
API = "https://api.oddspapi.io/v4/"
DEADLINE = datetime(2026, 9, 9, 22, 32, tzinfo=UTC)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    if digest(PROTOCOL.read_bytes()) != PROTOCOL_HASH:
        raise ValueError("protocol_changed")
    if (ROOT / "acquisition.json").exists():
        raise SystemExit("existing_acquisition_no_automatic_repeat")
    inv = json.loads((BASE / "AUDITORIA/inventario_dados_preservados.json").read_text(encoding="utf-8-sig"))
    hashes = {row["path"]: row["sha256"] for row in inv["files"]}

    def verified(path):
        raw = path.read_bytes()
        if digest(raw) != hashes[path.relative_to(BASE).as_posix()]:
            raise ValueError("migration_hash_mismatch")
        return raw

    universe_bytes = verified(OLD / "fixture_universe_jan_jun_2026.json")
    universe = json.loads(universe_bytes)
    if len(universe) != 177 or len({r["fixture_id"] for r in universe}) != 177:
        raise ValueError("universe_changed")
    for row in universe:
        at = datetime.fromisoformat(row["kickoff_at"].replace("Z", "+00:00"))
        if not re.fullmatch("id[0-9]+", row["fixture_id"]) or not at.tzinfo:
            raise ValueError("invalid_identity")
        if not datetime(2026, 1, 1, tzinfo=UTC) <= at < datetime(2026, 7, 1, tzinfo=UTC):
            raise ValueError("forbidden_time_window")
        if set(row) != {"fixture_id", "kickoff_at", "home", "away", "status"}:
            raise ValueError("unexpected_universe_fields")
    (ROOT / "raw").mkdir(exist_ok=True)
    (ROOT / "universe.json").write_bytes(universe_bytes)
    previous = json.loads(verified(OLD / "history_acquisition_manifest.json"))
    reusable = {r["fixture_id"]: r for r in previous["records"] if r.get("status") == "SAVED_PRIVATE_RAW"}
    state = {
        "protocol_sha256": PROTOCOL_HASH,
        "universe_sha256": digest(universe_bytes),
        "started_at": datetime.now(UTC).isoformat(),
        "status": "ACQUIRING",
        "universe_n": len(universe),
        "bookmakers": ["pinnacle", "bet365"],
        "endpoint": API + "historical-odds",
        "new_request_limit": 177,
        "quota_cost_documented": 0,
        "cooldown_after_response_seconds": 7,
        "automatic_retries": False,
        "records": [],
    }
    save(ROOT / "acquisition.json", state)
    account = json.loads((ROOT / "account_check_01.json").read_text(encoding="utf-8"))
    sub = account["subscription"]
    if account["status"] != "ACCOUNT_RETRIEVED" or sub["is_active"] is not True:
        raise ValueError("account_not_active")
    if sub["request_limit"] - sub["request_count"] < 20:
        raise ValueError("reserve_unavailable")
    if not {"pinnacle", "bet365"} <= set(sub["bookmakers"]):
        raise ValueError("bookmaker_access_not_verified")
    key = json.loads(
        (BASE / "DADOS_PRESERVADOS/migracao/private/ambiente_privado.json").read_text(encoding="utf-8-sig")
    )["values"]["ODDSPAPI_KEY"]
    opener = urllib.request.build_opener(
        NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
    )
    consecutive_failures = 0
    for ordinal, row in enumerate(universe, 1):
        fid = row["fixture_id"]
        record = {"ordinal": ordinal, "fixture_id": fid, "kickoff_at": row["kickoff_at"]}
        if fid in reusable:
            prior = reusable[fid]
            raw = verified(OLD / "raw" / (fid + ".json"))
            if digest(raw) != prior["sha256"]:
                raise ValueError("original_acquisition_hash_mismatch")
            (ROOT / "raw" / (fid + ".json")).write_bytes(raw)
            record.update(
                status="REUSED_VERIFIED",
                file="raw/" + fid + ".json",
                bytes=len(raw),
                sha256=digest(raw),
                received_at=prior["finished_at"],
                original_acquisition_at=prior["attempted_at"],
            )
            state["records"].append(record)
            save(ROOT / "acquisition.json", state)
            continue
        if datetime.now(UTC) >= DEADLINE:
            state["stop_reason"] = "DEADLINE"
            break
        record.update(
            status="ATTEMPT_STARTED",
            requested_at=datetime.now(UTC).isoformat(),
            parameters={"fixtureId": fid, "bookmakers": "pinnacle,bet365"},
        )
        state["records"].append(record)
        save(ROOT / "acquisition.json", state)
        stop = False
        try:
            request = urllib.request.Request(
                API + "historical-odds?" + urllib.parse.urlencode({**record["parameters"], "apiKey": key}),
                headers={"User-Agent": "brasileirao-research-data-audit/1"},
            )
            with opener.open(request, timeout=40) as response:
                raw = response.read(30_000_001)
                record.update(
                    http_status=response.status,
                    received_at=datetime.now(UTC).isoformat(),
                    response_headers={h: response.headers.get(h) for h in ("Date", "ETag", "Content-Type")},
                )
            if len(raw) > 30_000_000:
                raise ValueError("oversize_payload")
            payload = json.loads(raw)
            if (
                not isinstance(payload, dict)
                or payload.get("fixtureId") != fid
                or not isinstance(payload.get("bookmakers"), dict)
            ):
                raise ValueError("payload_identity_or_schema")
            (ROOT / "raw" / (fid + ".json")).write_bytes(raw)
            record.update(status="DOWNLOADED", file="raw/" + fid + ".json", bytes=len(raw), sha256=digest(raw))
            consecutive_failures = 0
        except urllib.error.HTTPError as exc:
            record.update(status="HTTP_FAILURE", http_status=exc.code)
            consecutive_failures += 1
            if exc.code in (401, 403, 429):
                stop = True
                state["stop_reason"] = "AUTHORIZATION_OR_RATE_LIMIT"
        except Exception as exc:
            record.update(status="REQUEST_FAILURE", error_type=type(exc).__name__)
            consecutive_failures += 1
        record["finished_at"] = datetime.now(UTC).isoformat()
        save(ROOT / "acquisition.json", state)
        if ordinal % 10 == 0 or record["status"] != "DOWNLOADED":
            print(json.dumps({"processed": ordinal, "universe_n": 177, "status": record["status"]}), flush=True)
        if stop or consecutive_failures >= 3:
            state.setdefault("stop_reason", "THREE_CONSECUTIVE_FAILURES")
            break
        time.sleep(7)
    state["finished_at"] = datetime.now(UTC).isoformat()
    state["status"] = "COMPLETE" if len(state["records"]) == len(universe) and "stop_reason" not in state else "STOPPED"
    state["downloaded"] = sum(r["status"] == "DOWNLOADED" for r in state["records"])
    state["reused"] = sum(r["status"] == "REUSED_VERIFIED" for r in state["records"])
    save(ROOT / "acquisition.json", state)
    print(json.dumps({k: v for k, v in state.items() if k != "records"}), flush=True)


if __name__ == "__main__":
    main()
