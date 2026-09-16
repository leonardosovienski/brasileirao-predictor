"""Contract regressions: synthetic metadata only, never protected cohorts."""

import json
from unittest.mock import Mock

import pytest

from brasileirao_scripts import evaluate_h14_prospective as h14
from brasileirao_scripts import evaluate_h15_prospective as h15
from brasileirao_scripts._prospective_evaluation_guard import EvaluationBlocked, claim_directory


@pytest.mark.parametrize("job", [h14, h15])
@pytest.mark.parametrize(
    "declared",
    [
        ["log_loss", "brier_1x2", "brier_ou25"],
        None,
        [],
        ["log_loss"],
        ["log_loss", "log_loss"],
        [[], "brier_1x2"],
    ],
)
def test_incompatible_protocol_blocks_before_claim_or_cohort_reads(job, declared, tmp_path, monkeypatch):
    registry = tmp_path / "trials.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "name": job.TRIAL,
                    "params": {"primary_metric": "rps", "guardrails": declared, "min_n_avaliacao": 900},
                }
            ]
        ),
        encoding="utf-8",
    )
    ledger = tmp_path / "unread-cohort.jsonl"
    database = tmp_path / "unread-results.db"
    forbidden = Mock(side_effect=AssertionError("cohort access forbidden"))
    monkeypatch.setattr(job, "_load_jsonl", forbidden)
    monkeypatch.setattr(job.db, "connect", forbidden)
    monkeypatch.setattr(job, "load_config", forbidden)
    with pytest.raises(EvaluationBlocked, match="metric mismatch"):
        job.evaluate(trials_path=registry, ledger_path=ledger, db_path=database, reports_dir=tmp_path / "reports")
    forbidden.assert_not_called()
    assert not claim_directory(trial=job.TRIAL, ledger_path=ledger).exists()
    assert list(tmp_path.iterdir()) == [registry]


@pytest.mark.parametrize("job", [h14, h15])
def test_cli_blocks_unsupported_protocol_without_output_or_claim(job, tmp_path, monkeypatch, capsys):
    registry = tmp_path / "trials.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "name": job.TRIAL,
                    "params": {
                        "primary_metric": "rps",
                        "guardrails": ["log_loss", "brier_1x2", "brier_ou25"],
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(job, "TRIALS_PATH", registry)
    monkeypatch.setattr(job, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(job, "REPORTS_DIR", tmp_path / "reports")
    assert job.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "brier_ou25" in captured.err
    assert list(tmp_path.iterdir()) == [registry]


@pytest.mark.parametrize("job", [h14, h15])
@pytest.mark.parametrize("interval", [[-0.1, 0.1], [-0.1, 0.0], [0.0, 0.0]])
def test_zero_interval_does_not_assert_equivalence_or_strict_negativity(job, interval):
    status, detail = job._verdict({"ci95": interval}, {})
    assert status == "refutada"  # Existing native decision rule is preserved.
    assert "não prova equivalência" in detail
    assert "estritamente negativo" not in detail


@pytest.mark.parametrize("job", [h14, h15])
@pytest.mark.parametrize("interval", [None, [None, None], [float("nan"), 0.1], [0.2, 0.1]])
def test_missing_or_invalid_guardrail_cannot_approve(job, interval):
    guardrails = {"log_loss": {"ci95": [0.01, 0.1]}}
    if interval is not None:
        guardrails["brier_1x2"] = {"ci95": interval}
    status, _ = job._verdict({"ci95": [0.01, 0.1]}, guardrails)
    assert status == "inconclusiva"


@pytest.mark.parametrize("job", [h14, h15])
def test_complete_guardrails_keep_existing_individual_decision(job):
    guardrails = {metric: {"ci95": [0.01, 0.1]} for metric in job.GUARDRAIL_METRICS}
    assert job._verdict({"ci95": [0.01, 0.1]}, guardrails)[0] == "comprovada"
    guardrails["log_loss"]["ci95"] = [-0.2, -0.1]
    assert job._verdict({"ci95": [0.01, 0.1]}, guardrails)[0] == "refutada"
