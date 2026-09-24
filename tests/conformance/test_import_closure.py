"""The transitive import closure of every entrypoint stays inside the domain (C24.1).

Checked on the INSTALLED package (checkout in CI, published wheel in the cleanroom): no path
from [project.scripts] or the plugin entry point reaches the envelope protocol, CAIN, the
ecosystem envelope or the reserved adapter_paths (rule 1); nothing outside adapter_paths
imports them (rule 2). Rule 3 (the adapter calls the domain only through adapter_api) is the
Stage B obligation; the adapter package is an empty reservation in Stage A.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections import deque
from importlib.metadata import distribution
from pathlib import Path

import brasileirao_predictor

FORBIDDEN_TOP = {"research_protocol", "cain", "ecosystem", "research_snapshot", "research_bundle", "cain_research"}
ADAPTERS = "brasileirao_predictor.adapters"
PACKAGES = ("brasileirao_predictor", "brasileirao_scripts")
SITE = Path(brasileirao_predictor.__file__).resolve().parent.parent


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(SITE).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _graph() -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}
    for package in PACKAGES:
        for path in (SITE / package).rglob("*.py"):
            name = _module_name(path)
            base = name.split(".") if path.name == "__init__.py" else name.split(".")[:-1]
            targets: set[str] = set()
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
                if isinstance(node, ast.Import):
                    targets.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        root = base[: len(base) - (node.level - 1)] if node.level > 1 else base
                        module = ".".join(root + ([node.module] if node.module else []))
                    else:
                        module = node.module or ""
                    targets.add(module)
                    targets.update(f"{module}.{alias.name}" for alias in node.names)
                elif (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and node.value.startswith(tuple(f"{p}." for p in PACKAGES))
                    and " " not in node.value
                ):
                    targets.add(node.value)  # modules launched with `python -m <module>`
            edges[name] = targets
    return edges


def _resolve(target: str, modules: set[str]) -> str | None:
    while target:
        if target in modules:
            return target
        target = target.rpartition(".")[0]
    return None


def _roots() -> dict[str, str]:
    dist = distribution("brasileirao-predictor")
    return {
        f"{ep.group}:{ep.name}": ep.value.split(":")[0]
        for ep in dist.entry_points
        if ep.group in {"console_scripts", "predictor.plugins"}
    }


def _closure(root: str, edges: dict[str, set[str]]) -> tuple[dict[str, str | None], set[str]]:
    modules = set(edges)
    seen: dict[str, str | None] = {root: None}
    external: set[str] = set()
    queue = deque([root])
    while queue:
        current = queue.popleft()
        parts = current.split(".")
        for target in [".".join(parts[:i]) for i in range(1, len(parts))] + sorted(edges.get(current, ())):
            if target.startswith(PACKAGES):
                local = _resolve(target, modules)
                if local and local not in seen:
                    seen[local] = current
                    queue.append(local)
            elif target:
                external.add(target.split(".")[0])
    return seen, external


def test_entrypoints_include_the_research_circuit() -> None:
    assert _roots()["console_scripts:brasileirao-research"] == "brasileirao_predictor.research_runtime.runner"


def test_no_entrypoint_reaches_envelope_cain_or_adapter_paths() -> None:
    edges = _graph()
    report = {}
    for label, root in _roots().items():
        seen, external = _closure(root, edges)
        report[label] = {
            "forbidden": sorted(external & FORBIDDEN_TOP),
            "adapters": sorted(m for m in seen if m == ADAPTERS or m.startswith(ADAPTERS + ".")),
        }
    assert all(not v["forbidden"] and not v["adapters"] for v in report.values()), json.dumps(report, indent=1)


def test_research_circuit_components_are_reachable_from_the_entrypoint() -> None:
    seen, _ = _closure("brasileirao_predictor.research_runtime.runner", _graph())
    for component in ("admission", "execution", "results", "worker", "recovery", "contract", "faults", "durable"):
        assert f"brasileirao_predictor.research_runtime.{component}" in seen, component
    assert "brasileirao_predictor.pit" in seen
    assert "brasileirao_predictor.model" in seen and "brasileirao_predictor.ratings" in seen


def test_economic_decision_code_is_not_reachable_from_the_research_entrypoint() -> None:
    seen, _ = _closure("brasileirao_predictor.research_runtime.runner", _graph())
    for module in (
        "brasileirao_predictor.research.economic_decision",
        "brasileirao_predictor.research.shadow_portfolio",
        "brasileirao_predictor.bet_log",
    ):
        assert module not in seen, module


def test_nothing_outside_adapter_paths_imports_them() -> None:
    offenders = []
    for module, targets in _graph().items():
        if module == ADAPTERS or module.startswith(ADAPTERS + "."):
            continue
        if any(t == ADAPTERS or t.startswith(ADAPTERS + ".") for t in targets):
            offenders.append(module)
    assert offenders == []


def test_runtime_import_of_the_circuit_loads_no_forbidden_module() -> None:
    code = (
        "import sys, json\n"
        "import brasileirao_predictor.research_runtime.runner, brasileirao_predictor.research_runtime.worker\n"
        "import brasileirao_predictor.research_runtime.recovery\n"
        f"bad = sorted(m for m in sys.modules if m.split('.')[0] in {sorted(FORBIDDEN_TOP)!r}"
        f" or m.startswith({ADAPTERS!r}))\n"
        "print(json.dumps(bad))\n"
    )
    output = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert json.loads(output.strip().splitlines()[-1]) == []
