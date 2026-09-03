"""Shared dependencies must be installed distributions, never vendored copies."""

from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shared_packages_are_supported_versions() -> None:
    assert version("predictor-core").startswith("3.1.")
    assert version("predictor-ops").startswith("4.0.")


def test_vendor_does_not_return() -> None:
    assert not (ROOT / "vendor").exists()


def test_ci_does_not_depend_on_workspace_imports() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    forbidden = ("PYTHONPATH", "ln -s", "../tools", "|| true", "continue-on-error")
    assert all(token not in workflow for token in forbidden)
