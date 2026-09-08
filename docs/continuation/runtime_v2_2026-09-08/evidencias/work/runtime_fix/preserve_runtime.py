"""Verify and preserve runtime v2 evidence; no application imports or study runs."""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
ISOLATED = ROOT / 'work/integration-repo'
OUT = ROOT / 'outputs/CORRECAO_RUNTIME'
ARCHIVES = REPO.parent / 'brasileirao-predictor-sessoes/2026-09-07'
DOCS = REPO / 'docs/continuation/runtime_v2_2026-09-08'
BACKUP = ARCHIVES / 'runtime_v2_2026-09-08'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert sha(source) == sha(target), str(target)


assert not BACKUP.exists() and not DOCS.exists(), 'Do not rewrite completed archives'
before = read(OUT / 'before.json')
old = read(ROOT / 'outputs/REVISAO_DO_CHAT/estado.json')
py = read(ROOT / 'work/runtime_fix/kernel_python_receipt.json')
dotnet = read(ROOT / 'work/runtime_fencing/DOTNET_FINAL_MANIFEST.json')
sources = {entry['path']: entry['sha256'] for entry in py['source'] + dotnet}
root_sources = [
    '.github/workflows/ci.yml', 'brasileirao_scripts/hotpath_smoke.py',
    'tests/test_hotpath_smoke.py', 'dotnet/LineupWorker.Tests/KernelCrossProcessTests.cs',
    'contracts/redis-protocol-v2.schema.json', 'contracts/redis-fair-odds-v2.schema.json',
    'contracts/redis-protocol-v2.md',
]
sources.update({name: sha(REPO / name) for name in root_sources})
assert len(sources) == 25
for name, digest in sources.items():
    assert sha(REPO / name) == digest, name
    if not name.endswith('.md'):
        assert sha(ISOLATED / name) == digest, 'Tested copy differs: ' + name
unchanged = {}
for name, digest in before['source_sha256'].items():
    if name not in sources:
        assert sha(REPO / name) == digest, name
        unchanged[name] = digest
protected = before['protected_sha256']
assert len(protected) == 14
for name, digest in protected.items():
    assert sha(REPO / name) == digest, name

archives = old['previous_backup_manifests'] + [{
    'archive': 'whole_chat_review_2026-09-08', 'files': 48,
    'manifest_sha256': before['parent_review_manifest_sha256'],
}]
for item in archives:
    folder = ARCHIVES if item['archive'] == 'initial_477' else ARCHIVES / item['archive']
    manifest = folder / 'BACKUP_MANIFEST.json'
    assert sha(manifest) == item['manifest_sha256']
    entries = read(manifest)['files']
    assert len(entries) == item['files']
    for entry in entries:
        target = (folder / entry['path']).resolve()
        assert target.is_relative_to(folder.resolve())
        assert sha(target) == entry['sha256'], str(target)
    item['verified_after_runtime_v2'] = True
assert sum(item['files'] for item in archives) == 812

for name, folder in [('TESTE_XG_REAL', OUT.parent / 'TESTE_XG_REAL'),
                     ('CORRECAO', OUT.parent / 'DIAGNOSTICO_XG/CORRECAO')]:
    manifest = folder / 'MANIFEST.json'
    assert sha(manifest) == before['closed_studies'][name]['manifest_sha256']
    for relative, digest in read(manifest)['files'].items():
        target = (folder / relative).resolve()
        assert target.is_relative_to(folder.resolve())
        assert sha(target) == digest, str(target)
for name, item in old['transitive_helper_retrospective_evidence'].items():
    assert sha(ROOT / 'work/price_strength_evaluation' / name) == item['current_sha256']

required = py['receipts'] + [
    'work/validation/runtime_v2_smoke_final3.json',
    'work/validation/runtime_v2_smoke_lint_final.json',
    'work/validation/runtime_v2_smoke_format_check.json',
    'work/validation/runtime_v2_smoke_pyright_verified.json',
    'work/validation/runtime_v2_static.json',
    'work/runtime_fix/validation/dotnet_v2_fourth.json',
    'work/runtime_fix/validation/dotnet_v2_warnaserror.json',
    'work/runtime_fix/validation/runtime_v2_cross_process.json',
]
receipts = {}
for relative in required:
    path = ROOT / relative
    receipt = read(path)
    assert receipt['exit_code'] == 0, relative
    receipts[relative] = {'sha256': sha(path), 'exit_code': 0, 'command': receipt['command']}
smoke_pyright = (ROOT / 'work/validation/runtime_v2_smoke_pyright_verified.log').read_text(encoding='utf-8-sig')
assert 'Total files checked: 1' in smoke_pyright and '0 errors, 0 warnings' in smoke_pyright
coverage_path = next((ISOLATED / 'artifacts/dotnet-runtime-v2-fourth').rglob('coverage.cobertura.xml'))
coverage = ET.parse(coverage_path).getroot().attrib
assert int(coverage['lines-covered']) == 695 and int(coverage['lines-valid']) == 807
assert int(coverage['branches-covered']) == 233 and int(coverage['branches-valid']) == 290
assert float(coverage['line-rate']) >= .8 and float(coverage['branch-rate']) >= .8
cleaned = read(ROOT / 'work/runtime_fix/redis_env_review_runtime/cleaned.json')
assert cleaned['port_no_longer_accepts_connections'] == 26380

evidence = set()
for pattern in ['kernel_v2_*', 'runtime_v2_*']:
    evidence.update(p for p in (ROOT / 'work/validation').glob(pattern) if p.is_file())
evidence.update((ROOT / 'work/runtime_fix/validation').glob('*'))
for folder in [ROOT / 'work/runtime_fix', ROOT / 'work/runtime_fencing']:
    evidence.update(p for p in folder.iterdir() if p.is_file() and p.suffix in {'.py', '.json', '.md'})
for folder in (ROOT / 'work/runtime_fix').glob('lua_boundary_audit_*'):
    evidence.update(p for p in folder.rglob('*') if p.is_file())
env = ROOT / 'work/runtime_fix/redis_env_review_runtime'
evidence.update(p for p in env.iterdir() if p.is_file() and p.suffix in {'.json', '.log', '.sh', '.conf'})
evidence.update(p for p in (env / 'receipts').rglob('*') if p.is_file())
for relative in ['work/validation_runner.py', 'work/guard/sitecustomize.py']:
    evidence.add(ROOT / relative)
for directory in ['artifacts/dotnet-runtime-v2-fourth', 'artifacts/runtime-v2-cross-process']:
    evidence.update(p for p in (ISOLATED / directory).rglob('*') if p.is_file() and p.suffix in {'.trx', '.xml'})
for source in sorted(evidence):
    copy(source, OUT / 'evidencias' / source.relative_to(ROOT))

(OUT / 'RESOLUCAO_DA_REVISAO.md').write_text('''# Resolução dos achados intermediários

Os achados de ROOT_COMPAT_REVIEW.md foram corrigidos depois daquela leitura:
o smoke compara o snapshot de lineup, o prazo do request e idempotency_key;
as fixtures têm envelope v2 completo e usam o parser efetivo do kernel.
Os 12 testes finais e o teste real entre processos passaram após as correções.

Recibos intermediários preservam falhas reais de compilação, setup, tipagem,
formatação e probes incompatíveis com a revisão em teste. A rodada Redis que
deselecionou testes e a checagem Pyright sem arquivos não contam como aprovação.
Somente os recibos explicitamente listados em estado.json fundamentam os
números finais. Probes Lua definitivos: lua_boundary_audit_20260908T033058.

A revisão foi interna. Não houve execução Compose nem CI remoto nesta etapa.
Os arquivos de reprodução registram caminhos desta máquina; outra máquina
precisa adaptar caminhos e provisionar sua própria instância descartável.
Não apontar os testes para Redis operacional. Arquivos fonte oficiais grandes
do provisionamento ficaram no scratch; os URLs, hashes e comandos foram
preservados no conjunto de evidências e na cópia persistente.
''', encoding='utf-8')

state = {
    'verified_at_utc': datetime.now(UTC).isoformat(),
    'status': 'RUNTIME_FIXES_VALIDATED_LOCALLY_WITH_DOCUMENTED_DEPLOYMENT_LIMITS',
    'source_sha256': sources, 'tested_copy_identical_count': 24,
    'documentation_only_source': 'contracts/redis-protocol-v2.md',
    'unchanged_prior_sources_sha256': unchanged,
    'protected_sha256': protected, 'protected_checks': {name: True for name in protected},
    'previous_backup_manifests': archives, 'previous_archived_files_verified': 812,
    'closed_studies': before['closed_studies'], 'closed_studies_reverified': True,
    'transitive_helpers_unchanged': True,
    'validation_receipts': receipts,
    'validation_counts': {'python_kernel_unit_passed': 139, 'python_smoke_unit_passed': 12,
                          'python_redis_integration_passed': 18, 'dotnet_suite_passed': 81,
                          'dotnet_suite_cross_process_skipped': 1,
                          'separate_cross_process_passed': 1, 'separate_cross_process_skipped': 0},
    'coverage': coverage, 'coverage_existing_gate_percent': 80,
    'redis': read(env / 'ready.json'), 'redis_cleanup': cleaned,
    'internal_review': True, 'docker_compose_executed': False, 'remote_ci_executed': False,
    'no_new_economic_fit_or_backtest': True, 'profitability_established': False,
    'live_database_access': False, 'financial_actions': False, 'commit_or_push': False,
    'remaining_limits': [
        'Deploy producer and consumer together on protocol v2; no deployment performed.',
        'Docker daemon unavailable; WSL2 HCS_E_HYPERV_NOT_INSTALLED; Compose not validated.',
        'Redis standalone only; durability depends on Redis persistence and exceptional server failures.',
        'Pub/Sub fair-ready and final signals have no acknowledgement; lost fair-ready may abstain.',
        'Pending recovery starts at accepted registration and ends at original 60-second expiry.',
        'Pre-registration retry is bounded; upstream must recover longer failures or process loss.',
        'Provider CapturedAt is not an authenticated revision clock.',
        'Synthetic tests establish code behavior, not executable odds, financial edge or profit.',
    ],
    'persistent_docs': str(DOCS), 'persistent_backup': str(BACKUP),
}
write(OUT / 'estado.json', state)

checkpoint = '''
> ## CHECKPOINT — FALHAS DO RUNTIME CORRIGIDAS (08/09/2026 UTC)
>
> Evidências: docs/continuation/runtime_v2_2026-09-08/RESULTADO.md e estado.json.
> As pendências de resposta antiga e reserva consumida descritas abaixo foram
> corrigidas nesta etapa: protocolo v2, snapshot/registro atômicos, versão atual,
> lease com dono, retry, recuperação de pendências e publicação final condicionada.
> Fila trata o item realmente descartado; saúde tem TTL e token de sessão.
> Smoke, schemas e workflow atualizados; produtor e consumidor devem migrar juntos.
>
> 151 unitários Python (139 kernel + 12 smoke), 18 integrações Redis reais,
> 81 testes .NET e 1 entre processos passaram. O caso entre processos pulado
> na suíte comum foi executado separadamente. Cobertura .NET: 86,12% linhas,
> 80,34% ramos; gates existentes de 80% passaram. Build Release sem warnings.
> Redis 8.2.1 próprio em WSL1 foi encerrado e a distro temporária removida.
> Docker/Compose e CI remoto NÃO executados. Validação e revisão são internas.
>
> Pub/Sub segue sem ACK; perda de fair-ready pode resultar em abstenção. Retry
> antes do registro é limitado; pending não é fila permanente. Standalone somente.
> Não houve implantação, banco operacional, novo fit/backtest ou ação financeira.
> 14 hashes protegidos, 812 arquivos de backups e os estudos fechados conferidos.
> Fórmulas, configuração, coortes, agendas e resultados econômicos preservados.
> Nova cópia: brasileirao-predictor-sessoes/2026-09-07/runtime_v2_2026-09-08/.
> Os checkpoints abaixo são históricos; rentabilidade continua não demonstrada.

'''
for relative, note in [('HANDOFF.md', checkpoint), ('docs/continuation/RETOMADA.md', '''
> Etapa mais recente: [correções do runtime v2](runtime_v2_2026-09-08/RESULTADO.md).
> Respostas antigas, lease/retry, descarte de fila e saúde corrigidos. Passaram
> 151 unitários Python, 18 integrações Redis, 81 .NET e 1 entre processos.
> Redis real validado; ambiente temporário removido. Compose/CI remoto pendentes.
> Produtor e consumidor devem migrar juntos. Ler os limites no relatório e o
> primeiro checkpoint do HANDOFF. Não houve novo resultado econômico.

''')]:
    path = REPO / relative
    heading, remainder = path.read_text(encoding='utf-8-sig').split('\n', 1)
    path.write_text(heading + '\n' + note + remainder, encoding='utf-8')

for name in sources:
    copy(REPO / name, OUT / 'codigo' / name)
for source in sorted(OUT.rglob('*')):
    if source.is_file():
        copy(source, DOCS / source.relative_to(OUT))
        copy(source, BACKUP / 'outputs/CORRECAO_RUNTIME' / source.relative_to(OUT))
for relative in ['HANDOFF.md', 'docs/continuation/RETOMADA.md']:
    copy(REPO / relative, BACKUP / 'code' / relative)
entries = [{'path': p.relative_to(BACKUP).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
           for p in sorted(BACKUP.rglob('*')) if p.is_file()]
write(BACKUP / 'BACKUP_MANIFEST.json', {'created_at_utc': datetime.now(UTC).isoformat(),
      'scope': 'Runtime v2 source snapshots, synthetic validation and cleanup receipts; no original archives rewritten.',
      'files': entries})
for entry in entries:
    assert sha(BACKUP / entry['path']) == entry['sha256']
receipt = {'created_at_utc': datetime.now(UTC).isoformat(), 'backup': str(BACKUP),
           'files': len(entries), 'total_bytes': sum(e['bytes'] for e in entries),
           'manifest_sha256': sha(BACKUP / 'BACKUP_MANIFEST.json'), 'all_copies_verified': True,
           'receipt_location_note': 'Outside manifest to avoid circular hash dependency.'}
write(OUT / 'backup_receipt.json', receipt)
copy(OUT / 'backup_receipt.json', DOCS / 'backup_receipt.json')
print(json.dumps({'status': 'PASS', 'sources': len(sources), 'protected': 14,
                  'old_archived_files': 812, 'new_backup': receipt}, ensure_ascii=False, indent=2))
