"""Explicit application data/configuration root, separate from installed code."""

import os
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent


def project_root() -> Path:
    value = os.environ.get("BRASILEIRAO_PROJECT_ROOT")
    if value is None:
        return SOURCE_ROOT  # compatibility for explicitly invoked legacy checkout commands
    root = Path(value).expanduser()
    if not root.is_absolute():
        raise ValueError("BRASILEIRAO_PROJECT_ROOT must be absolute")
    return root.resolve()


def runtime_root() -> Path:
    root = Path(os.environ.get("BRASILEIRAO_RUNTIME_ROOT", project_root().parent / "runtime"))
    if not root.is_absolute():
        raise ValueError("BRASILEIRAO_RUNTIME_ROOT must be absolute")
    if root.resolve().is_relative_to(SOURCE_ROOT):
        raise ValueError("runtime must be outside the source checkout or installation")
    return root.resolve()
