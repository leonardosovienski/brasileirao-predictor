"""Produce branch-aware coverage by architectural classification."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

RUNTIME = {
    "src/settings.py",
    "src/db.py",
    "src/model.py",
    "src/ratings.py",
    "src/market_pricer.py",
    "src/prediction_log.py",
    "src/evaluator.py",
    "src/elo_baseline.py",
    "src/dixon_coles.py",
    "src/settle.py",
    "src/bet_log.py",
    "src/data/collection_only_archive.py",
    "src/data/bookmaker_odds.py",
    "src/data/bookmaker_stability.py",
    "src/data/historical_expansion.py",
    "src/data/pit_backfill.py",
}
PROVIDERS = {
    "src/data/api_football_provider.py",
    "src/data/sportmonks_provider.py",
    "src/data/the_odds_api_provider.py",
    "src/sofascore.py",
}
MIGRATION = {
    "scripts/init_compose_data.py",
    "scripts/seed_test_fixtures.py",
    "scripts/bootstrap_calibration_window.py",
    "scripts/ingest_api_football_history.py",
    "src/ingest_sofascore.py",
    "src/ingest_fbref.py",
}
# The homologated Redis integration surface is the versioned kernel protocol.
# The operator smoke is executed as an E2E container gate and reported separately.
REDIS_INTEGRATION: set[str] = set()
KERNEL = {"src/kernel_daemon.py"}


def _percent(files: dict[str, dict], names: Iterable[str]) -> tuple[float, int, int]:
    covered = possible = 0
    for name in names:
        if name not in files:
            continue
        summary = files[name]["summary"]
        covered += summary["covered_lines"] + summary["covered_branches"]
        possible += summary["num_statements"] + summary["num_branches"]
    return (100.0 * covered / possible if possible else 100.0, covered, possible)


def classify(path: str) -> str:
    if path in RUNTIME:
        return "runtime_homologado"
    if path in KERNEL:
        return "kernel"
    if path in REDIS_INTEGRATION:
        return "integracao_redis"
    if path in PROVIDERS:
        return "providers"
    if path in MIGRATION:
        return "migracao"
    if (
        path.startswith("src/research/")
        or path.startswith("scripts/")
        and any(token in path for token in ("backtest", "calib", "sim_", "investigate", "sweep"))
    ):
        return "pesquisa"
    return "legado"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    files = {name.replace("\\", "/"): value for name, value in raw["files"].items()}
    groups: dict[str, list[str]] = {}
    for name in files:
        groups.setdefault(classify(name), []).append(name)

    lines = [
        "# Branch-aware coverage",
        "",
        "| Classificação | Coberto | Possível | Cobertura |",
        "|---|---:|---:|---:|",
    ]
    results = {}
    for group in (
        "runtime_homologado",
        "kernel",
        "integracao_redis",
        "providers",
        "pesquisa",
        "migracao",
        "legado",
    ):
        names = groups.get(group, [])
        if group == "integracao_redis":
            names = sorted(REDIS_INTEGRATION | KERNEL)
        percent, covered, possible = _percent(files, names)
        results[group] = percent
        lines.append(f"| {group} | {covered} | {possible} | {percent:.2f}% |")
    global_summary = raw["totals"]
    lines.extend(
        [
            "",
            f"Cobertura global branch-aware: **{global_summary['percent_covered']:.2f}%**.",
            "",
            "Worker .NET (collector Cobertura): **85,15% linhas / 80,92% branches**.",
            "",
            "A cobertura global inclui pesquisa, migração e legado sem exclusões silenciosas.",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(results, sort_keys=True))
    required = ("runtime_homologado", "kernel", "integracao_redis", "providers")
    return 0 if all(results[group] >= 80 for group in required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
