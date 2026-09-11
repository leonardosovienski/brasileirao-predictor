"""Observable Task Scheduler entrypoint for the Brasileirao shadow routine."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from contextlib import closing
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from brasileirao_predictor.paths import SOURCE_ROOT, project_root, runtime_root

# `pythonw.exe` (executavel de toda tarefa agendada) nao tem console: um
# processo de console filho ganharia janela VISIVEL na tela do dono.
# Saida ja e capturada, entao a flag nao esconde nada.
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

ROOT = project_root()
PAYLOAD = Path(__file__).with_name("sombra_diaria_payload.py")
# Runtime mutable: heartbeats/logs must never dirty the source worktree.
# Historical tracked evidence remains in logs/operations; new writes go here.
LOG_DIR = runtime_root() / "operations"
_GIT_RUN = subprocess.run


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"provenance input is missing: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    result = _GIT_RUN(["git", "-C", str(SOURCE_ROOT), *args], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("project Git provenance is unavailable")
    return result.stdout.strip()


def consumer_provenance(task_name: str, root: Path = ROOT) -> dict[str, object]:
    try:
        branch = _git("branch", "--show-current") or None
        commit = _git("rev-parse", "HEAD")
        clean = not bool(_git("status", "--porcelain"))
    except (OSError, RuntimeError):
        branch = commit = clean = None
    config_path = Path(os.environ.get("BRASILEIRAO_CONFIG_PATH", root / "config.yaml"))
    if config_path.is_file():
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        database = root / config["database"]
    else:
        database = root / "data" / "matches.db"
    if (
        os.environ.get("BRASILEIRAO_DATABASE_PATH")
        and Path(os.environ["BRASILEIRAO_DATABASE_PATH"]).resolve() != database.resolve()
    ):
        raise ValueError("database override differs from payload configuration")
    teams = Path(os.environ.get("BRASILEIRAO_TEAMS_PATH", root / "data" / "teams_brasileirao.json"))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="provenance-", dir=LOG_DIR) as directory:
        snapshot = Path(directory) / "matches.sqlite"
        with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as target:
                source.backup(target)
        database_hash = _sha256(snapshot)
    return {
        "project_name": "brasileirao-predictor",
        "project_commit": commit,
        "project_branch": branch,
        "project_worktree_clean": clean,
        "predictor_core_version": version("predictor-core"),
        "predictor_ops_version": version("predictor-ops"),
        "input_hashes": {
            "matches_database": database_hash,
            "teams": _sha256(teams),
        },
        "artifact_schema_version": "operational-envelope/1.1",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "task_name": task_name,
        "execution_turn": "morning" if task_name.endswith("manha") else "night",
        "input_scope": "consistent SQLite backup at capture time; payload may observe later commits",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the shadow routine with the operational envelope.")
    parser.add_argument(
        "--check", action="store_true", help="Check distribution through Ops without running acquisition"
    )
    parser.add_argument(
        "--task-name",
        required=True,
        choices=("brasileirao-sombra-manha", "brasileirao-sombra-noite"),
    )
    args = parser.parse_args(argv)
    job_id = args.task_name + ("-check" if args.check else "")
    if not (SOURCE_ROOT / ".git").exists() and "BRASILEIRAO_PROJECT_ROOT" not in os.environ:
        print("installed shadow requires explicit BRASILEIRAO_PROJECT_ROOT", file=sys.stderr)
        return 3
    if not PAYLOAD.is_file():
        print("operational entrypoint is incomplete", file=sys.stderr)
        return 3
    try:
        metadata = json.dumps(consumer_provenance(args.task_name), ensure_ascii=False, sort_keys=True)
    except (OSError, RuntimeError, ValueError, KeyError, sqlite3.Error) as exc:
        print(f"consumer provenance unavailable: {exc}", file=sys.stderr)
        return 3
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    config_path = LOG_DIR / ("job-" + uuid.uuid4().hex + ".json")
    payload_command = [sys.executable, "-X", "utf8", "-m", "brasileirao_scripts.sombra_diaria_payload"]
    if args.check:
        payload_command.append("--check")
    with config_path.open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "schema_version": "3",
                "jobs": [
                    {
                        "id": job_id,
                        "command": payload_command,
                        "provenance": json.loads(metadata),
                        "runtime": {"root": str(LOG_DIR)},
                    }
                ],
            },
            stream,
            ensure_ascii=False,
        )
        stream.flush()
        os.fsync(stream.fileno())
    command = [
        sys.executable,
        "-m",
        "predictor_ops",
        "run",
        "--job",
        job_id,
        "--config",
        str(config_path),
    ]
    environment = os.environ.copy()
    environment["BRASILEIRAO_CAPTURE_TURN"] = json.loads(metadata)["execution_turn"]
    return subprocess.run(command, env=environment, check=False, creationflags=_NO_WINDOW).returncode


if __name__ == "__main__":
    raise SystemExit(main())
