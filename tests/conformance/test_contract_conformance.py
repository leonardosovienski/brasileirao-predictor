"""Conformance of the Brasileirão research contract through the INSTALLED entrypoint.

Gates: E2E, PROVENANCE, ADMISSION, IDEMPOTENCY, AUTHORITY_SEPARATION, CAPITAL_FORBIDDEN,
OPS_RUNTIME, CORE_PARTICIPATION. Every request is a file processed by `brasileirao-research`
in a fresh process; the result is re-read by another fresh process (`show`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from brasileirao_predictor.research_runtime.contract import ContractError, validate_result

from . import fixtures
from .harness import Lab, cli, standard_lab


@pytest.fixture(scope="module")
def lab():
    value = standard_lab()
    yield value
    value.cleanup()


def _ops_events(state: Path) -> list[dict]:
    rows = []
    for events in (state / "x" / "o").glob("*/events.jsonl"):
        rows += [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows


def test_e2e_file_request_to_result_and_reread_after_restart(lab: Lab) -> None:
    request = fixtures.request("brasileirao:REQ-E2E-001", client_ref={"ticket": 7, "note": "opaque"})
    code, outcome = lab.submit(request)
    assert code == 0 and outcome["status"] == "RESULT", outcome
    assert outcome["client_ref"] == {"ticket": 7, "note": "opaque"}
    assert outcome["capital_permission"] is False
    # Restart: a NEW process re-reads the authoritative result, never recomputes it.
    code, shown = lab.show("brasileirao:REQ-E2E-001")
    assert code == 0 and shown["source"] == "authoritative_result_store"
    result = validate_result(shown["result"])
    code2, shown2 = lab.show("brasileirao:REQ-E2E-001")
    assert code2 == 0 and shown2["result_sha256"] == shown["result_sha256"]
    assert result["result_id"] == outcome["result_id"] and result["request_id"] == request["request_id"]
    for field in ("result_id", "request_id", "admission_id", "experiment_id", "research_id", "hypothesis_id"):
        assert result[field].startswith("brasileirao:"), field
    # Core participation: the scientific state is the Core trial row; replay drove the time axis.
    core = result["core_facts"]
    assert core["scientific_state_source"] == "core_trial_registry"
    assert core["trial_ids"] and core["trial_ids"][0].startswith("brasileirao:TRIAL-")
    assert core["temporal_validation"]["engine"] == "predictor_core.measurement.replay"
    assert core["temporal_validation"]["max_used_minus_cutoff_seconds"] < 0
    assert core["temporal_validation"]["db_caches_read"] == []
    # Ops participation: a real job of the Ops CLI, FORECAST_GENERATION, never EXECUTION.
    ops = result["ops_facts"]
    assert ops["mechanism"].startswith("jobs file schema_version 3")
    assert ops["job_type"] == "FORECAST_GENERATION" and ops["operational_state"] == "SUCCEEDED"
    assert ops["library_provenance"]["mode"] == "strict" and ops["library_provenance"]["identity_status"] == "VALIDATED"
    events = [e for e in _ops_events(lab.state) if e.get("run_id") == ops["ops_run_id"]]
    assert (
        events
        and events[-1]["run_status"] == "SUCCEEDED"
        and events[-1]["provenance"]["request_id"] == request["request_id"]
    )
    # Provenance: request -> admission -> experiment -> trial -> ops run -> effect -> result.
    prov = result["provenance"]
    assert prov["admission_policy_id"] == "brasileirao-research-qualification"
    assert len(prov["request_content_hash"]) == 64 and len(prov["logical_experiment_hash"]) == 64
    assert set(result["domain_facts"]["references"]) == {
        "dataset",
        "model",
        "features",
        "baseline",
        "cost_model",
        "odds",
    }
    assert result["domain_facts"]["effect_sha256"]
    assert result["domain_facts"]["predictions"], "no prediction in the result"
    assert result["scientific_state"] in {"SUPPORTED", "REFUTED", "INCONCLUSIVE"}


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda r: r | {"hypothesis_id": "brasileirao:H9"}, "PROTECTED_HYPOTHESIS"),
        (lambda r: r | {"hypothesis_id": "brasileirao:A1"}, "PROTECTED_HYPOTHESIS"),
        (lambda r: r | {"hypothesis_id": "brasileirao:HX-UNKNOWN"}, "HYPOTHESIS_NOT_ADMITTED"),
        (
            lambda r: (
                r
                | {
                    "season": 2025,
                    "events": {"kickoff_from": "2025-06-01T00:00:00Z", "kickoff_to": "2025-07-01T00:00:00Z"},
                }
            ),
            "HOLDOUT_SEALED",
        ),
        (
            lambda r: (
                r
                | {
                    "season": 2024,
                    "events": {"kickoff_from": "2024-12-01T00:00:00Z", "kickoff_to": "2025-01-02T00:00:00Z"},
                }
            ),
            "HOLDOUT_SEALED",
        ),
        (
            lambda r: (
                r
                | {
                    "season": 2019,
                    "events": {"kickoff_from": "2019-06-01T00:00:00Z", "kickoff_to": "2019-07-01T00:00:00Z"},
                }
            ),
            "SEASON_NOT_ALLOWED",
        ),
        (
            lambda r: r | {"events": {"kickoff_from": "2022-06-01T00:00:00Z", "kickoff_to": "2023-02-01T00:00:00Z"}},
            "WINDOW_OUTSIDE_SEASON",
        ),
        (
            lambda r: r | {"references": r["references"] | {"model": {"name": "other-model", "version": "1"}}},
            "REFERENCE_UNAUTHORIZED_OR_UNKNOWN",
        ),
        (lambda r: r | {"command": ["python", "-c", "print(1)"]}, "SCHEMA_INVALID"),
        (lambda r: r | {"handler": "brasileirao.handlers.walkforward_forecast_evaluation.v1"}, "SCHEMA_INVALID"),
        (lambda r: r | {"module": "os"}, "SCHEMA_INVALID"),
        (lambda r: r | {"sql": "DROP TABLE matches"}, "SCHEMA_INVALID"),
        (lambda r: r | {"path": "C:/BRASILEIRAO/brasileirao-predictor/data/matches.db"}, "SCHEMA_INVALID"),
        (lambda r: r | {"url": "https://example.invalid"}, "SCHEMA_INVALID"),
        (lambda r: r | {"capital_permission": True}, "SCHEMA_INVALID"),
        (lambda r: r | {"request_type": "EXECUTE_BET"}, "REQUEST_TYPE_NOT_ALLOWED"),
        (lambda r: r | {"request_id": "H9"}, "SCHEMA_INVALID"),
        (lambda r: r | {"data_cutoff": "2023-10-01T00:00:00"}, "SCHEMA_INVALID"),
        (lambda r: r | {"data_cutoff": "2023-10-01T00:00:00-03:00"}, "SCHEMA_INVALID"),
        (lambda r: r | {"decision_lead_minutes": 5}, "PARAMETER_OUT_OF_BOUNDS"),
        (lambda r: r | {"target": "CORRECT_SCORE"}, "SCHEMA_INVALID"),
    ],
)
def test_admission_rejects_before_any_execution(lab: Lab, mutate, reason: str, request) -> None:
    rid = f"brasileirao:REQ-ADM-{request.node.callspec.indices['mutate']:02d}"
    base = fixtures.request(rid)
    candidate = mutate(base)
    code, outcome = lab.submit(candidate)
    assert code == 2 and outcome["status"] == "REJECTED", outcome
    assert outcome["reason"] == reason, outcome
    shown_code, shown = lab.show(
        candidate.get("request_id", rid) if isinstance(candidate.get("request_id"), str) else rid
    )
    assert shown_code == 3 and shown["status"] == "NOT_FOUND"


def test_invalid_json_duplicate_keys_nan_and_oversize_are_rejected(lab: Lab) -> None:
    raw_cases = {
        "dup": b'{"request_id": "brasileirao:REQ-DUP", "request_id": "brasileirao:REQ-DUP2"}',
        "nan": b'{"request_id": NaN}',
        "notjson": b"\xff\xfe not json",
        "big": b"{" + b" " * (256 * 1024 + 10) + b"}",
    }
    for name, raw in raw_cases.items():
        path = lab.root / "req" / f"raw-{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        code, lines, _stderr = lab.process(path)
        assert code == 2 and lines[-1]["status"] == "REJECTED", (name, lines)


def test_idempotency_duplicate_conflict_and_single_effect(lab: Lab) -> None:
    request = fixtures.request("brasileirao:REQ-IDEM-001", target="OU25", client_ref="first")
    code, first = lab.submit(request)
    assert code == 0 and first["status"] == "RESULT"
    code, again = lab.submit(request | {"client_ref": "second"})
    assert code == 0 and again["status"] == "DUPLICATE" and again["result_id"] == first["result_id"]
    assert again["client_ref"] == "second"
    code, conflict = lab.submit(request | {"decision_lead_minutes": 90})
    assert code == 2 and conflict["status"] == "CONFLICT"
    successes = [
        e
        for e in _ops_events(lab.state)
        if e.get("run_status") == "SUCCEEDED" and e["provenance"]["request_id"] == request["request_id"]
    ]
    assert len(successes) == 1
    code, shown = lab.show(request["request_id"])
    assert shown["result"]["result_id"] == first["result_id"]


def test_duplicate_after_policy_change_returns_the_stored_result() -> None:
    lab = standard_lab()
    try:
        request = fixtures.request("brasileirao:REQ-POLICY-CHANGE")
        code, first = lab.submit(request)
        assert code == 0 and first["status"] == "RESULT"
        lab.write_policy(max_request_bytes=32768)
        code, again = lab.submit(request)
        assert code == 0 and again["status"] == "DUPLICATE" and again["result_id"] == first["result_id"]
    finally:
        lab.cleanup()


def test_authority_separation_invariants_are_enforced_by_the_contract() -> None:
    lab = standard_lab()
    try:
        _code, outcome = lab.submit(fixtures.request("brasileirao:REQ-AUTH-001"))
        _code, shown = lab.show("brasileirao:REQ-AUTH-001")
    finally:
        lab.cleanup()
    result = shown["result"]
    # Ops failure never carries science or edge; science never implies edge; edge never capital.
    for broken in (
        result | {"operational_state": "FAILED"},
        result | {"economic_state": "WATCH", "scientific_state": "INCONCLUSIVE"},
        result | {"result_state": "WATCH_NO_CAPITAL", "economic_state": "NO_EDGE"},
        result | {"capital_permission": True},
        result | {"result_state": "FORECAST_ONLY"},
        result | {"request_id": "H9"},
    ):
        with pytest.raises(ContractError):
            validate_result(broken)
    assert outcome["capital_permission"] is False


def test_forecast_only_for_future_events_makes_no_scientific_claim() -> None:
    """Events after the data cutoff are forecast with information strictly before the cutoff."""
    lab = standard_lab()
    try:
        request = fixtures.request(
            "brasileirao:REQ-FORECAST-001",
            kickoff_from="2023-07-01T00:00:00Z",
            kickoff_to="2023-09-01T00:00:00Z",
            data_cutoff="2023-06-30T00:00:00Z",
        )
        code, outcome = lab.submit(request)
        assert code == 0, outcome
        _c, shown = lab.show(request["request_id"])
    finally:
        lab.cleanup()
    result = shown["result"]
    predictions = result["domain_facts"]["predictions"]
    assert predictions and all(p["cutoff"] == "2023-06-30T00:00:00Z" for p in predictions)
    assert result["domain_facts"]["evaluation"]["n_evaluated"] >= 30  # labels exist in the snapshot


def test_capital_is_forbidden_everywhere() -> None:
    lab = standard_lab()
    try:
        lab.submit(fixtures.request("brasileirao:REQ-CAPITAL-001"))
        jobs = list((lab.state / "x" / "e").glob("*/ops-job.*.json"))
        assert jobs
        for path in jobs:
            job = json.loads(path.read_text(encoding="utf-8"))["jobs"][0]
            assert job["capital_permission"] is False and job["job_type"] != "EXECUTION"
        outcome_files = list((lab.state / "outcomes").glob("*.json"))
        assert outcome_files and all(
            json.loads(p.read_text(encoding="utf-8")).get("capital_permission", False) is False for p in outcome_files
        )
    finally:
        lab.cleanup()


def test_entrypoint_needs_no_checkout_or_project_root(tmp_path: Path) -> None:
    """The installed entrypoint reads nothing from a checkout: no config.yaml, no .git, no data/."""
    done = cli("--help")
    assert done.returncode == 0 and "brasileirao-research" in done.stdout
    import brasileirao_predictor.research_runtime as package

    for module in Path(package.__file__).parent.glob("*.py"):
        source = module.read_text(encoding="utf-8")
        for forbidden in (
            "project_root(",
            "SOURCE_ROOT",
            "load_config",
            "BRASILEIRAO_PROJECT_ROOT",
            '"git"',
            "matches.db",
        ):
            assert forbidden not in source, (module.name, forbidden)
