"""Preserve final recovery evidence without importing the application or rerunning studies."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
WORK = ROOT / 'work/pending_closure'
ISOLATED = ROOT / 'work/integration-repo'
OUT = ROOT / 'outputs/PENDENCIAS_CORRIGIDAS'
ARCHIVES = REPO.parent / 'brasileirao-predictor-sessoes/2026-09-07'
DOCS = REPO / 'docs/continuation/runtime_recovery_2026-09-08'
BACKUP = ARCHIVES / 'runtime_recovery_2026-09-08'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert sha(source) == sha(target), str(target)


assert not DOCS.exists() and not BACKUP.exists(), 'Never overwrite a closed archive'
previous = read(ROOT / 'outputs/CORRECAO_RUNTIME/estado.json')
checks = read(WORK / 'final_checks.json')
sources = checks['source_sha256']
for name, digest in sources.items():
    assert sha(REPO / name) == digest, name
    if name not in checks['documentation_only']:
        assert sha(ISOLATED / name) == digest, 'Tested copy differs: ' + name
untouched = {}
for name, digest in (previous['source_sha256'] | previous['unchanged_prior_sources_sha256']).items():
    if name not in sources:
        assert sha(REPO / name) == digest, 'Unexpected source change: ' + name
        untouched[name] = digest
protected = previous['protected_sha256']
assert len(protected) == 14
for name, digest in protected.items():
    assert sha(REPO / name) == digest, name

archives = previous['previous_backup_manifests'] + [{
    'archive': 'runtime_v2_2026-09-08', 'files': 186,
    'manifest_sha256': read(ROOT / 'outputs/CORRECAO_RUNTIME/backup_receipt.json')['manifest_sha256'],
}]
for item in archives:
    folder = ARCHIVES if item['archive'] == 'initial_477' else ARCHIVES / item['archive']
    manifest = folder / 'BACKUP_MANIFEST.json'
    assert sha(manifest) == item['manifest_sha256']
    entries = read(manifest)['files']
    assert len(entries) == item['files']
    for entry in entries:
        target = (folder / entry['path']).resolve()
        assert target.is_relative_to(folder.resolve()) and sha(target) == entry['sha256'], str(target)
    item['verified_after_recovery'] = True
assert sum(item['files'] for item in archives) == 998
for name, folder in [('TESTE_XG_REAL', ROOT / 'outputs/TESTE_XG_REAL'),
                     ('CORRECAO', ROOT / 'outputs/DIAGNOSTICO_XG/CORRECAO')]:
    manifest = folder / 'MANIFEST.json'
    assert sha(manifest) == previous['closed_studies'][name]['manifest_sha256']
    for relative, digest in read(manifest)['files'].items():
        target = (folder / relative).resolve()
        assert target.is_relative_to(folder.resolve()) and sha(target) == digest, str(target)

receipts = {}
for relative in checks['final_receipts']:
    path = ROOT / relative
    result = read(path)
    assert result['exit_code'] == 0, relative
    receipts[relative] = {'sha256': sha(path), 'exit_code': 0, 'command': result['command']}
coverage = ET.parse(ROOT / checks['coverage_path']).getroot().attrib
assert float(coverage['line-rate']) >= .8 and float(coverage['branch-rate']) >= .8
host_receipt = read(ROOT / checks['host_receipt'])
assert host_receipt['status'] == 'PASS' and host_receipt['dbsize_after'] == 0
cleaned = read(WORK / 'redis_env_pending_closure/cleaned.json')
assert cleaned['port_no_longer_accepts_connections'] == 26380

evidence = set(p for p in WORK.iterdir() if p.is_file() and p.suffix in {'.py', '.json', '.md', '.ps1'})
for directory in ['validation', 'environment_review', 'compose_isolated', 'watchdog_before']:
    evidence.update(p for p in (WORK / directory).rglob('*') if p.is_file())
for pattern in ['host_process_evidence_*', 'outbox_acl_*']:
    for folder in WORK.glob(pattern):
        evidence.update(p for p in folder.rglob('*') if p.is_file())
env = WORK / 'redis_env_pending_closure'
evidence.update(p for p in env.iterdir() if p.is_file() and p.suffix in {'.json', '.log', '.sh', '.conf'})
evidence.update(p for p in (env / 'receipts').rglob('*') if p.is_file())
evidence.update(p for p in (ROOT / 'work/validation').glob('pending_inbox_*') if p.is_file())
for relative in ['work/validation_runner.py', 'work/guard/sitecustomize.py',
                 'work/runtime_fix/synthetic_kernel_process.py', checks['coverage_path']]:
    evidence.add(ROOT / relative)
for directory in checks['artifact_directories']:
    evidence.update(p for p in (ROOT / directory).rglob('*') if p.is_file() and p.suffix in {'.xml', '.trx'})
for source in sorted(evidence):
    copy(source, OUT / 'evidencias' / source.relative_to(ROOT))
for relative in sources:
    copy(REPO / relative, OUT / 'codigo' / relative)

state = {
    'verified_at_utc': datetime.now(UTC).isoformat(),
    'status': 'CODE_RECOVERY_FIXED_AND_VALIDATED; COMPOSE_BLOCKED_BY_HOST',
    'source_sha256': sources, 'untouched_prior_sources_sha256': untouched,
    'tested_copy_identical': True, 'documentation_only': checks['documentation_only'],
    'protected_sha256': protected, 'protected_checks': {name: True for name in protected},
    'previous_backup_manifests': archives, 'previous_archived_files_verified': 998,
    'closed_studies': previous['closed_studies'], 'closed_studies_reverified': True,
    'validation_counts': checks['validation_counts'], 'coverage': coverage,
    'coverage_gate_unchanged_percent': 80, 'final_validation_receipts': receipts,
    'host_process_receipt': host_receipt, 'redis_cleanup': cleaned,
    'docker_compose_config_validated': True, 'docker_compose_build_run_executed': False,
    'remote_ci_executed': False, 'internal_review_only': True,
    'remaining_host_action': 'Elevated boot diagnosis; hypervisor absent this boot, WSL2 HCS_E_HYPERV_NOT_INSTALLED. No boot/BIOS/feature changes or reboot performed.',
    'contract_limits': [
        'Canonical stream ingestion required for recovery; legacy Pub/Sub remains volatile.',
        'Input accepted by Redis only; publisher must retry writes not accepted or with uncertain replies.',
        'Finite economic lifetime is unchanged; retention does not authorize late execution.',
        'Outbox holds last 10000 batches; no financial executor or exactly-once order guarantee.',
        'Redis standalone persistence governs loss of server state.',
        'Legacy snapshots lacking recorded watchdog deadline cannot prove their original deadline.',
        'Provider clock/data provenance and profitability cannot be inferred from synthetic tests.',
    ],
    'new_economic_fit_or_backtest': False, 'profitability_established': False,
    'financial_actions': False, 'live_database_access': False, 'commit_or_push': False,
    'persistent_docs': str(DOCS), 'persistent_backup': str(BACKUP),
}
write(OUT / 'estado.json', state)

note = f'''
> ## CHECKPOINT — RECUPERAÇÃO E PENDÊNCIAS DE SOFTWARE (08/09/2026 UTC)
>
> Evidências: docs/continuation/runtime_recovery_2026-09-08/RESULTADO.md e estado.json.
> Inbox Redis com ACK/reclaim, índice ready e outbox corrigem perdas de entrada,
> aviso e saída. Watchdog tem deadline/índice persistidos, sem depender de RAM.
> Health exige os dois loops ativos por sessão/instância; lineup exige 11 titulares.
> Cliente respeita usuário ACL e recusa DB inválido. Dockerfiles usam locks,
> contexto exclui dados/segredos e CI isola o projeto de teste.
>
> Python: 154 unitários e 30 integrações Redis passaram. .NET:
> {checks['validation_counts']['dotnet_full_passed']} testes na suíte e 1 E2E separado passaram; limites de 80% preservados.
> Host .NET real e kernel Python: inicialização, smoke por stream e health após
> parada abrupta passaram.
> Redis descartável encerrado e distro própria removida. Verificação interna.
>
> Compose build/up e CI remoto NÃO executados: engine ausente, hipervisor não
> ativo nesta inicialização, WSL2 HCS_E_HYPERV_NOT_INSTALLED. Diagnóstico de boot
> exige sessão elevada; nenhuma mudança de boot/BIOS/reboot foi feita.
> Inbox deve substituir produtores Pub/Sub legados para recuperação. Validade
> econômica não foi estendida; outbox não é executor nem promessa de lucro.
> 14 arquivos protegidos, 998 arquivos arquivados e estudos fechados conferidos.
> Sem fit/backtest, banco operacional, capital, coortes/agenda, commit ou push.
> Backup: brasileirao-predictor-sessoes/2026-09-07/runtime_recovery_2026-09-08/.
> Checkpoints abaixo são históricos. Ler limites e migração antes de implantar.

'''
for relative, addition in [('HANDOFF.md', note), ('docs/continuation/RETOMADA.md', '''
> Etapa mais recente: [recuperação e pendências de software](runtime_recovery_2026-09-08/RESULTADO.md).
> Inbox, ready, outbox, watchdog persistente e health corrigidos e testados.
> Redis e processos reais validados; Compose ainda depende de correção do host.
> Ler primeiro checkpoint do HANDOFF, estado.json e limites de migração.
> Nenhum resultado econômico novo ou capital liberado.

''')]:
    path = REPO / relative
    heading, remainder = path.read_text(encoding='utf-8-sig').split('\n', 1)
    path.write_text(heading + '\n' + addition + remainder, encoding='utf-8')
for source in sorted(OUT.rglob('*')):
    if source.is_file():
        copy(source, DOCS / source.relative_to(OUT))
        copy(source, BACKUP / 'outputs/PENDENCIAS_CORRIGIDAS' / source.relative_to(OUT))
for relative in ['HANDOFF.md', 'docs/continuation/RETOMADA.md']:
    copy(REPO / relative, BACKUP / 'code' / relative)
entries = [{'path': p.relative_to(BACKUP).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
           for p in sorted(BACKUP.rglob('*')) if p.is_file()]
write(BACKUP / 'BACKUP_MANIFEST.json', {'created_at_utc': datetime.now(UTC).isoformat(), 'files': entries})
for entry in entries:
    assert sha(BACKUP / entry['path']) == entry['sha256']
receipt = {'created_at_utc': datetime.now(UTC).isoformat(), 'backup': str(BACKUP),
           'files': len(entries), 'total_bytes': sum(e['bytes'] for e in entries),
           'manifest_sha256': sha(BACKUP / 'BACKUP_MANIFEST.json'), 'all_copies_verified': True,
           'receipt_location_note': 'Outside manifest to avoid circular dependency.'}
write(OUT / 'backup_receipt.json', receipt)
copy(OUT / 'backup_receipt.json', DOCS / 'backup_receipt.json')
print(json.dumps({'status': 'PASS', 'sources': len(sources), 'protected': 14,
                  'old_backup_files_verified': 998, 'new_backup': receipt}, indent=2))
