"""Reconcile already published historical reports; no model fit or new backtest."""
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

repo = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
out = Path(r"C:\Users\Superleo13\Documents\Codex\2026-09-07\le\outputs")
sources = {}


def read_report(name):
    path = repo / "reports" / name
    raw = path.read_bytes()
    sources[name] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
    return json.loads(raw)


current = read_report("benchmark_serving_v2_corrected_2021_2024_2026-08-26.json")
losses = read_report("losses_serving_v2_2021_2024.json")
year2025 = read_report("benchmark_serving_v2_corrected_2025_diagnostic_2026-08-26.json")
legacy_market = read_report("benchmark_serving_market_no_vig_2026-08-22.json")
assert len(losses) == current["n"] == 1320
assert all("2021-01-01" <= row["date"][:10] <= "2024-12-31" for row in losses)
assert len({row["event_id"] for row in losses}) == len(losses)
recomputed = {key: math.fsum(row[key] for row in losses) / len(losses) for key in ("rps", "brier", "log_loss")}
for key, value in recomputed.items():
    metric = next(item for item in current["metrics"] if item["metric"] in (key, key + "_1x2"))
    assert round(metric["value"], 6) == round(value, 6), key

with sqlite3.connect((repo / "data" / "matches.db").as_uri() + "?mode=ro", uri=True) as conn:
    conn.execute("PRAGMA query_only=ON")
    conn.row_factory = sqlite3.Row
    coverage = [dict(row) for row in conn.execute("""
        SELECT substr(date,1,4) AS year, COUNT(*) AS completed_matches,
               COUNT(DISTINCT event_id) AS unique_event_ids,
               SUM(kickoff_at IS NOT NULL) AS kickoff_present,
               SUM(odds_home IS NOT NULL AND odds_draw IS NOT NULL AND odds_away IS NOT NULL) AS complete_1x2_odds,
               SUM(odds_over IS NOT NULL AND odds_under IS NOT NULL) AS complete_ou_odds,
               SUM(home_xg IS NOT NULL AND away_xg IS NOT NULL) AS xg_pair_present
        FROM sofascore_matches
        WHERE date >= '2021-01-01' AND date < '2026-01-01'
          AND home_score IS NOT NULL AND away_score IS NOT NULL
        GROUP BY substr(date,1,4) ORDER BY year
    """)]


def summary(report):
    return {key: report[key] for key in (
        "n", "period", "engine", "baseline", "half_life_days", "retrain_every",
        "metrics", "baseline_coverage", "generated_at"
    )} | {"accuracy": report["diagnostic"]["accuracy_1x2"]}


data = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "mode": "RECONCILIATION_OF_PREVIOUSLY_PUBLISHED_DIAGNOSTICS",
    "new_backtest_executed": False,
    "protected_cohorts_read": False,
    "coverage_2021_2025": coverage,
    "historical_completed_total": sum(row["completed_matches"] for row in coverage),
    "corrected_v2_2021_2024": summary(current),
    "recomputed_published_loss_means": recomputed,
    "published_means_match_to_6_decimals": True,
    "corrected_v2_2025": summary(year2025),
    "legacy_market_comparison_not_current_v2": summary(legacy_market),
    "sources": sources,
    "limitations": [
        "Historical data have already been examined; these are diagnostics, not blind confirmation.",
        "Legacy market comparison uses an older model configuration; do not merge its numbers with v2.",
        "Sofascore aggregate odds lack named bookmaker and proven executable quote timestamp.",
        "Historical result and xG availability at the simulated decision time is not fully attested.",
        "Benchmark uses max_goals=8 and refit every 100 matches; current production config uses max_goals=12 and scheduled refreshes.",
        "This verification recalculates means of published per-game losses; it does not refit or rerun forecasts.",
    ],
}
out.mkdir(exist_ok=True)
(out / "qualidade_historica_conferida.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def metric(report, name):
    return next(item for item in report["metrics"] if item["metric"] == name)

rps = metric(current, "rps")
oldrps = metric(legacy_market, "rps")
doc = f"""# Qualidade histórica conferida — 07/09/2026

Há {format(data['historical_completed_total'], ',').replace(',', '.')} partidas concluídas de 2021 a 2025 na base local
(380 por ano). A contagem foi feita em SQLite somente leitura, com filtro SQL
até 31/12/2025; nenhuma coorte protegida foi aberta.

## O que os testes existentes mostram

| Teste publicado | Jogos | RPS modelo | RPS referência | Leitura |
|---|---:|---:|---:|---|
| Modelo corrigido v2 × frequência histórica prequential, 2021–2024 | {current['n']} | {rps['value']:.6f} | {rps['baseline_value']:.6f} | Modelo melhor nesse histórico |
| Modelo anterior × agregado de mercado, relatório de 22/08 | {legacy_market['n']} | {oldrps['value']:.6f} | {oldrps['baseline_value']:.6f} | Mercado melhor nesse histórico |

RPS mede erro das probabilidades; menor é melhor. Os dois painéis não têm
exatamente a mesma configuração nem a mesma amostra e não devem ser fundidos.
No painel corrigido, Brier e log loss também favorecem o modelo contra a
frequência histórica. O diagnóstico corrigido de 2025 cobre outros 380 jogos.

Nesta conferência, as médias das perdas por jogo do painel corrigido de 1.320
partidas foram recalculadas e coincidiram com o relatório publicado nas seis
casas decimais disponíveis. Isso verifica a consistência do relatório;
não é um novo treino, backtest ou confirmação independente.

## O que podemos concluir

O histórico já permite avaliar qualidade, reproduzir diagnósticos e localizar
falhas. Não é necessário esperar H14/H15 para esse trabalho. Há sinal preditivo
contra uma referência simples; vantagem rentável sobre o mercado não foi
demonstrada pelas avaliações examinadas.

Dados já utilizados continuam úteis para desenvolvimento e auditoria, mas
não voltam a ser teste cego. Ter placar, xG e odds históricos não prova quando
cada informação estava disponível. As odds agregadas não identificam uma
cotação comprovadamente executável. O benchmark também usa grade de 8 gols e
refit a cada 100 jogos, enquanto a configuração operacional usa grade de 12
gols e atualização agendada; não é reprodução exata de toda a operação atual.

Detalhes, cobertura por ano, métricas completas e hashes dos quatro artefatos
originais: [evidência da conferência](qualidade_historica_conferida.json).
"""
(out / "QUALIDADE_HISTORICA.md").write_text(doc, encoding="utf-8")
print(json.dumps({"completed": data["historical_completed_total"], "published_means_match_to_6_decimals": True, "recomputed": recomputed, "coverage": coverage, "report": str(out / "QUALIDADE_HISTORICA.md")}, ensure_ascii=False))
