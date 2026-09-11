import hashlib
import json
import shutil
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
docs=repo/'docs/continuation/resolution_2026-09-10'; evidence=docs/'evidence'
def digest(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def dump(p,x):
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

newpaths=['dotnet/LineupWorker.Tests/'+n for n in '''OperationalSettingsTests.cs WorkerHealthTests.cs FairOddsRecoveryTests.cs KernelInvocationIdentityTests.cs WatchdogRecoveryTests.cs LineupStreamTests.cs FairOddsCorrelationTests.cs KernelCrossProcessTests.cs WorkerRuntimeFencingTests.cs WorkerRuntimeTests.cs'''.split()]
newpaths+=['dotnet/LineupWorker/packages.lock.json','scripts/migration/build_data_archive.py']
newpaths+=['tests/'+n for n in '''test_audit_fixes.py test_backtest_extended.py test_backtest_odds.py test_backup_restore.py test_benchmark_panel_fixes.py test_bookmaker_odds.py test_bookmaker_stability.py test_bootstrap.py test_brasileirao_domain.py test_build_data_archive.py test_capture_decision.py test_capture_sofascore_event.py test_closing_scenario.py test_collection_only_archive.py'''.split()]
notes=json.loads((root/'semantic-review-notes-05.json').read_text(encoding='utf-8'))
notes['batches'].append(dict(paths=newpaths,entire_returned_contents_read=True,recorded_at=datetime.now(UTC).isoformat(),source_hashes_at_recording={p:digest(repo/p)['sha256'] for p in newpaths},findings=[
'All listed sources read fully; truncated WorkerRuntime tail and lock header, backtest_extended tail/backtest_odds and build_data_archive test middle were fetched again. No operational tests/DBs/cohort evaluations were run from this batch.',
'.NET recovery tests cover lost wakeup/index/outbox retention, final Redis fence, lease/version identity, input redaction, bounded queue, watchdog persistence, heartbeat ownership and process cleanup. Mock correlation does not replace real Redis; runtime suite and latest installed cross-process both passed. Timed fixture sleeps are host-sensitive, not production timing guarantees. Cross-process synthetic full-fill signal does not certify commerce.',
'NuGet lock reviewed: direct Hosting10.0.10 and StackExchange.Redis3.0.17; transitive graph includes RESPite/System.IO.Hashing and Microsoft.Extensions. locked restore/build passed in owned copy; no current vulnerability audit claimed.',
'Archive builder checks explicit plan/exclusions, size/hash/Windows collisions and preserves snapshot maps; it permits private configs only when explicitly selected by a migration plan. Not a Git-publication filter. Nested ZIP audit is filenames/metadata, not semantic proof of arbitrary payload safety. Test fixtures use synthetic .env text, not credentials.',
'Backtest tests validate legacy markets/orientation and nearest-date matching, not independent event identity or price availability. Some tests encode the old date-tolerance/source assumptions; they do not cure protected ingestion. Audit numerical tests are fixed synthetic instances, not universal CI inclusion properties or economic proof.',
'Benchmark tests verify paired sign/baseline/serving wiring, but bootstrap constant-vector test cannot prove the actual block algorithm and turno chronology test cannot prove official return legs after postponements. Some end-to-end tests call load_config and must not run under private-data audit without redirected fixtures.',
'Bookmaker tests distinguish aliases/ambiguous fixtures and selections, but midnight kickoff tolerance and legacy last-update closing remain assumptions. Stability is source coverage classification, not acceptance/liquidity. Bootstrap width assertions hold for fixed synthetic cases; not mathematical universal guarantees. Domain test named all-synthetic also reads config.yaml; not run.',
'Capture decision tests enforce API identity, cutoff, receipt/hash/size, missing latest payload, duplicate clock and abstention with unknown fixed costs. Sofascore capture tests do not model network delay crossing kickoff, actual available-at or all concurrent writers. Closing-scenario tests verify conditional cashflow and day-level lock only. Collection-only tests use synthetic rows and lifecycle retries; no protected source content read.'
]))
dump(root/'semantic-review-notes-06.json',notes)
shutil.copyfile(root/'semantic-review-notes-06.json',evidence/'semantic-review-notes-06.json')
inventory=json.loads((repo/'docs/continuation/reconciliation_2026-09-10/evidence/source-inventory.json').read_text(encoding='utf-8'))
read={p for b in notes['batches'] for p in b['paths']}
changed=set(subprocess.check_output(['git','diff','--name-only'],cwd=repo,stderr=subprocess.PIPE).decode().splitlines())
for row in inventory:
    if row['review']=='protected_contract_only_no_execution':
        assert row['path'] not in changed
    elif row['path'] in read:
        row['review']='semantic_read_with_recorded_findings'
    row['current_source_metadata']=digest(repo/row['path'])
pending=[r for r in inventory if r['review']=='inventory_static_or_targeted_review_only']
dump(evidence/'source-inventory.json',inventory);dump(evidence/'semantic-remaining.json',pending)
coverage=dict(baseline_files=len(inventory),depth=dict(Counter(r['review'] for r in inventory)),remaining_files=len(pending),all_sources_semantically_reviewed=False,new_changed_files_reviewed_separately=True,protected_contract_status_preserved=True)
dump(evidence/'review-coverage.json',coverage)
registry=json.loads((docs/'REGISTROS.json').read_text(encoding='utf-8'))
issue=next(r for r in registry['issues'] if r['id']=='CPL-P25')
issue['action']=f'Revisão ampliada: {coverage["depth"]}. Restam {len(pending)} arquivos com revisão estática/dirigida, enumerados em evidence/semantic-remaining.json. Novas fontes e diffs verificados separadamente.'
next(c for c in registry['claims'] if c['id']==issue['claim'])['found']=issue['action']
for c in registry['claims']:
    if c.get('issue') in {'RCA-P04','RCA-P05','RCA-P06','RCA-P07','RCA-P08'}:
        c['conclusion']='alegação original refutada como geral; correção confirmada no escopo sintético'
dump(docs/'REGISTROS.json',registry)
lines=['# Registro central — RES-20260910','','Gerado de REGISTROS.json; limites originais preservados.','','| ID | Estado | Ação | Limite |','| --- | --- | --- | --- |']
for r in registry['issues']:
    lines.append('| '+' | '.join(str(r.get(k,'')).replace('|','/').replace('\n',' ') for k in ('id','status','action','limitation'))+' |')
(docs/'REGISTROS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
for foldername in ('package-final','package-final-cli','installed-cross-final'):
    folder=root/foldername
    for p in folder.iterdir():
        if p.is_file() and p.suffix in {'.log','.json'}:
            target=evidence/foldername/p.name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(p,target)
    if foldername=='installed-cross-final':
        for p in folder.rglob('*.trx'):
            target=evidence/foldername/p.name;shutil.copyfile(p,target)
package=json.loads((root/'package-final/receipt.json').read_text())
cli=json.loads((root/'package-final-cli/receipt.json').read_text())
cross=json.loads((root/'installed-cross-final/receipt.json').read_text())
assert cli['completed'] and cross['server_stopped'] and all(c['exit_code']==0 for c in cross['commands'])
dump(evidence/'package-summary.json',dict(sdist_and_wheel_succeeded=True,wheel_modules_byte_equal=len(package['wheel_source_bytes_checked']),artifacts=package['artifacts'],installation_without_pythonpath=True,explicit_reuse_of_RI_dependencies=True,cli_checks_completed=True,original_script_expected_code_error_preserved=True,latest_cross_process_passed=1,redis_stopped=True))
result=(docs/'RESULTADO.md').read_text(encoding='utf-8').replace('95 arquivos',f'{len(pending)} arquivos')
result=result.replace('Pacote final, instalação e ensaio entre processos terão seus recibos anexados antes da integração.',f'Sdist offline e wheel derivada passaram; {len(package["wheel_source_bytes_checked"])} módulos conferidos byte a byte. Wheel instalada em venv separado sem PYTHONPATH, reutilizando explicitamente dependências RI. CLI help/health e novo ensaio entre processos passaram; Redis encerrado. O primeiro roteiro esperou indevidamente saída 1 sem configuração: o contrato retorna 2. Falha preservada e verificação correta separada em package-final-cli; não foi alterado o produto para satisfazer o roteiro.')
(docs/'RESULTADO.md').write_text(result,encoding='utf-8')
contracts=(docs/'CONTRATOS.md').read_text(encoding='utf-8')
contracts+='''
## Outros contratos corrigidos

O entrypoint instalado brasileirao-kernel usa kernel_cli:main. --healthcheck exige caminhos/configuração válidos (erro de argumentos = 2), consulta Redis sem importar NumPy/Numba/modelo/DB, usa limites de conexão/leitura e retorna 1 se indisponível. Logs mostram somente classe da exceção. PubSub mantém no máximo 32 handlers, com poller durável limitado separadamente a 32; não é um limite global de 32. Parâmetros do kernel são validados antes de cliente/JIT, com grade inteira de 1 a 100 e valores finitos.

Player stats v2 conserva available_at pós-jogo ou desconhecido, sem convertê-lo em instante pré-jogo. Promovidos exigem inteiros, equipes/posições únicas, quatro promovidos por temporada e JSON sem chaves repetidas. O detector estrutural exige preço soft e referência dentro da idade admitida, odds imutáveis e parâmetros finitos; o solver power expande o bracket. Fontes antigas de clocks continuam limitadas.

O importador OU2.5 v3 exige caminho de DB inexistente; lê/hash/parseia os mesmos bytes, rejeita odds não finitas/<=1 e contagens fracionárias/inválidas. Publica por hard link exclusivo somente após integrity_check e fsync do temporário próprio. Falhas deixam temporário preservado; não há importação operacional implícita. Backup recusa symlink/junction e destino dentro da árvore copiada; URI SQLite usa Path.as_uri e manifesto é verificado também no destino.

odds_shop não carrega configuração no import. Modo online exige clocks conhecidos e mercados completos com casas únicas; --from-file não pode disparar --tempos online. A saída é diagnóstico, não recomenda aposta nem anuncia janela economicamente validada. Uso de API metered continua condicionado a plano/quota/reserva verificados antes de executar a CLI; ela não foi usada para coleta nesta etapa.

Liquidação diagnóstica v2 exige source_event_id correspondente, placares inteiros não negativos e probabilidades finitas normalizadas. Hash da previsão vincula os fatos; fact_hash separa resultado de settled_at e content_hash protege recibo. Writer lock coordena autores cooperantes; retry idêntico mantém o primeiro recibo, conflito é rejeitado. Registros v1 não são migrados automaticamente e precisam de conciliação explícita. Não há execução financeira ou liquidação de coortes.

coverage_report exige presença de todas as fontes definidas, medição branch e contagens inteiras coerentes. Zero denominador é N/A. Inclui kernel_cli e kernel_redis_v2. A cobertura .NET não é hardcoded; exige recibo separado. Não foi afirmado que todo o gate Python passou nesta revisão parcial.
'''
(docs/'CONTRATOS.md').write_text(contracts,encoding='utf-8')
dump(evidence/'manifest.json',{p.relative_to(docs).as_posix():digest(p) for p in sorted(evidence.rglob('*')) if p.is_file() and p.name!='manifest.json'})
print(json.dumps(dict(coverage=coverage,modules=len(package['wheel_source_bytes_checked']),python=335,dotnet=160,latest_cross=1)))
