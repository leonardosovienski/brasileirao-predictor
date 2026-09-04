from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "brasileirao_scripts" / "install_windows_scheduler.ps1"
JOBS = ROOT / "jobs.market-research.example.json"


def test_scheduler_installer_uses_every_manifest_job() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")
    jobs = json.loads(JOBS.read_text(encoding="utf-8"))["jobs"]

    assert len(jobs) == 11
    assert "foreach ($job in $manifest.jobs)" in installer
    assert "Install-PredictorTask -Name ([string]$job.id)" in installer


def test_scheduler_installer_keeps_model_cache_alive() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")

    assert '"brasileirao-model-update"' in installer
    assert '-Module "brasileirao_predictor.cron_update_models"' in installer
    assert '$arguments = "-X utf8 -m $Module"' in installer


def test_scheduler_registration_fails_high() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")

    assert installer.count("Register-ScheduledTask") == 3
    assert installer.count("Register-ScheduledTask -TaskName $Name") == 3
    assert installer.count("-Force -ErrorAction Stop") == 3


def test_scheduler_disables_stale_h11_and_audits_repository_root() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")
    assert '"brasileirao-h11-1x2-shadow"' in installer
    assert "tarefas apontando para outro repositorio" in installer


def test_scheduler_installer_declares_20_unique_tasks() -> None:
    jobs = {job["id"] for job in json.loads(JOBS.read_text(encoding="utf-8"))["jobs"]}
    direct = {
        "brasileirao-market-research",
        "brasileirao-model-update",
        "brasileirao-h9-emit",
        "brasileirao-h9-closing",
        "brasileirao-h9-settle",
        "brasileirao-h9-backup",
        "brasileirao-h9-missed-window",
        "brasileirao-h14-persist",
        "brasileirao-h15-persist",
    }

    assert len(jobs | direct) == 20


def test_scheduler_installer_covers_h14_and_h15_persistence() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")
    assert '"brasileirao-h14-persist"' in installer
    assert '"brasileirao-h15-persist"' in installer
    assert "persist_h14_prospective.py" in installer
    assert "persist_h15_prospective.py" in installer
