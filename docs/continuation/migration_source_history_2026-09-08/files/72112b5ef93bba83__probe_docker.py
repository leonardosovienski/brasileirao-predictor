"""Record bounded, read-only Docker engine probes; an exit code alone is insufficient."""
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess

items = []
for context in ("default", "desktop-linux"):
    command = ["docker", "--context", context, "info", "--format", "{{json .ServerVersion}}"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
        try:
            version = json.loads(result.stdout)
        except ValueError:
            version = None
        available = result.returncode == 0 and isinstance(version, str) and bool(version.strip())
        items.append({"context": context, "command": command, "exit_code": result.returncode,
                      "server_version": version, "available": available, "stderr": result.stderr.strip()})
    except subprocess.TimeoutExpired:
        items.append({"context": context, "command": command, "available": False, "timeout": True})
report = {"checked_at_utc": datetime.now(UTC).isoformat(), "probes": items,
          "service_start_attempt": "Windows denied opening com.docker.service; no elevation attempted",
          "isolated_redis_created": False, "redis_integration_executed": False, "compose_e2e_executed": False}
(Path(__file__).parent / "validation" / "docker_probe.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
