import importlib.metadata
import sys
from pathlib import Path

import predictor_core
import predictor_ops
import predictor_ops.runner
from predictor_ops.models import JobConfig, RuntimeConfig

ROOT = Path(__file__).resolve().parents[1]


def test_shared_dependencies_load_from_site_packages() -> None:
    assert importlib.metadata.version("predictor-core") == "2.1.0"
    assert importlib.metadata.version("predictor-ops") == "2.0.1"
    assert "site-packages" in str(predictor_core.__file__)
    assert "site-packages" in str(predictor_ops.__file__)


def test_shared_wheel_hashes_are_pinned() -> None:
    records = (ROOT / "constraints" / "shared-wheels.sha256").read_text(encoding="utf-8")
    assert "83de1d4415700dedaf387bc46dd9685e046de1fa47f37367bf2167462b09761b" in records
    assert "77ca2eb3f1090226dfef23b84d7fb2f9a61bd858c970d433d28303e637a8903e" in records


def test_predictor_ops_closes_owned_stdout_pipe(tmp_path: Path, monkeypatch) -> None:
    spawned = []
    real_popen = predictor_ops.runner.subprocess.Popen

    def recording_popen(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        spawned.append(process)
        return process

    monkeypatch.setattr(predictor_ops.runner.subprocess, "Popen", recording_popen)
    job = JobConfig(
        id="pipe-cleanup",
        command=[sys.executable, "-c", "print('done')"],
        runtime=RuntimeConfig(root=tmp_path),
        heartbeat_interval_seconds=0.01,
    )
    result = predictor_ops.runner.run_job(job)

    assert result.exit_code == 0
    assert len(spawned) == 1
    assert spawned[0].stdout is not None and spawned[0].stdout.closed
