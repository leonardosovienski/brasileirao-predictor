"""Record completed human/model source reads; no imports or operational I/O."""
import hashlib
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
docs = repo / 'docs/continuation/resolution_2026-09-10'
evidence = docs / 'evidence'

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def digest(path):
    content = path.read_bytes()
    return dict(bytes=len(content), sha256=hashlib.sha256(content).hexdigest())

names = '''test_db.py test_db_extended_odds.py test_dixon_coles.py test_dixon_coles_fit.py test_economic_search.py
test_elo_baseline.py test_elo_baseline_block_guard.py test_exp001_cutoff_state_regression.py test_feature_builder.py test_find_odds.py test_historical_admission.py test_historical_expansion.py
test_followup_capture_contract.py test_h10_fadiga_walkforward.py test_hostil_2026_07_18.py
test_hotpath_smoke.py test_integral_review_admission.py test_integral_review_event_backtest.py test_inventario_dados.py test_kernel_protocol.py
test_kickoff_block_guard.py test_lineup_inbox_redis.py test_live_capture_admission.py test_market_0b_resolution.py test_market_edge_ordering.py
test_market_pricer.py test_market_probs_date.py test_math.py test_model.py test_model_xg.py test_operational_readiness.py
test_ou25_market_anchor.py test_ou25_nested_replay.py test_parse_all_odds.py
test_parse_ou_scope_regression.py test_parsers_sofascore.py test_permutation_test.py test_predict_cache_freshness.py
test_pit_backfill.py test_prediction_log.py test_prereg_serving_vs_climatologia.py test_price_hurdle.py
test_price_strength_artifacts.py test_price_strength_dynamic_xg.py test_price_strength_quotes.py test_price_strength_reliability.py
test_price_strength_review_regressions.py test_price_strength_study.py test_promoted_cold_start.py test_ratings.py
test_redis_integration.py test_research_01a_refit_cadence.py test_research_xg_ensemble.py test_run_passive_process_tree.py
test_run_passive_task.py test_season_2026_split.py test_serving_evaluator.py
test_settle.py test_simulator.py test_sofascore_cache.py test_sofascore_probe.py test_sombra_h5.py
test_statistics_parser.py test_sync_competition_filter.py test_the_odds_api_provider.py test_trial_provenance_enforcement.py test_trials_registry_schema.py
test_windows_scheduler_contract.py test_xg_input_quality.py test_xg_model.py'''.split()
paths = ['tests/' + name for name in names]
assert len(paths) == len(set(paths)) == 70
remaining = json.loads((evidence / 'semantic-remaining.json').read_text(encoding='utf-8'))
assert set(paths) == {row['path'] for row in remaining}
notes = json.loads((root / 'semantic-review-notes-06.json').read_text(encoding='utf-8'))
findings = [
    'All 70 listed test sources read fully, without executing tests or opening their referenced operational records. Truncated market_pricer/market_probs_date text was retrieved again. Source inspection is distinct from test execution and commercial validation.',
    'DB tests enforce write-once opening/latest close and propagation, not availability/status history. A date2026/kickoff2022 fixture explicitly tolerates inconsistent calendar metadata. Extended odds permit 1.0 at storage. Preserved shared ingestion remains CPL-P22; no operational migrations.',
    'DC/Elo/serving kickoff guards exclude simultaneous blocks but kickoff ordering is not actual label availability. Several no-future tests only compare prediction/maturity metadata, ranges or differing fits. NB-to-Poisson numerical convergence does not prove an empirical model foundation; goal fallback without a crash does not prove absence of bias. These old comments are not accepted scientific claims.',
    'Economic-search and price-hurdle tests use exact cashflow or independent algebra for fixed scenarios, missing labels/capital reservations and unknown execution. No BE rerun or economic tuning. Old backtest CLV uses closing reference as diagnostic, not an offered executable quote.',
    'EXP001 and live capture tests cover inactive parent/market/selection, cutoff, event identity and sanitized errors. Generic bet365 cannot replace bet365.bet.br. API state admission deliberately does not establish execution, limits or source authentication.',
    'Feature builder tests check side/period but not actual feature availability. Legacy find_odds/market_probs accept date tolerances, swapped teams and even unreadable-date fallback. These do not establish event identity. Shared dependencies stay preserved under CPL-P22.',
    'Historical admission tests reject missing evidence, future/tied state and duplicates. Expansion processed-row counts are not insert counts. Followup capture tests use copied helpers and mocked responses/credentials, validate reserve20 and minimum21/free250 and exclusive attempts; no test proves the scheduled task active.',
    'H10 and research_xg tests still call actual load_config. Prereg-serving and sombra_h5 tests read actual trials/attestation and historical results. Trial-schema/provenance tests open real registries. Hostile Sombra tests can consult default snapshots. These tests were source-reviewed only, not executed here. Do not renew an attestation to make them pass.',
    'Inventory read-only AST checks cover constant SQL only; regex-selected queries do not establish all dynamic SQL safety. WAL hostile n>=1 is weaker than proving all intended committed rows. Kernel fake-client tests prove schema/correlation plumbing; real Lua/native cross-process receipts are separate.',
    'Market pricer hand-calculated 3x3 examples cover integer/half/quarter AH stakes and total push. They do not validate legacy Sombra quarter-line settlement. Market resolution PROCEED is permission for further research, not economic GO. Ordering/permutation tests check strata and fixed formulas, not sufficient temporal dependence or power.',
    'OU nested/anchor tests check kickoff grouping and future-label mutation, but no real availability clocks. Invalid-price pair exclusion lowers paired sample; complete universe accounting belongs to the corrected residual replay. Synthetic margin / probability produces underround, not a realistic bookmaker margin. Freezing candidate from supplied metrics does not attest those metrics.',
    'Parser regressions distinguish OU goals from cards/corners/period, duplicate conflicts and opening/current. Legacy 1x2 permits partial markets and calls current fractionalValue closing without receipt evidence. is_pre_match detects milliseconds; it cannot attest collection availability. Statistics tests strip units without preserving units in numeric values; do not merge incompatible statistics.',
    'Cache tests certify count/config invalidation but not revisions with unchanged count or code/data lineage. sofascore last-page immutability is a false general premise: pagination evolves and results can revise. Existing shared cache/collector is intentionally byte-preserved; envelopes and curated-v2 are successors, not a deployed fix to protected collectors.',
    'PIT v2 tests exercise raw immutability and cutoff/read-only schema. A synthetic fixture carrying scores before kickoff is not real temporal evidence. Prediction-log tests cover append/schema and persistence error, not multi-process transactions or commercial execution. New diagnostic settlement v2 has independent regression evidence and is distinct from legacy grade/record_result.',
    'Price-strength artifact tests enforce exact single-read hashes, exclusive publication, input lineage, duplicate/nonfinite JSON, blocked repo-data paths and failure receipts. A hash proves byte consistency, not source authentication. Dynamic-xg tests check revision ordering, self-target exclusion, availability, calibration boundaries/config identity and cold-start abstention; no real-data fit was run.',
    'Price-strength quote tests exclude offering book, stale/suspended/conflicting/unorderable states, global provider-event aliases and future updates; deterministic candidate ties are algorithmic choices, not commercial advantage. Reliability tests use independent convex-loss oracles and strict typed vectors; in-sample convex optimum is not out-of-sample skill. Study tests explicitly retain profitability/execution=false.',
    'Promoted cold-start tests use strictly earlier seasons and season-cluster bootstrap, while tiny synthetic GO_CANDIDATE outputs do not demonstrate adequate power. Ratings tests cover conservation, decay and date batching. Reliable kickoff alone cannot prove a result was received before a later game.',
    'Redis integration requires explicit non-default local endpoint/run_id, cleans only owned UUIDs and verifies leases/TTL/ready index/ACL error preflight. It synthesizes registration, so .NET registration is validated separately. Inbox integration additionally requires empty DB14. No Redis suite was newly executed during these reads.',
    'Research01a/xg verdict tests canonize crossing-zero as refutada and allow incomplete guardrails in some examples; NaN/missing guardrail defects were already recorded in notes05. Historical conclusion/evaluator bytes stay frozen. Global score permutation preserves marginals but does not prove exchangeability across time. Shared scientific limitations are not silently closed.',
    'Passive launcher tests mock operational jobs; process-tree integration owns its synthetic handles and asserts descendants exited before finished heartbeat. Scheduler tests inspect strings/counts, not installed active tasks. Neither establishes runtime scheduling or a valid DC capture receipt.',
    'Season2026 split tests enforce official-round integers, strict clocks/booleans and one-hour decisions. Paper eligibility from supplied gates is not commercial evidence. Serving tests assert synthetic parity; fallback to priors/goals and stale model cache remain disclosed shared limitations.',
    'Legacy settle tests allow absent date/aliases/swapped names and no prediction. They grade model choices rather than a financial ledger. Simulator tests build malformed synthetic date strings and check graph components; component size four alone does not prove an official complete round-robin group.',
    'TheOddsApiProvider first fixture supplies retrieved_at midnight before bookmaker last_update19:00 and accepts it; source data clocks cannot be attested by such tests. It does sanitize transport key errors. Probe tests summarize payload structure only. Shared provider fix is not deployed under the collection freeze.',
    'Trial provenance test checks strings against empty/UNKNOWN; None becomes "None" and is not caught, and an unchanged list length does not freeze exact membership. No registry/test was executed or altered; stronger future schema must be isolated from protected cohorts. Earlier claims that unavailable originals are irrecoverable by construction are bounded by files actually received, not proof no original exists elsewhere.',
    'XG input-quality tests distinguish missing/invalid/unattested zero pairs and do not replace provenance. xg_model tests verify synthetic fit/prediction/cache wiring and diagnostic degradation, not statistical neutrality or code-version freshness. These constraints remain cross-referenced in CPL-P22/RCA-P10/CPL-P26 rather than relabeled as fixed.'
]
notes['batches'].append(dict(paths=paths, entire_returned_contents_read=True, recorded_at=datetime.now(UTC).isoformat(), source_hashes_at_recording={p: digest(repo / p)['sha256'] for p in paths}, findings=findings))
dump(root / 'semantic-review-notes-07.json', notes)
shutil.copyfile(root / 'semantic-review-notes-07.json', evidence / 'semantic-review-notes-07.json')
inventory = json.loads((evidence / 'source-inventory.json').read_text(encoding='utf-8'))
for row in inventory:
    if row['path'] in paths:
        assert row['review'] == 'inventory_static_or_targeted_review_only'
        row['review'] = 'semantic_read_with_recorded_findings'
        row['current_source_metadata'] = digest(repo / row['path'])
depth = dict(Counter(r['review'] for r in inventory))
assert depth == {'semantic_read_with_recorded_findings': 399, 'protected_contract_only_no_execution': 59}
dump(evidence / 'source-inventory.json', inventory)
dump(evidence / 'semantic-remaining.json', [])
coverage = dict(baseline_files=458, depth=depth, remaining_files=0, allowed_semantic_review_complete=True, all_sources_semantically_reviewed=False, protected_contract_status_preserved=True, new_changed_files_reviewed_separately=True, execution_not_implied=True)
dump(evidence / 'review-coverage.json', coverage)
registry = json.loads((docs / 'REGISTROS.json').read_text(encoding='utf-8'))
issue = next(r for r in registry['issues'] if r['id'] == 'CPL-P25')
issue.update(status='validado', action='Leitura semântica dos 399 arquivos não protegidos do inventário base concluída, com notas01–07 e hashes; 59 arquivos protegidos permanecem em contrato/metadados sem execução. Fontes novas e diffs revisados separadamente.', closure_test='evidence/source-inventory.json; evidence/review-coverage.json; evidence/semantic-review-notes-07.json', limitation='Fechamento da cobertura de leitura permitida, não alegação de zero bugs ou execução global. Defeitos legados compartilhados e validação operacional continuam nos bloqueios explícitos.')
claim = next(c for c in registry['claims'] if c['id'] == issue['claim'])
claim['found'] = issue['action']
claim['conclusion'] = 'alegação anterior refutada; revisão semântica permitida agora concluída, com fronteiras protegidas explícitas'
registry['dated_at'] = datetime.now(UTC).isoformat()
registry['summary']['status_counts'] = dict(Counter(r['status'] for r in registry['issues']))
registry['summary']['source_review'] = coverage
registry['mandate_complete'] = False
dump(docs / 'REGISTROS.json', registry)
lines = ['# Registro central — RES-20260910', '', 'Gerado de REGISTROS.json; limites originais preservados.', '', '| ID | Estado | Ação | Limite |', '| --- | --- | --- | --- |']
for row in registry['issues']:
    lines.append('| ' + ' | '.join(str(row.get(k, '')).replace('|', '/').replace('\n', ' ') for k in ('id', 'status', 'action', 'limitation')) + ' |')
(docs / 'REGISTROS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
result = (docs / 'RESULTADO.md').read_text(encoding='utf-8')
result = result.replace('há dependências protegidas/externas e 70 arquivos do inventário cuja revisão ainda é estática ou dirigida.', 'restam sete requisitos protegidos/externos no registro de 59 itens (52 validados). A leitura semântica dos 399 arquivos permitidos do inventário base está concluída; outros 59 permanecem restritos a contratos/metadados.')
result = result.replace('Concluir a revisão semântica enumerada em evidence/semantic-remaining.json, principalmente testes e contratos de infraestrutura.', 'A lista evidence/semantic-remaining.json está vazia para o inventário permitido. Notas07 registram os últimos 70 testes lidos e seus limites; leitura não equivale a executar toda a suíte.')
result += '\nA wheel foi fechada com os mesmos 231 módulos Python atuais antes da atualização final dos relatórios. O sdist conserva a documentação do instante da construção; a entrega Git/ZIP acompanha estes relatórios mais recentes. Não se afirma igualdade do sdist com documentação editada posteriormente.\n'
(docs / 'RESULTADO.md').write_text(result, encoding='utf-8')
continuation = '''# Continuação do trabalho

Continue em C:/BRASILEIRAO/brasileirao-predictor, solo. Leia os dois mandatos em C:/BRASILEIRAO/INSTRUCOES, o registro RES-20260910, RESULTADO e CONTRATOS. Confira HEAD/alterações e AUDITORIA/RESOLUCAO_2026-09-10.json. A revisão semântica permitida do inventário base foi concluída: 399 fontes/testes lidos, 59 protegidos limitados a contratos/metadados; notas07 e coverage guardam os limites. Não repetir leituras/testes já concluídos sem mudança ou preocupação concreta.

Há 52 itens validados e sete requisitos ainda bloqueados: CPL-P22 (dependências compartilhadas da coleta), CPL-P23 (ponte comercial e dados de modelo autenticados), CPL-P24 (estado/recibo legível da agenda), CPL-P26 (oferta, aceitação, capacidade e custos), RCA-P09 (engine Linux e CI global), RCA-P10 (fatos comerciais/contábeis autenticados), RCA-P11 (restauração operacional protegida e arquivos não recebidos). Os componentes corrigidos foram testados; isso não preenche fatos externos nem fecha defeitos legados compartilhados. Corrija o que for autorizado e verificável, sem apenas reclassificar bloqueios.

Preserve H14/H15/H9/A1, suas dependências, observações, resultados, claims, avaliadores e agendas. Não leia resultados intermediários, liquide, renove atestados ou execute testes que abram registros reais. Não autentique contas/aposte/movimente capital. Capital false; lucro executável ainda não demonstrado. Não repetir desempenho BE ou chamar novo holdout o já observado. Preserve decisão DC 11/09/2026 23:00 UTC, reserva20 e hashes dos helpers, sem duplicar agenda. Runners/ambientes/evidências: C:/BRASILEIRAO/work/resolution-2026-09-10. As correções não migraram a operação protegida.
'''
(docs / 'PROXIMO_PROMPT.md').write_text(continuation, encoding='utf-8')
(Path('C:/BRASILEIRAO/INSTRUCOES') / 'PROXIMO_PROMPT_APOS_RESOLUCAO_2026-09-10.md').write_text(continuation, encoding='utf-8')
for path in [repo / 'README.md', repo / 'HANDOFF.md', repo / 'docs/ESTADO_ATUAL.md', repo / 'docs/DATA_MAP.md', repo / 'docs/INDICE_DOCUMENTACAO.md', repo / 'docs/continuation/RETOMADA.md', Path('C:/BRASILEIRAO/LEIA_PRIMEIRO.md')]:
    text = path.read_text(encoding='utf-8')
    text = text.replace('revisão global ainda incompleta', 'leitura semântica permitida concluída; validação global ainda limitada')
    text = text.replace('revisão integral ainda incompleta', 'leitura semântica permitida concluída; requisitos externos/protegidos ainda abertos')
    if '399' not in text:
        text += '\nInventário base: 399 arquivos com leitura semântica e 59 protegidos limitados a contratos/metadados. Registro RES: 52 itens validados, sete bloqueados por requisitos especificados. Não significa zero bugs, CI global aprovado ou lucro demonstrado.\n'
    path.write_text(text, encoding='utf-8')
dump(evidence / 'manifest.json', {p.relative_to(docs).as_posix(): digest(p) for p in sorted(evidence.rglob('*')) if p.is_file() and p.name != 'manifest.json'})
print(json.dumps(dict(coverage=coverage, status_counts=registry['summary']['status_counts'])))
