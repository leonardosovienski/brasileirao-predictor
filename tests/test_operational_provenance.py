from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _entrypoint():
    spec = importlib.util.spec_from_file_location("sombra_operational_provenance", ROOT / "scripts" / "sombra_diaria.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(
    not (ROOT / "data" / "matches.db").is_file(),
    reason="matches.db é artefato operacional local (gitignored); ausente num clone fresco de CI",
)
def test_shadow_consumer_provenance_identifies_turn_and_inputs() -> None:
    metadata = _entrypoint().consumer_provenance("brasileirao-sombra-manha")
    assert metadata["project_name"] == "brasileirao-predictor"
    assert metadata["execution_turn"] == "morning"
    assert metadata["artifact_schema_version"] == "operational-envelope/1.1"
    assert all(len(value) == 64 for value in metadata["input_hashes"].values())
    assert "tools_version" not in metadata and "tools_commit" not in metadata


def test_entrypoint_propagates_capture_turn(monkeypatch) -> None:
    module = _entrypoint()
    metadata = {
        "execution_turn": "night", "project_name": "brasileirao-predictor"
    }
    monkeypatch.setattr(module, "consumer_provenance", lambda _task: metadata)
    observed = {}

    class Result:
        returncode = 0

    def fake_run(command, **kwargs):
        observed.update(kwargs)
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.main(["--task-name", "brasileirao-sombra-noite"]) == 0
    assert observed["env"]["BRASILEIRAO_CAPTURE_TURN"] == "night"
