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
# Redis protocol coverage is a code classification, not proof of an E2E run.
# The operator smoke is executed as an E2E container gate and reported separately.
REDIS_INTEGRATION: set[str] = set()
KERNEL = {
    "brasileirao_predictor/kernel_cli.py",
    "brasileirao_predictor/kernel_daemon.py",
    "brasileirao_predictor/kernel_message.py",
    "brasileirao_predictor/kernel_redis_v2.py",
}
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


def _percent(files: dict[str, dict], names: Iterable[str]) -> tuple[float | None, int, int]:
    covered = possible = 0
    for name in names:
        summary = files[name]["summary"]
        counts = [summary[k] for k in ("covered_lines", "num_statements", "covered_branches", "num_branches")]
        if any(type(value) is not int or value < 0 for value in counts):
            raise ValueError(f"invalid_coverage_counts:{name}")
        if counts[0] > counts[1] or counts[2] > counts[3]:
            raise ValueError(f"covered_exceeds_possible:{name}")
        covered += summary["covered_lines"] + summary["covered_branches"]
        possible += summary["num_statements"] + summary["num_branches"]
    return (100.0 * covered / possible if possible else None, covered, possible)


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
    falhas = []
    if raw.get("meta", {}).get("branch_coverage") is not True:
        falhas.append("branch_coverage must be true")
    required_files = RUNTIME | KERNEL | REDIS_INTEGRATION | PROVIDERS | EVIDENCIA
    for missing in sorted(required_files - files.keys()):
        falhas.append(f"arquivo obrigatorio ausente: {missing}")
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
            names = sorted((REDIS_INTEGRATION | KERNEL) & files.keys())
        percent, covered, possible = _percent(files, names)
        results[group] = percent
        display = "N/A" if percent is None else f"{percent:.2f}%"
        lines.append(f"| {group} | {covered} | {possible} | {display} |")
    global_percent, _, _ = _percent(files, files)
    global_display = "N/A" if global_percent is None else f"{global_percent:.2f}%"
    lines.extend(
        [
            "",
            f"Cobertura global branch-aware nos arquivos fornecidos: **{global_display}**.",
            "",
            "Worker .NET: consulte o artefato Cobertura e o gate separado do job .NET; "
            "este JSON Python não fornece sua cobertura.",
            "",
            "Arquivos obrigatórios ausentes reprovam o gate. N/A indica ausência de denominador, "
            "não 100%. A enumeração do restante depende de coverage.source e do comando executado.",
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
    for group in required:
        percent = results[group]
        if percent is None:
            falhas.append(f"{group}: sem linhas/branches medidos")
        elif percent < 80:
            falhas.append(f"{group} {percent:.2f}% < 80%")
    evidencia = results["geradores_de_evidencia"]
    if evidencia is None:
        falhas.append("geradores_de_evidencia: sem linhas/branches medidos")
    elif evidencia < EVIDENCIA_PISO:
        falhas.append(
            f"geradores_de_evidencia {evidencia:.2f}% < piso {EVIDENCIA_PISO:.2f}% — "
            "o código que produz evidência publicada não pode regredir"
        )
    for falha in falhas:
        print(f"GATE: {falha}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
