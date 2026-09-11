"""Generate an isolated Compose lab using empty volumes and reviewed fixtures."""

import json
import os
import subprocess
import sys
from pathlib import Path


def isolate(spec: dict, repo: Path, output: Path) -> dict:
    """Refuse unexpected host mounts; replace config without opening its source."""
    for service in spec["services"].values():
        for volume in service.get("volumes", []):
            if volume["type"] != "bind":
                continue
            target = volume["target"]
            if target == "/app/config.yaml":
                volume["source"] = str(output / "config.json")
                volume["read_only"] = True
            elif target == "/app/config" and Path(volume["source"]).resolve() == repo / "docker":
                volume["read_only"] = True
            else:
                raise ValueError("unexpected_host_mount")
    worker = spec["services"]["worker"]["environment"]
    for key in ("WebSocketUrl", "ApiKey", "Protocol", "Source", "Bookmaker"):
        worker[f"LINEUP_Exchange__{key}"] = ""
    worker["LINEUP_Worker__AllowSyntheticInputs"] = "true"
    return spec


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    output = Path(sys.argv[1]).resolve()
    if output.is_relative_to(repo) or repo.is_relative_to(output):
        raise ValueError("new_output_outside_checkout_required")
    output.mkdir(exist_ok=False)
    empty = output / "empty.env"
    empty.write_text("", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("EXCHANGE_", "LINEUP_"))}
    env.update(EXCHANGE_WEBSOCKET_URL="", EXCHANGE_API_KEY="", LINEUP_ALLOW_SYNTHETIC_INPUTS="true")
    completed = subprocess.run(
        ["docker", "compose", "--env-file", str(empty), "-f", str(repo / "compose.yaml"), "config", "--format", "json"],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    spec = isolate(json.loads(completed.stdout), repo, output)
    # JSON is YAML-compatible. No local configuration, results or credentials are copied.
    (output / "config.json").write_text(
        json.dumps({"elo": {}, "model": {"calibration_window_years": 3, "goal_half_life_days": 365}}),
        encoding="utf-8",
    )
    (output / "compose.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
