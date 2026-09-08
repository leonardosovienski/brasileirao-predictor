"""Run explicit checks in the disposable checkout, with receipts and no live data."""
import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "integration-repo"
LOGS = ROOT / "validation"
LOGS.mkdir(exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument("name")
parser.add_argument("--timeout", type=int, default=300)
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
allowed = {
    "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "TEMP", "TMP",
    "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES",
    "PROGRAMFILES(X86)", "PROGRAMW6432", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS",
    "OS", "HOMEDRIVE", "HOMEPATH", "DOTNET_ROOT",
}
env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
env.update({
    "PYTHONPATH": str(ROOT / "guard") + os.pathsep + str(REPO),
    "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "NUMBA_CACHE_DIR": str(ROOT / "numba_cache"),
    "COVERAGE_FILE": str(ROOT / "validation" / ".coverage"),
    "REDIS_URL": "redis://127.0.0.1:16389/15",
    "SPORTS_DB_PATH": str(REPO / "data" / "sports.db"),
    "MARKET_DB_PATH": str(REPO / "data" / "market.db"),
    "BRASILEIRAO_DB_PATH": str(REPO / "data" / "matches.db"),
    "BRASILEIRAO_CONFIG_PATH": str(REPO / "config.yaml"),
    "RUNTIME_DIR": str(ROOT / "runtime"),
    "PREDICTIONS_LOG_PATH": str(ROOT / "predictions.jsonl"),
    "PERIOD_LOG_PATH": str(ROOT / "periods.jsonl"),
    "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1",
})
command = args.command[1:] if args.command[:1] == ["--"] else args.command
receipt = {
    "name": args.name, "started_at_utc": datetime.now(UTC).isoformat(),
    "command": command, "cwd": str(REPO), "live_data_used": False,
    "environment_allowlist": True, "python_external_network_blocked": True,
}
start = time.monotonic()
with (LOGS / f"{args.name}.log").open("w", encoding="utf-8") as log:
    process = subprocess.Popen(command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        receipt["exit_code"] = process.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                       stdout=log, stderr=log, timeout=15, check=False)
        receipt["exit_code"] = 124
        receipt["timeout"] = True
receipt["seconds"] = time.monotonic() - start
(LOGS / f"{args.name}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt))
print("\n".join((LOGS / f"{args.name}.log").read_text(encoding="utf-8", errors="replace").splitlines()[-20:]))
raise SystemExit(receipt["exit_code"])
