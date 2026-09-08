"""Independent acquisition checks; all network and secrets are replaced."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("independent_ext51_acquire", SOURCE / "acquire.py")
acquire = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acquire)


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    for name in ("plan.json", "selection.json"):
        (tmp_path / name).write_bytes((SOURCE / name).read_bytes())
    monkeypatch.setattr(acquire, "ROOT", tmp_path)
    monkeypatch.setattr(acquire, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(acquire, "_key", lambda: "independent-synthetic-key")
    monkeypatch.setattr(acquire, "quota", lambda key: {"request_count": 62, "request_limit": 250})
    requests, sleeps = [], []
    monkeypatch.setattr(acquire.time, "sleep", sleeps.append)

    def install(statuses, *, identity_mismatch=False, leak=False):
        def get(url, params, timeout):
            index = len(requests)
            requests.append({"url": url, "params": params, "timeout": timeout})
            status = statuses[index] if index < len(statuses) else statuses[-1]
            payload = {"fixtureId": "wrong" if identity_mismatch else params["fixtureId"]}
            if leak:
                payload["example"] = params["apiKey"]
            return SimpleNamespace(status_code=status, content=json.dumps(payload).encode(), json=lambda: payload)
        monkeypatch.setattr(acquire.requests, "get", get)

    return tmp_path, requests, sleeps, install


def test_three_rate_errors_stop_without_retry(isolated):
    directory, requests, sleeps, install = isolated
    install([429])
    acquire.main()
    manifest = json.loads((directory / "manifest.json").read_text())
    assert len(requests) == 3
    assert len({r["params"]["fixtureId"] for r in requests}) == 3
    assert sleeps == [30, 30]
    assert manifest["attempted_count"] == 3
    assert manifest["unattempted_count"] == 48
    assert manifest["status"] == "STOP_PROVIDER_ERROR_NO_RETRY"
    assert not list((directory / "raw").iterdir())


@pytest.mark.parametrize("status", [401, 402, 403])
def test_auth_and_payment_failures_stop_on_first_attempt(isolated, status):
    directory, requests, sleeps, install = isolated
    install([status])
    acquire.main()
    manifest = json.loads((directory / "manifest.json").read_text())
    assert len(requests) == 1 and not sleeps
    assert manifest["unattempted_count"] == 50


def test_complete_success_matches_frozen_ids_once_and_rate_pacing(isolated):
    directory, requests, sleeps, install = isolated
    install([200])
    acquire.main()
    selection = json.loads((directory / "selection.json").read_text())
    manifest = json.loads((directory / "manifest.json").read_text())
    assert [r["params"]["fixtureId"] for r in requests] == [r["fixture_id"] for r in selection]
    assert all(r["params"]["bookmakers"] == "pinnacle" for r in requests)
    assert all(r["url"].endswith("/historical-odds") for r in requests)
    assert sleeps == [7] * 50
    assert manifest["saved_count"] == 51
    assert len(list((directory / "raw").glob("*.json"))) == 51


@pytest.mark.parametrize("flag", ["identity_mismatch", "leak"])
def test_rejected_body_is_never_saved(isolated, flag, capsys):
    directory, requests, sleeps, install = isolated
    install([200], **{flag: True})
    acquire.main()
    manifest = json.loads((directory / "manifest.json").read_text())
    assert len(requests) == 51 and manifest["saved_count"] == 0
    assert not list((directory / "raw").iterdir())
    assert all(r["status"] == "EXCEPTION_NO_RETRY" for r in manifest["records"])
    assert "independent-synthetic-key" not in capsys.readouterr().out


def test_existing_manifest_prevents_any_new_request(isolated):
    directory, requests, sleeps, install = isolated
    install([200])
    (directory / "manifest.json").write_text("{}")
    assert acquire.main() == 2
    assert requests == [] and sleeps == []


def test_changed_frozen_selection_prevents_any_request(isolated):
    directory, requests, sleeps, install = isolated
    install([200])
    (directory / "selection.json").write_text("[]")
    assert acquire.main() == 2
    assert requests == [] and sleeps == []
