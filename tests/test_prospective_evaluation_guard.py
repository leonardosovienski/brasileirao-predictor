"""One-shot governance regression tests using only temporary synthetic artifacts."""

import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import Mock

import pytest

from brasileirao_scripts import _prospective_evaluation_guard as guard
from brasileirao_scripts import evaluate_h14_prospective as h14
from brasileirao_scripts import evaluate_h15_prospective as h15

JOBS = [(h14, "h14"), (h15, "h15")]
WAITING = {"status": "AGUARDANDO_N", "n": 3, "min_n_avaliacao": 900, "faltam": 897}
COMPLETE = {"status": "INCONCLUSIVA", "n": 900, "capital_enabled": False, "synthetic": True}


@pytest.fixture(autouse=True)
def isolate_default_cohorts(tmp_path, monkeypatch):
    for job, prefix in JOBS:
        monkeypatch.setattr(job, "LEDGER_PATH", tmp_path / "inputs" / prefix / "ledger.jsonl")
        monkeypatch.setattr(job, "TRIALS_PATH", tmp_path / "inputs" / prefix / "trials.json")
        monkeypatch.setattr(job, "REPORTS_DIR", tmp_path / "defaults" / prefix / "reports")


def claim_file(job, prefix):
    directory = guard.claim_directory(trial=job.TRIAL, ledger_path=job.LEDGER_PATH)
    return directory / f".{prefix}_evaluation.claim.json"


@pytest.mark.parametrize(("job", "prefix"), JOBS)
def test_existing_report_blocks_cli_before_dispatch_and_stdout(job, prefix, tmp_path, monkeypatch, capsys):
    report = tmp_path / f"{prefix}_avaliacao_2027-01-01T000000Z.json"
    report.write_text('{"synthetic": true}\n', encoding="utf-8")
    original = report.read_bytes()
    calculate = Mock(side_effect=AssertionError("must not evaluate"))
    monkeypatch.setattr(job, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(job, "evaluate", calculate)
    assert job.main() == 1
    calculate.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Nenhuma avaliação foi executada" in captured.err
    assert report.read_bytes() == original
    assert list(tmp_path.iterdir()) == [report]


@pytest.mark.parametrize(("job", "prefix"), JOBS)
def test_existing_report_blocks_direct_api_before_any_input_reads(job, prefix, tmp_path, monkeypatch):
    (tmp_path / f"{prefix}_avaliacao_old.json").write_text("{}", encoding="utf-8")
    calculate = Mock(side_effect=AssertionError("must not read registry, DB or ledger"))
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    with pytest.raises(guard.EvaluationBlocked):
        job.evaluate(reports_dir=tmp_path)
    calculate.assert_not_called()


@pytest.mark.parametrize(("job", "prefix"), JOBS)
def test_direct_success_persists_report_and_blocks_repeat(job, prefix, tmp_path, monkeypatch):
    calculate = Mock(return_value=dict(COMPLETE))
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    assert job.evaluate(reports_dir=tmp_path) == COMPLETE
    reports = list(tmp_path.glob(f"{prefix}_avaliacao_*.json"))
    assert len(reports) == 1
    assert json.loads(reports[0].read_text(encoding="utf-8")) == COMPLETE
    assert claim_file(job, prefix).is_file()
    with pytest.raises(guard.EvaluationBlocked):
        job.evaluate(reports_dir=tmp_path)
    calculate.assert_called_once_with(trials_path=None, ledger_path=None, db_path=None)


@pytest.mark.parametrize(("job", "prefix"), JOBS)
def test_below_threshold_releases_claim_without_report_and_can_check_later(job, prefix, tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    calculate = Mock(return_value=dict(WAITING))
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    assert job.evaluate(reports_dir=reports) == WAITING
    assert job.evaluate(reports_dir=reports) == WAITING
    assert calculate.call_count == 2
    assert not reports.exists()


@pytest.mark.parametrize(("job", "prefix"), JOBS)
@pytest.mark.parametrize("failure", [ValueError("synthetic failure"), SystemExit("synthetic interruption")])
def test_error_or_interruption_keeps_claim_and_forbids_retry(job, prefix, failure, tmp_path, monkeypatch):
    calculate = Mock(side_effect=failure)
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    with pytest.raises(type(failure)):
        job.evaluate(reports_dir=tmp_path)
    assert claim_file(job, prefix).is_file()
    assert not list(tmp_path.glob(f"{prefix}_avaliacao_*.json"))
    with pytest.raises(guard.EvaluationBlocked):
        job.evaluate(reports_dir=tmp_path)
    assert calculate.call_count == 1


@pytest.mark.parametrize(("job", "prefix"), JOBS)
def test_truncated_crash_claim_blocks_without_parsing_or_opening_inputs(job, prefix, tmp_path, monkeypatch):
    claim = claim_file(job, prefix)
    claim.parent.mkdir(parents=True)
    claim.write_bytes(b'{"trial":')
    calculate = Mock(side_effect=AssertionError("must not evaluate"))
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    with pytest.raises(guard.EvaluationBlocked):
        job.evaluate(reports_dir=tmp_path)
    calculate.assert_not_called()
    assert claim.read_bytes() == b'{"trial":'


@pytest.mark.parametrize(("job", "prefix"), JOBS)
def test_report_write_failure_does_not_disclose_or_allow_another_attempt(job, prefix, tmp_path, monkeypatch, capsys):
    calculate = Mock(return_value=dict(COMPLETE))
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    monkeypatch.setattr(job, "REPORTS_DIR", tmp_path)
    original_open = Path.open

    class PartialWriteFailure:
        def __init__(self, path, stream):
            self.path = path
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def fileno(self):
            return self.stream.fileno()

        def write(self, payload):
            self.stream.write(payload[: max(1, len(payload) // 2)])
            self.stream.flush()
            assert not list(tmp_path.glob(f"{prefix}_avaliacao_*.json"))
            raise OSError("synthetic full disk after partial write")

    def fail_report(path, mode="r", *args, **kwargs):
        if path.name.startswith(f".{prefix}_avaliacao_") and path.suffix == ".pending" and mode == "x":
            return PartialWriteFailure(path, original_open(path, mode, *args, **kwargs))
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_report)
    with pytest.raises(OSError, match="synthetic"):
        job.main()
    assert capsys.readouterr().out == ""
    assert job.main() == 1
    assert capsys.readouterr().out == ""
    assert calculate.call_count == 1
    assert not list(tmp_path.glob(f"{prefix}_avaliacao_*.json"))
    assert not list(tmp_path.glob("*.pending"))


@pytest.mark.parametrize("collision", [False, True], ids=["link-unsupported", "existing-destination"])
def test_atomic_publication_failure_keeps_claim_without_overwriting_report(collision, tmp_path, monkeypatch):
    calculate = Mock(return_value=dict(COMPLETE))
    original_link = guard.os.link
    targets = []

    def fail_link(source, target):
        assert json.loads(source.read_text(encoding="utf-8")) == COMPLETE
        assert not target.exists()
        targets.append(target)
        if collision:
            target.write_bytes(b"preexisting report: do not overwrite")
            return original_link(source, target)
        raise OSError("synthetic filesystem without hardlink support")

    monkeypatch.setattr(guard.os, "link", fail_link)
    with pytest.raises(OSError):
        guard.evaluate_once(
            calculate, reports_dir=tmp_path, claim_dir=tmp_path / "claims", prefix="h14", trial="synthetic"
        )
    assert (tmp_path / "claims/.h14_evaluation.claim.json").is_file()
    assert not list(tmp_path.glob("*.pending"))
    if collision:
        assert targets[0].read_bytes() == b"preexisting report: do not overwrite"
    else:
        assert not targets[0].exists()
    with pytest.raises(guard.EvaluationBlocked):
        guard.evaluate_once(
            calculate, reports_dir=tmp_path, claim_dir=tmp_path / "claims", prefix="h14", trial="synthetic"
        )
    assert calculate.call_count == 1


def test_simultaneous_attempts_only_one_crosses_the_atomic_claim(tmp_path, monkeypatch):
    start = Barrier(2)
    original = guard.require_available
    calculate = Mock(return_value=dict(COMPLETE))

    def precheck(reports_dir, prefix, *, claim_dir):
        original(reports_dir, prefix, claim_dir=claim_dir)
        start.wait(timeout=5)  # both pass the non-atomic check, then compete

    monkeypatch.setattr(guard, "require_available", precheck)

    def attempt():
        try:
            guard.evaluate_once(
                calculate, reports_dir=tmp_path, claim_dir=tmp_path / "claims", prefix="h14", trial="synthetic"
            )
            return "completed"
        except guard.EvaluationBlocked:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt(), range(2)))
    assert sorted(results) == ["blocked", "completed"]
    assert calculate.call_count == 1
    assert len(list(tmp_path.glob("h14_avaliacao_*.json"))) == 1


def test_claims_are_scoped_to_the_trial(tmp_path):
    guard.evaluate_once(
        lambda: dict(COMPLETE), reports_dir=tmp_path, claim_dir=tmp_path / "claims", prefix="h14", trial="synthetic-14"
    )
    guard.evaluate_once(
        lambda: dict(COMPLETE), reports_dir=tmp_path, claim_dir=tmp_path / "claims", prefix="h15", trial="synthetic-15"
    )
    assert len(list(tmp_path.glob("*_avaliacao_*.json"))) == 2


@pytest.mark.parametrize(("job", "prefix"), JOBS)
def test_changing_report_directory_cannot_repeat_the_same_cohort(job, prefix, tmp_path, monkeypatch):
    calculate = Mock(return_value=dict(COMPLETE))
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    first = tmp_path / "first-output"
    second = tmp_path / "different-output"
    assert job.evaluate(reports_dir=first) == COMPLETE
    with pytest.raises(guard.EvaluationBlocked):
        job.evaluate(reports_dir=second)
    assert calculate.call_count == 1
    assert not second.exists()
    assert len(list(first.glob(f"{prefix}_avaliacao_*.json"))) == 1


@pytest.mark.parametrize(("job", "prefix"), JOBS)
@pytest.mark.parametrize("alternate_registry", [False, True], ids=["same-registry", "alternate-registry"])
def test_legacy_default_report_blocks_an_alternate_output_directory(
    job, prefix, alternate_registry, tmp_path, monkeypatch
):
    job.REPORTS_DIR.mkdir(parents=True)
    (job.REPORTS_DIR / f"{prefix}_avaliacao_old.json").write_text("{}", encoding="utf-8")
    calculate = Mock(side_effect=AssertionError("must not read the already evaluated cohort"))
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    with pytest.raises(guard.EvaluationBlocked):
        job.evaluate(
            trials_path=tmp_path / "alternate-registry.json" if alternate_registry else None,
            reports_dir=tmp_path / "alternate",
        )
    calculate.assert_not_called()


def test_path_identity_is_canonical_without_reading_files(tmp_path):
    direct = guard.claim_directory(trial="h14", ledger_path=tmp_path / "cohort/ledger.jsonl")
    redundant = guard.claim_directory(trial="h14", ledger_path=tmp_path / "cohort/../cohort/ledger.jsonl")
    assert direct == redundant
    assert not direct.exists()


@pytest.mark.parametrize(("job", "prefix"), JOBS)
def test_registry_path_change_does_not_reopen_the_same_ledger(job, prefix, tmp_path, monkeypatch):
    calculate = Mock(return_value=dict(COMPLETE))
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    assert job.evaluate(reports_dir=tmp_path / "first") == COMPLETE
    with pytest.raises(guard.EvaluationBlocked):
        job.evaluate(trials_path=tmp_path / "different-registry.json", reports_dir=tmp_path / "second")
    assert calculate.call_count == 1


@pytest.mark.parametrize(("job", "prefix"), JOBS)
def test_moving_ledger_and_claim_state_to_new_root_preserves_single_evaluation(job, prefix, tmp_path, monkeypatch):
    old_root = tmp_path / "old-computer"
    new_root = tmp_path / "new-computer"
    ledger = old_root / "data/ledger.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_bytes(b'{"synthetic":true}\n')
    calculate = Mock(return_value=dict(COMPLETE))
    monkeypatch.setattr(job, "_evaluate_claimed", calculate)
    assert (
        job.evaluate(ledger_path=ledger, trials_path=old_root / "trials.json", reports_dir=tmp_path / "first-report")
        == COMPLETE
    )
    original_claim_dir = guard.claim_directory(trial=job.TRIAL, ledger_path=ledger)
    assert original_claim_dir.is_dir()
    # Both resolved targets are exclusively owned synthetic paths under tmp_path.
    assert old_root.resolve().is_relative_to(tmp_path.resolve())
    assert new_root.resolve().is_relative_to(tmp_path.resolve())
    shutil.move(str(old_root), str(new_root))
    relocated = new_root / "data/ledger.jsonl"
    migrated_claim_dir = guard.claim_directory(trial=job.TRIAL, ledger_path=relocated)
    assert original_claim_dir.relative_to(old_root) == migrated_claim_dir.relative_to(new_root)
    assert migrated_claim_dir.is_dir()
    with pytest.raises(guard.EvaluationBlocked):
        job.evaluate(ledger_path=relocated, trials_path=new_root / "trials.json", reports_dir=tmp_path / "new-report")
    assert calculate.call_count == 1
    assert not (tmp_path / "new-report").exists()
