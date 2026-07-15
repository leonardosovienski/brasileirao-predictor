"""Observable Task Scheduler entrypoint for the Brasileirao shadow routine."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT.parent
RUNNER = WORKSPACE / "tools" / "operational_runner.py"
PAYLOAD = Path(__file__).with_name("sombra_diaria_payload.py")
LOG_DIR = ROOT / "logs" / "operations"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the shadow routine with the operational envelope.")
    parser.add_argument("--task-name", required=True, choices=("brasileirao-sombra-manha", "brasileirao-sombra-noite"))
    args = parser.parse_args(argv)
    if not RUNNER.is_file() or not PAYLOAD.is_file():
        print("operational entrypoint is incomplete", file=sys.stderr)
        return 3
    command = [
        sys.executable, str(RUNNER), "run", "--task", args.task_name,
        "--project", "brasileirao-predictor", "--cwd", str(ROOT),
        "--log", str(LOG_DIR / f"{args.task_name}.log"),
        "--event-log", str(LOG_DIR / "events.jsonl"),
        "--heartbeat", str(LOG_DIR / f"{args.task_name}.heartbeat.json"),
        "--expected-artifact", str(ROOT / "data" / "sombra_diaria.log"),
        "--timeout", "7200", "--", sys.executable, "-X", "utf8", str(PAYLOAD),
    ]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
