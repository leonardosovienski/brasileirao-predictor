"""Observable Task Scheduler entrypoint for the Brasileirao shadow routine."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

# `pythonw.exe` (executavel de toda tarefa agendada) nao tem console: um
# processo de console filho ganharia janela VISIVEL na tela do dono.
# Saida ja e capturada, entao a flag nao esconde nada.
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = Path(__file__).with_name("sombra_diaria_payload.py")
# Runtime mutable: heartbeats/logs must never dirty the source worktree.
# Historical tracked evidence remains in logs/operations; new writes go here.
LOG_DIR = ROOT / "data" / "runtime" / "operations"
_GIT_RUN = subprocess.run


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"provenance input is missing: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    result = _GIT_RUN(["git", "-C", str(ROOT), *args], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("project Git provenance is unavailable")
    return result.stdout.strip()


def consumer_provenance(task_name: str, root: Path = ROOT) -> dict[str, object]:
    branch = _git("branch", "--show-current") or None
    return {
        "project_name": "brasileirao-predictor",
        "project_commit": _git("rev-parse", "HEAD"),
        "project_branch": branch,
        "project_worktree_clean": not bool(_git("status", "--porcelain")),
        "predictor_core_version": version("predictor-core"),
        "predictor_ops_version": version("predictor-ops"),
        "input_hashes": {
            "matches_database": _sha256(root / "data" / "matches.db"),
            "teams": _sha256(root / "data" / "teams_brasileirao.json"),
        },
        "artifact_schema_version": "operational-envelope/1.1",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "task_name": task_name,
        "execution_turn": "morning" if task_name.endswith("manha") else "night",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the shadow routine with the operational envelope.")
    parser.add_argument(
        "--task-name",
        required=True,
        choices=("brasileirao-sombra-manha", "brasileirao-sombra-noite"),
    )
    args = parser.parse_args(argv)
    if not PAYLOAD.is_file():
        print("operational entrypoint is incomplete", file=sys.stderr)
        return 3
    try:
        metadata = json.dumps(consumer_provenance(args.task_name), ensure_ascii=False, sort_keys=True)
    except (OSError, RuntimeError) as exc:
        print(f"consumer provenance unavailable: {exc}", file=sys.stderr)
        return 3
    command = [
        sys.executable,
        "-m",
        "predictor_ops",
        "run",
        "--job-id",
        args.task_name,
        "--runtime-root",
        str(LOG_DIR),
        "--command",
        "--",
        sys.executable,
        "-X",
        "utf8",
        str(PAYLOAD),
    ]
    environment = os.environ.copy()
    environment["BRASILEIRAO_CAPTURE_TURN"] = json.loads(metadata)["execution_turn"]
    return subprocess.run(command, cwd=ROOT, env=environment, check=False, creationflags=_NO_WINDOW).returncode


if __name__ == "__main__":
    raise SystemExit(main())
