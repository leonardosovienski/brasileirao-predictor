import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_shadow_runner_uses_ignored_runtime_operations_directory():
    spec = importlib.util.spec_from_file_location("sombra_diaria_paths", ROOT / "scripts" / "sombra_diaria.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.LOG_DIR == ROOT / "data" / "runtime" / "operations"
