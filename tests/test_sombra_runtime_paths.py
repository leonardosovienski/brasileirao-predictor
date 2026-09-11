import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shadow_runner_uses_ignored_runtime_operations_directory():
    spec = importlib.util.spec_from_file_location(
        "sombra_diaria_paths", ROOT / "brasileirao_scripts" / "sombra_diaria.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.LOG_DIR == ROOT.parent / "runtime" / "operations"
    assert not module.LOG_DIR.is_relative_to(ROOT)


def test_external_project_and_runtime_roots_are_explicit(tmp_path, monkeypatch):
    from brasileirao_predictor.paths import project_root, runtime_root

    monkeypatch.setenv("BRASILEIRAO_PROJECT_ROOT", str(tmp_path / "application"))
    monkeypatch.setenv("BRASILEIRAO_RUNTIME_ROOT", str(tmp_path / "state"))
    assert project_root() == tmp_path / "application"
    assert runtime_root() == tmp_path / "state"
    assert not (tmp_path / "application").exists()


def test_shadow_payload_invokes_installed_modules():
    from brasileirao_scripts.sombra_diaria_payload import PASSOS

    assert all("-m" in command for _, command, _ in PASSOS)
    assert not any(part.endswith(".py") for _, command, _ in PASSOS for part in command)
