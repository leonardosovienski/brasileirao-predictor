"""Drive the INSTALLED `brasileirao-research` entrypoint in fresh processes (no mocks).

Every call is a real child process of the console script next to sys.executable, so the
admission, the Ops CLI job, the worker and the result store run exactly as in operation.
The state root stays short (Windows MAX_PATH with the predictor_ops layout).
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import fixtures

SCRIPT = Path(sys.executable).with_name(
    "brasileirao-research.exe" if sys.platform == "win32" else "brasileirao-research"
)
PYTHON_ENV_DROP = ("COV_CORE_SOURCE", "COV_CORE_CONFIG", "COV_CORE_DATAFILE", "COVERAGE_PROCESS_START")


def short_root(prefix: str = "brq") -> Path:
    base = os.environ.get("BRASILEIRAO_RESEARCH_TEST_ROOT") or tempfile.gettempdir()
    return Path(tempfile.mkdtemp(prefix=prefix + "-", dir=base))


def cli(*args: str, env: dict | None = None, timeout: float = 600) -> subprocess.CompletedProcess:
    environment = {k: v for k, v in os.environ.items() if k not in PYTHON_ENV_DROP}
    environment.update(env or {})
    return subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=timeout,
        check=False,
    )


def outcomes(completed: subprocess.CompletedProcess) -> list[dict]:
    return [json.loads(line) for line in completed.stdout.splitlines() if line.startswith("{")]


@dataclass
class Lab:
    """One operator installation: object store, policy, state root and dataset versions."""

    root: Path
    registry: list[dict] = field(default_factory=list)
    datasets: dict[str, dict] = field(default_factory=dict)

    @property
    def objects(self) -> Path:
        return self.root / "obj"

    @property
    def state(self) -> Path:
        return self.root / "s"

    @property
    def policy_path(self) -> Path:
        return self.root / "policy.json"

    def put_json(self, kind: str, name: str, value: dict) -> str:
        path = self.root / f"{kind}-{name}.json"
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        done = cli("put-object", "--objects", str(self.objects), str(path))
        assert done.returncode == 0, done.stderr
        object_hash = json.loads(done.stdout)["object_hash"]
        self.registry.append(
            {"kind": kind, "name": name, "version": "1", "revision_id": f"{name}-r1", "content_hash": object_hash}
        )
        return object_hash

    def put_dataset(self, name: str, source: Path, as_of: str = fixtures.AS_OF) -> dict:
        done = cli(
            "put-dataset", "--objects", str(self.objects), "--source", str(source), "--as-of", as_of, "--label", name
        )
        assert done.returncode == 0, done.stderr
        stored = json.loads(done.stdout)
        self.registry.append(
            {
                "kind": "dataset",
                "name": name,
                "version": "1",
                "revision_id": f"{name}-r1",
                "content_hash": stored["manifest_hash"],
            }
        )
        self.datasets[name] = stored
        return stored

    def write_policy(self, **limits) -> None:
        self.policy_path.write_text(
            json.dumps(fixtures.policy(self.registry, **limits), sort_keys=True), encoding="utf-8"
        )

    def request_file(self, request: dict, name: str | None = None) -> Path:
        path = self.root / "req" / f"{name or request['request_id'].split(':')[-1]}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        return path

    def process(self, *paths: Path, state: Path | None = None, env: dict | None = None) -> tuple[int, list[dict], str]:
        done = cli(
            "--state",
            str(state or self.state),
            "process",
            "--policy",
            str(self.policy_path),
            "--objects",
            str(self.objects),
            *[str(p) for p in paths],
            env=env,
        )
        return done.returncode, outcomes(done), done.stderr

    def submit(self, request: dict, **kwargs) -> tuple[int, dict]:
        code, lines, stderr = self.process(self.request_file(request), **kwargs)
        assert lines, f"no outcome line (exit {code}): {stderr[-2000:]}"
        return code, lines[-1]

    def show(self, request_id: str, state: Path | None = None) -> tuple[int, dict]:
        done = cli("--state", str(state or self.state), "show", request_id)
        return done.returncode, json.loads(done.stdout)

    def cleanup(self) -> None:
        def writable(function, path, _exc) -> None:  # operator objects are read-only on purpose
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            function(path)

        shutil.rmtree(self.root, onexc=writable)


def standard_lab(dataset_variants: dict[str, dict] | None = None, **limits) -> Lab:
    """Objects for every reference kind + one synthetic dataset per variant (name -> build options)."""
    lab = Lab(short_root())
    lab.put_json("model", "serving-baseline", fixtures.MODEL_CONFIG)
    lab.put_json("features", "elo-home-advantage", fixtures.FEATURES)
    lab.put_json("baseline", "climatology", fixtures.BASELINE_CLIM)
    lab.put_json("baseline", "market", fixtures.BASELINE_MARKET)
    lab.put_json("cost_model", "close-slippage-tax", fixtures.COST_MODEL)
    lab.put_json("odds", "sofascore-close", fixtures.ODDS)
    for name, options in (dataset_variants or {"synthetic": {}}).items():
        source = fixtures.build_dataset(lab.root / "src" / f"{name}.sqlite3", **options)
        lab.put_dataset(name, source)
    lab.write_policy(**limits)
    return lab


def result_file(outcome: dict) -> dict:
    return outcome["result"] if "result" in outcome else {}


def comparable(result: dict) -> dict:
    """Content that must be invariant across runs of the same question (no run identities)."""
    domain = result["domain_facts"]
    return {
        "result_state": result["result_state"],
        "scientific_state": result["scientific_state"],
        "economic_state": result["economic_state"],
        "predictions": [{k: v for k, v in p.items() if k != "information_fingerprint"} for p in domain["predictions"]],
        "evaluation": domain["evaluation"],
        "economics": domain["economics"],
        "data_quality": domain["data_quality"],
    }


__all__ = ["Lab", "cli", "comparable", "outcomes", "short_root", "standard_lab"]
