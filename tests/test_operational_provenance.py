from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _entrypoint():
    path = ROOT / "brasileirao_scripts" / "sombra_diaria.py"
    spec = importlib.util.spec_from_file_location("sombra_operational_provenance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shadow_consumer_provenance_identifies_turn_and_inputs(tmp_path: Path, monkeypatch) -> None:
    data = tmp_path / "data"
    data.mkdir()
    with sqlite3.connect(data / "matches.db") as conn:
        conn.execute("CREATE TABLE fixture(value)")
    (data / "teams_brasileirao.json").write_text("{}", encoding="utf-8")

    module = _entrypoint()
    monkeypatch.setattr(module, "LOG_DIR", tmp_path / "runtime")
    metadata = module.consumer_provenance("brasileirao-sombra-manha", root=tmp_path)
    assert metadata["project_name"] == "brasileirao-predictor"
    assert metadata["execution_turn"] == "morning"
    assert metadata["artifact_schema_version"] == "operational-envelope/1.1"
    assert all(len(value) == 64 for value in metadata["input_hashes"].values())
    assert "tools_version" not in metadata and "tools_commit" not in metadata


def test_entrypoint_propagates_capture_turn(monkeypatch, tmp_path) -> None:
    module = _entrypoint()
    monkeypatch.setattr(module, "LOG_DIR", tmp_path / "runtime")
    metadata = {"execution_turn": "night", "project_name": "brasileirao-predictor"}
    monkeypatch.setattr(module, "consumer_provenance", lambda _task: metadata)
    observed = {}

    class Result:
        returncode = 0

    def fake_run(command, **kwargs):
        observed.update(kwargs)
        config = json.loads(Path(command[command.index("--config") + 1]).read_text())
        assert config["jobs"][0]["provenance"] == metadata
        assert config["jobs"][0]["command"][-1] == "brasileirao_scripts.sombra_diaria_payload"
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.main(["--task-name", "brasileirao-sombra-noite"]) == 0
    assert observed["env"]["BRASILEIRAO_CAPTURE_TURN"] == "night"
