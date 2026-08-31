import importlib.metadata
import sys
from pathlib import Path

import predictor_core
import predictor_ops
import predictor_ops.runner
from predictor_ops.models import JobConfig, RuntimeConfig

ROOT = Path(__file__).resolve().parents[1]


def test_shared_dependencies_load_from_site_packages() -> None:
    assert importlib.metadata.version("predictor-core") == "3.0.0"
    assert importlib.metadata.version("predictor-ops") == "4.0.0"
    assert "site-packages" in str(predictor_core.__file__)
    assert "site-packages" in str(predictor_ops.__file__)


def test_shared_wheel_hashes_are_pinned() -> None:
    records = (ROOT / "constraints" / "shared-wheels.sha256").read_text(encoding="utf-8")
    assert "fdc1d3e27b6805a1d125702b6e3bb88f6fa3483791c22ea310bf6c56d5581c4d" in records
    assert "a79b895492181c88c428ee8984a38d5f3da0d0105f060f89a061376d5cfe2b2b" in records


def test_python_images_verify_shared_wheels_before_install() -> None:
    for name in ("Dockerfile.cli", "Dockerfile.kernel"):
        dockerfile = (ROOT / name).read_text(encoding="utf-8")
        assert "COPY constraints/shared-wheels.sha256" in dockerfile
        verify_at = dockerfile.index("sha256sum -c constraints/shared-wheels.sha256")
        install_at = dockerfile.index("uv pip install")
        assert verify_at < install_at


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
