"""Produce branch-aware coverage by architectural classification."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

RUNTIME = {
    "brasileirao_predictor/settings.py",
    "brasileirao_predictor/db.py",
    "brasileirao_predictor/model.py",
    "brasileirao_predictor/ratings.py",
    "brasileirao_predictor/market_pricer.py",
    "brasileirao_predictor/prediction_log.py",
    "brasileirao_predictor/evaluator.py",
    "brasileirao_predictor/elo_baseline.py",
    "brasileirao_predictor/dixon_coles.py",
    "brasileirao_predictor/settle.py",
    "brasileirao_predictor/bet_log.py",
    "brasileirao_predictor/data/collection_only_archive.py",
    "brasileirao_predictor/data/bookmaker_odds.py",
    "brasileirao_predictor/data/bookmaker_stability.py",
    "brasileirao_predictor/data/historical_expansion.py",
    "brasileirao_predictor/data/pit_backfill.py",
}
PROVIDERS = {
    "brasileirao_predictor/data/api_football_provider.py",
    "brasileirao_predictor/data/sportmonks_provider.py",
    "brasileirao_predictor/data/the_odds_api_provider.py",
    "brasileirao_predictor/sofascore.py",
}
MIGRATION = {
    "brasileirao_scripts/init_compose_data.py",
    "brasileirao_scripts/seed_test_fixtures.py",
    "brasileirao_scripts/bootstrap_calibration_window.py",
    "brasileirao_scripts/ingest_api_football_history.py",
    "brasileirao_predictor/ingest_sofascore.py",
    "brasileirao_predictor/ingest_fbref.py",
}
# The homologated Redis integration surface is the versioned kernel protocol.
# The operator smoke is executed as an E2E container gate and reported separately.
REDIS_INTEGRATION: set[str] = set()
KERNEL = {"brasileirao_predictor/kernel_daemon.py"}
# Código que produz EVIDÊNCIA publicada: os artefatos de reports/ que sustentam
# vereditos fechados no registro de tentativas, e a régua que os desconta.
# Auditoria adversarial 2026-09-05, achado 6 (issue #57): estes arquivos caíam
# em "pesquisa"/"legado", categorias sem gate, enquanto os contratos ficavam
# acima de 80%. O caminho que vai do dado bruto até a afirmação publicada era o
# menos exercitado do repositório — 22% em quem calcula o DSR, 54% em quem
# produziu a única trial `comprovada`.
EVIDENCIA = {
    "brasileirao_scripts/research_xg_ensemble.py",
    "brasileirao_scripts/backtest_walkforward.py",
    "brasileirao_scripts/trial_draw_calibration_a10.py",
    "brasileirao_scripts/research_market_edge_ordering.py",
    "brasileirao_scripts/benchmark_predictor.py",
    "brasileirao_predictor/research/market_edge_ordering.py",
    "brasileirao_predictor/research/prospective_validation/metrics.py",
}
# Piso-catraca, não meta. Medido em 2026-09-05: 56,40%. O alvo é 80%, o mesmo
# das categorias homologadas; subir o piso exige escrever teste, e ele nunca
# desce. Colocar 80 aqui hoje quebraria o CI sem corrigir nada.
EVIDENCIA_PISO = 56.0


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
    if path in EVIDENCIA:
        return "geradores_de_evidencia"
    if path in MIGRATION:
        return "migracao"
    if (
        path.startswith("brasileirao_predictor/research/")
        or path.startswith("brasileirao_scripts/")
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
        "geradores_de_evidencia",
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
            "",
            f"`geradores_de_evidencia` é o código que produz os artefatos de `reports/` "
            f"que sustentam vereditos fechados. Piso-catraca em {EVIDENCIA_PISO:.0f}% "
            "(medido em 2026-09-05); alvo 80%, o mesmo das categorias homologadas.",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(results, sort_keys=True))
    required = ("runtime_homologado", "kernel", "integracao_redis", "providers")
    falhas = [f"{g} {results[g]:.2f}% < 80%" for g in required if results[g] < 80]
    evidencia = results["geradores_de_evidencia"]
    if evidencia < EVIDENCIA_PISO:
        falhas.append(
            f"geradores_de_evidencia {evidencia:.2f}% < piso {EVIDENCIA_PISO:.2f}% — "
            "o código que produz evidência publicada não pode regredir"
        )
    for falha in falhas:
        print(f"GATE: {falha}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
