"""Repository hygiene guards for installable, non-vendored code."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(
    not (GIT and (ROOT / ".git").exists()),
    reason="git hygiene requires a Git checkout",
)


def test_no_code_file_is_gitignored() -> None:
    files = [
        path
        for package in ("src", "scripts", "tests")
        for path in (ROOT / package).rglob("*.py")
        if "__pycache__" not in path.parts and ".venv" not in path.parts
    ]
    ignored: list[str] = []
    relative = [str(path.relative_to(ROOT)) for path in files]
    for index in range(0, len(relative), 100):
        process = subprocess.run(
            [GIT, "-C", str(ROOT), "check-ignore", *relative[index : index + 100]],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode == 0:
            ignored.extend(process.stdout.splitlines())
    assert not ignored, f"Python code is ignored by Git: {ignored}"


def test_vendor_is_absent() -> None:
    assert not (ROOT / "vendor").exists()
