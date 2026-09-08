"""Freeze a separate exploratory extension using metadata only."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK / "price_extension_51"
OLD = WORK / "selection_reanalysis"
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
ROOT.mkdir(exist_ok=True)
assert not (ROOT / "plan.json").exists()
def read(path):
    return json.loads(path.read_text(encoding="utf-8"))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def dt(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    return parsed.astimezone(timezone.utc)
def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

universe_path = OLD / "price_history/fixture_universe_jan_jun_2026.json"
excluded_path = OLD / "price_history/fixture_selection_30.json"
old_results_path = OLD / "pinnacle_only_results.json"
universe = read(universe_path)
excluded = {row["fixture_id"] for row in read(excluded_path)}
old_results = read(old_results_path)
by_id = {row["fixture_id"]: row for row in universe}
latest_target = max(dt(by_id[key]["kickoff_at"]) - timedelta(minutes=10) for key in old_results["training_ids"])
selection = sorted([row for row in universe if row["fixture_id"] not in excluded
                    and dt(row["kickoff_at"]) - timedelta(hours=1) > latest_target],
                   key=lambda row: (row["kickoff_at"], row["fixture_id"]))
assert len(selection) == len({r["fixture_id"] for r in selection}) == 51
assert old_results["ridge_beta"] == -0.31988646513691255
save("selection.json", selection)
plan = {
    "id": "DISCOVERY-B-PIN-EXT51-20260907",
    "frozen_at": datetime.now(timezone.utc).isoformat(),
    "registration_semantics": "NEW_EXPLORATORY_EXTENSION_AFTER_PREVIOUS_RESULTS_NOT_BLIND_OR_FUTURE_REPLICATION",
    "previous_stopping_preserved": "The prior 30-ID study is complete and unchanged. This separate bounded extension follows the user's request to continue without waiting for future games.",
    "selected_n": 51,
    "selection_file_sha256": sha(ROOT / "selection.json"),
    "source_universe_sha256": sha(universe_path),
    "excluded_previous_selection_file_sha256": sha(excluded_path),
    "source_pinnacle_results_sha256": sha(old_results_path),
    "source_replay_sha256": sha(OLD / "price_discovery_replay.py"),
    "source_replay_path": str(OLD / "price_discovery_replay.py"),
    "source_pinnacle_results_path": str(old_results_path),
    "excluded_previous_selection_path": str(excluded_path),
    "source_universe_path": str(universe_path),
    "selection_rule": "All unused IDs in the metadata universe whose T-1h decision is strictly after latest training T-10min target; exclude all30 prior selected IDs including failed requests. No replacement.",
    "training_latest_target_at": latest_target.isoformat(),
    "beta": old_results["ridge_beta"],
    "new_fits": 0,
    "models": ["persistence", "frozen_ridge_momentum"],
    "forecast": "normalized(q_T1 + beta*(q_T1-q_T6)); clamp coordinates at1e-6 then normalize; same existing implementation",
    "bookmaker": "pinnacle",
    "market": "1X2",
    "side_order": ["home", "draw", "away"],
    "feature_cutoffs": ["T6H", "T1H"],
    "target_cutoff": "T10M",
    "decimal_odds_range": [1.01, 20.0],
    "complete_vector_overround_range": [0.99, 1.30],
    "oldest_leg_max_age_hours": 6,
    "last_state_rule": "last timestamp <=cutoff first, explicit active true second; reject conflicts, stale or incomplete vectors; no interpolation",
    "primary_metric": "Mean over events of mean squared error across three coordinates; paired same valid panel",
    "minimum_complete_test_events": 30,
    "diagnostics": ["monthly paired errors", "leave_one_event_delta_range", "number of events better", "missing reasons over all51"],
    "inference": "Descriptive only. No formal confidence or profit verdict; entire historical search/adaptation retained.",
    "secondary_price_proxy": {
        "selection": "At most one per feature-valid event: max(predicted_q_T10*quoted_odds_T1-1)>0.02; ties home, draw, away. Never use target for selection.",
        "threshold": 0.02,
        "observed": "q_observed_T10[selected]*quoted_odds_T1[selected]-1",
        "cost_scenario": 0.02,
        "net_proxy": "observed minus cost_scenario; not realised profit, trueEV, settlement or executed CLV",
        "missing_target": "retain as unassessed signal; never suppress from signal denominator",
    },
    "requests": {"historical_free_max": 51, "new_billable_requests": 0, "bookmakers": ["pinnacle"], "reserve": 20,
                 "cooldown_after_response_seconds": 7, "cooldown_after_429_seconds": 30, "automatic_retries": False,
                 "stop_on_auth_or_payment_error": True, "stop_after_consecutive_429": 3},
    "stopping": "One acquisition of at most51 distinct histories and one evaluation. Keep failures, no retries/replacements/refits/threshold changes/new books. Stop and report regardless of sign. No prospective study or capital promotion.",
    "protected_scope": "Only Jan-Jun2026 previously exploratory metadata, before protected cohorts; no A1 data or football results accessed",
    "raw_data_policy": "Private local work/raw only, no provider raw redistribution",
    "prior_result": "13 training/9 test,3.35%MSE reduction fragile to removing one event; new51 interleaved in same test period, not independent future replication",
    "official_sources": ["https://oddspapi.io/us/docs/get-historical-odds", "https://oddspapi.io/us/docs/requests-and-quota"],
}
save("plan.json", plan)
decision = f"""# DECISION_RECORD — extensão histórica de preço com regra congelada

- ACTION: coletar no máximo 51 históricos Pinnacle e avaliar o coeficiente já congelado, sem novos ajustes.
- WHY_NOW: o usuário perguntou se era necessário esperar o próximo fim de semana; há jogos históricos adicionais admissíveis, dentro da autorização vigente para executar a pesquisa.
- ALTERNATIVES_CONSIDERED: esperar partidas futuras; alterar regras; repetir as falhas anteriores. Esta extensão usa todos os 51 IDs admissíveis pelos metadados, sem reposição.
- EVIDENCE_TO_BE_REVEALED: preços anteriores ao jogo, previsão de preço T−10min a partir de T−1h/T−6h, erro contra persistência e prêmio implícito secundário. Nenhum placar ou lucro.
- HYPOTHESIS_FAMILY: DISCOVERY-B-PIN-EXT51-20260907, extensão exploratória da mesma família B.
- MARKET_TYPE: 1X2 pré-jogo, Pinnacle.
- SEARCH_HISTORY: resultado anterior já conhecido (3,35% em nove testes, frágil); 51 jogos distintos intercalados no mesmo período. Não é réplica futura nem confirmação cega. O estudo anterior permanece encerrado.
- CONFIG_HASH: SHA-256 plan.json `{sha(ROOT / 'plan.json')}`.
- DATASET_HASH: SHA-256 selection.json `{sha(ROOT / 'selection.json')}`; históricos terão hashes por resposta.
- PREREQUISITE_GATES: decisão T−1h estritamente após último alvo de treino ({latest_target.isoformat()}); excluir 30 IDs anteriores; Jan–Jun admissível; parsers testados; fonte original por hash; quota com reserva20; nenhum gasto.
- EXPECTED_INFORMATION_GAIN: falsificar ou fortalecer descritivamente o sinal de reversão congelado e verificar se ele chega a selecionar preços acima do prêmio implícito de2%, preservando a diferença entre proxy e lucro real.
- STOPPING_RULE: uma coleta, uma avaliação; máximo51 pedidos únicos sem repetição/substituição, pausas7s após resposta e30s após429, parar após3consecutivos. Sem mudar parâmetros depois dos resultados. Publicar todos os estados, inclusive insuficiência. Não registrar trial nem habilitar capital.
"""
(ROOT / "DECISION_RECORD.md").write_text(decision, encoding="utf-8")
destination = REPO / "docs/decisions/2026-09-07-price-extension-51.md"
assert not destination.exists()
destination.write_text(decision, encoding="utf-8")
print(json.dumps({"selected_n": 51, "plan_sha256": sha(ROOT / "plan.json"), "selection_sha256": sha(ROOT / "selection.json"), "training_latest_target_at": latest_target.isoformat()}))
