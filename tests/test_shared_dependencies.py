import importlib.metadata
import sys
from pathlib import Path

import predictor_core
import predictor_ops
import predictor_ops.runner
from predictor_ops.models import JobConfig, RuntimeConfig

ROOT = Path(__file__).resolve().parents[1]


def test_shared_dependencies_load_from_site_packages() -> None:
    assert importlib.metadata.version("predictor-core") == "2.2.0"
    assert importlib.metadata.version("predictor-ops") == "3.0.0"
    assert "site-packages" in str(predictor_core.__file__)
    assert "site-packages" in str(predictor_ops.__file__)


def test_shared_wheel_hashes_are_pinned() -> None:
    records = (ROOT / "constraints" / "shared-wheels.sha256").read_text(encoding="utf-8")
    assert "2e1809ddd20637dd4f685c654d6c3fea4604cb44249bedc6afe7175db0a0aa95" in records
    assert "22b811595e90866a52ddf5a403ddb827e59cfeda948951e78193daabeb984825" in records


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
