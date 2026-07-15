from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _entrypoint():
    spec = importlib.util.spec_from_file_location("sombra_operational_provenance", ROOT / "scripts" / "sombra_diaria.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shadow_consumer_provenance_identifies_turn_and_inputs() -> None:
    metadata = _entrypoint().consumer_provenance("brasileirao-sombra-manha")
    assert metadata["project_name"] == "brasileirao-predictor"
    assert metadata["execution_turn"] == "morning"
    assert metadata["artifact_schema_version"] == "operational-envelope/1.1"
    assert all(len(value) == 64 for value in metadata["input_hashes"].values())
    assert "tools_version" not in metadata and "tools_commit" not in metadata
