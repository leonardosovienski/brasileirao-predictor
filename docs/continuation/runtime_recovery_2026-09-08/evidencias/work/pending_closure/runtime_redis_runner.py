"""Run explicit tests against the newly provisioned Redis, checked by run_id."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import time

import provision_redis_wsl as provision

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "integration-repo"
LOGS = ROOT / "pending_closure" / "validation"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=int, choices=(13, 14, 15), required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--e2e-python", type=Path)
    parser.add_argument("--e2e-script", type=Path)
    parser.add_argument("name")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.name or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in args.name):
        raise ValueError("name must be a simple receipt stem")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("explicit test command required")
    created = json.loads((provision.BASE / "created.json").read_text(encoding="utf-8"))
    ready = json.loads((provision.BASE / "ready.json").read_text(encoding="utf-8"))
    info = provision.server_info()
    if created["distro"] != provision.DISTRO or ready["run_id"] != info["run_id"] or ready["process_id"] != info["process_id"]:
        raise RuntimeError("endpoint is not the owned Redis process")
    env = dict(provision.ENV)
    redis_url = f"redis://127.0.0.1:{provision.PORT}/{args.db}"
    env.update({
        "PYTHONPATH": str(ROOT / "guard") + os.pathsep + str(REPO),
        "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "NUMBA_CACHE_DIR": str(ROOT / "pending_closure" / "numba_cache"),
        "COVERAGE_FILE": str(LOGS / f"{args.name}.coverage"),
        "REDIS_URL": redis_url, "LINEUP_TEST_REDIS_URL": redis_url,
        "LINEUP_TEST_REDIS_RUN_ID": ready["run_id"],
        "SPORTS_DB_PATH": str(REPO / "data" / "sports.db"),
        "MARKET_DB_PATH": str(REPO / "data" / "market.db"),
        "BRASILEIRAO_DB_PATH": str(REPO / "data" / "matches.db"),
        "BRASILEIRAO_CONFIG_PATH": str(REPO / "config.yaml"),
        "RUNTIME_DIR": str(ROOT / "pending_closure" / "runtime"),
        "PREDICTIONS_LOG_PATH": str(ROOT / "pending_closure" / "predictions.jsonl"),
        "PERIOD_LOG_PATH": str(ROOT / "pending_closure" / "periods.jsonl"),
    })
    if bool(args.e2e_python) != bool(args.e2e_script):
        raise ValueError("provide both explicit E2E Python and script paths")
    if args.e2e_python:
        python_path, script_path = args.e2e_python.resolve(strict=True), args.e2e_script.resolve(strict=True)
        if not python_path.is_file() or script_path.suffix != ".py" or not script_path.is_file() or not script_path.is_relative_to(ROOT):
            raise ValueError("E2E requires an existing interpreter and a .py script inside the isolated work directory")
        env["LINEUP_E2E_PYTHON"], env["LINEUP_E2E_KERNEL_SCRIPT"] = str(python_path), str(script_path)
        env["LINEUP_E2E_REDIS_URL"], env["LINEUP_E2E_REDIS_RUN_ID"] = redis_url, ready["run_id"]
    receipt = {"name": args.name, "started_at_utc": datetime.now(UTC).isoformat(), "command": command,
               "cwd": str(REPO), "redis_url": redis_url, "redis_run_id": ready["run_id"],
               "live_data_used": False, "environment_allowlist": True,
               "python_external_network_blocked": True, "redis_ownership_verified_before": True}
    if args.e2e_python:
        receipt["e2e_python"], receipt["e2e_script"] = env["LINEUP_E2E_PYTHON"], env["LINEUP_E2E_KERNEL_SCRIPT"]
        receipt["e2e_script_sha256"] = provision.hashlib.sha256(script_path.read_bytes()).hexdigest()
    LOGS.mkdir(exist_ok=True)
    log_path, receipt_path = LOGS / f"{args.name}.log", LOGS / f"{args.name}.json"
    if log_path.exists() or receipt_path.exists():
        raise FileExistsError("receipt name already exists")
    started = time.monotonic()
    with log_path.open("x", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            receipt["exit_code"] = process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                           stdout=log, stderr=log, timeout=15, check=False,
                           env=env, creationflags=subprocess.CREATE_NO_WINDOW)
            receipt.update({"exit_code": 124, "timeout": True})
    receipt["seconds"] = time.monotonic() - started
    try:
        receipt["redis_ownership_verified_after"] = provision.server_info()["run_id"] == ready["run_id"]
        receipt["redis_dbsize_after"] = provision.redis_commands(("SELECT", args.db), ("DBSIZE",))[1]
    except Exception as exc:
        receipt["redis_ownership_verified_after"] = False
        receipt["redis_postcheck_error"] = type(exc).__name__
    with receipt_path.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
        handle.write("\n")
    print(json.dumps(receipt))
    print("\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]))
    raise SystemExit(receipt["exit_code"] if receipt["redis_ownership_verified_after"] else 125)


if __name__ == "__main__":
    main()
