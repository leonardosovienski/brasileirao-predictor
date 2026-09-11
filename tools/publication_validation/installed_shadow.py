"""Installed Ops/shadow envelope against fresh synthetic resources only."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def main():
    import brasileirao_predictor

    assert Path(brasileirao_predictor.__file__).is_relative_to(Path(sys.prefix))
    root = Path(sys.argv[1]).resolve()
    root.mkdir(exist_ok=False)
    application = root / "application"
    (application / "data").mkdir(parents=True)
    (application / "config.yaml").write_text("database: data/matches.db\n", encoding="utf-8")
    (application / "data/teams_brasileirao.json").write_text("{}", encoding="utf-8")
    with sqlite3.connect(application / "data/matches.db") as conn:
        conn.execute("CREATE TABLE synthetic_fixture(id INTEGER)")
    environment = os.environ.copy()
    environment.update(BRASILEIRAO_PROJECT_ROOT=str(application), BRASILEIRAO_RUNTIME_ROOT=str(root / "runtime"))
    for key in ("BRASILEIRAO_DATABASE_PATH", "BRASILEIRAO_CONFIG_PATH", "BRASILEIRAO_TEAMS_PATH"):
        environment.pop(key, None)
    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "brasileirao_scripts.sombra_diaria",
            "--task-name",
            "brasileirao-sombra-manha",
            "--check",
        ],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    (root / "stdout.txt").write_text(process.stdout, encoding="utf-8")
    (root / "stderr.txt").write_text(process.stderr, encoding="utf-8")
    assert process.returncode == 0, process.stderr
    configs = list((root / "runtime/operations").glob("job-*.json"))
    config = json.loads(configs[0].read_text(encoding="utf-8"))
    assert config["schema_version"] == "3"
    assert config["jobs"][0]["provenance"]["input_hashes"]["matches_database"]
    # The genuine runner must persist completion and the supplied provenance.
    receipts = [p.read_text(encoding="utf-8") for p in (root / "runtime").rglob("*.jsonl")]
    assert any("brasileirao-sombra-manha-check" in text and "matches_database" in text for text in receipts)
    print(json.dumps({"status": "PASS", "installed_shadow_ops": True, "scientific_steps_executed": False}))


if __name__ == "__main__":
    main()
