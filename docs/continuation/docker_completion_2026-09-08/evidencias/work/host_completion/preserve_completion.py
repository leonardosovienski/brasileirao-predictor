"""Archive the bounded host/Compose follow-up without changing closed evidence."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
OUT = ROOT / 'outputs/INTEGRACAO_DOCKER'
DOCS = REPO / 'docs/continuation/docker_completion_2026-09-08'
ARCHIVES = REPO.parent / 'brasileirao-predictor-sessoes/2026-09-07'
BACKUP = ARCHIVES / 'docker_completion_2026-09-08'


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


assert not DOCS.exists() and not BACKUP.exists(), 'Never overwrite a closed archive'
previous = read(ROOT / 'outputs/PENDENCIAS_CORRIGIDAS/estado.json')
for name, digest in (previous['source_sha256'] | previous['untouched_prior_sources_sha256'] | previous['protected_sha256']).items():
    assert sha(REPO / name) == digest, 'Unexpected source change: ' + name
archives = previous['previous_backup_manifests'] + [{
    'archive': 'runtime_recovery_2026-09-08', 'files': 275,
    'manifest_sha256': read(ROOT / 'outputs/PENDENCIAS_CORRIGIDAS/backup_receipt.json')['manifest_sha256'],
}]
for item in archives:
    folder = ARCHIVES if item['archive'] == 'initial_477' else ARCHIVES / item['archive']
    manifest_path = folder / 'BACKUP_MANIFEST.json'
    assert sha(manifest_path) == item['manifest_sha256']
    entries = read(manifest_path)['files']
    assert len(entries) == item['files']
    for entry in entries:
        path = (folder / entry['path']).resolve()
        assert path.is_relative_to(folder.resolve()) and sha(path) == entry['sha256'], str(path)
assert sum(item['files'] for item in archives) == 1273
for name, folder in [('TESTE_XG_REAL', ROOT / 'outputs/TESTE_XG_REAL'),
                     ('CORRECAO', ROOT / 'outputs/DIAGNOSTICO_XG/CORRECAO')]:
    assert sha(folder / 'MANIFEST.json') == previous['closed_studies'][name]['manifest_sha256']
    for relative, digest in read(folder / 'MANIFEST.json')['files'].items():
        assert sha(folder / relative) == digest, relative

manifest_path = ROOT / 'work/compose_completion/harness/manifest.json'
harness = read(manifest_path)
assert harness['configuration_parser_exit_code'] == 0
assert harness['synthetic_fixture_contract_passed'] and harness['synthetic_init_and_cache_read_passed']
assert harness['declared_source_count'] == 36 and harness['runtime_and_test_sources_equal']
assert not harness['daemon_or_container_started']
for relative, digest in harness['hashes'].items():
    assert sha(manifest_path.parent / relative) == digest, relative
runner_receipt_path = ROOT / 'work/compose_completion/runner_validation_final.json'
runner = read(runner_receipt_path)
assert runner['exit_code'] == 0 and runner['plan_only']
assert runner['docker_commands_executed_by_runner'] is False
for relative, digest in runner['script_sha256'].items():
    assert sha(runner_receipt_path.parent / relative) == digest, relative
preflight = read(ROOT / 'work/host_completion/preflight.json')
assert preflight['computer']['HypervisorPresent'] is False
assert preflight['elevated'] is False
assert preflight['elevation_attempt']['status'] == 'FAILED'
assert 'cancelada pelo usu' in preflight['elevation_attempt']['error']
probes = read(ROOT / 'work/host_completion/docker_probes.json')
assert all(p['exit_code'] != 0 and json.loads(p['stdout'])['Server'] is None for p in probes)

evidence = []
for folder in [ROOT / 'work/host_completion', ROOT / 'work/compose_completion']:
    evidence.extend(path for path in folder.rglob('*') if path.is_file() and '__pycache__' not in path.parts)
for source in sorted(evidence):
    copy(source, OUT / 'evidencias' / source.relative_to(ROOT))
state = {
    'verified_at_utc': datetime.now(UTC).isoformat(),
    'status': 'OFFLINE_HARNESS_FIXED_AND_VALIDATED; COMPOSE_BLOCKED_BY_WINDOWS_ELEVATION',
    'new_runtime_code_changes': False,
    'previous_sources_sha256_verified': previous['source_sha256'],
    'protected_sha256_verified': previous['protected_sha256'],
    'previous_backup_manifests': archives,
    'previous_backup_files_reverified': 1273,
    'closed_studies_reverified': True,
    'harness_manifest_sha256': sha(manifest_path),
    'compose_config_parser_exit_code': 0,
    'synthetic_vorp_contract_passed': True,
    'synthetic_database_init_and_load_passed': True,
    'synthetic_database_count': 2,
    'future_runner_validation': runner,
    'compose_build_up_e2e_executed': False,
    'remote_ci_executed': False,
    'new_application_test_suite_runs': 0,
    'host_preflight': preflight,
    'docker_local_probes': probes,
    'uac_requests': 1,
    'elevated_helper_executed': False,
    'boot_bios_features_restart_changes': False,
    'internal_producer_migration_missing': False,
    'operational_database_access': False,
    'fit_backtest_or_financial_actions': False,
    'commit_push_or_deployment': False,
    'remaining': [
        'Administrative read of the active boot entry and Windows virtualization components.',
        'Conditional host repair supported by the elevated diagnosis; reboot if that repair requires it.',
        'Docker Linux engine and actual Compose build/up/recovery/health tests.',
        'Remote CI for the final source state has not been executed.',
    ],
    'persistent_docs': str(DOCS),
    'persistent_backup': str(BACKUP),
}
write(OUT / 'estado.json', state)
note = '''
> ## CHECKPOINT — CONTINUAÇÃO DO DOCKER (08/09/2026, 12h UTC)
>
> Evidências: docs/continuation/docker_completion_2026-09-08/RESULTADO.md.
> Corrigida somente a fixture VORP do harness sintético: replacement_levels.
> O VORP real e o Compose/CI já tinham a chave correta. Parser, contrato da
> fixture e init/load de dois bancos sintéticos passaram. 36 fontes conferidas.
> Nenhum produtor interno real ficou sem migrar: publicações legadas são testes.
>
> Compose/CI remoto continuam pendentes. Firmware/SLAT habilitados, hipervisor
> ausente, dois pipes Docker indisponíveis. Uma tentativa normal de UAC para
> diagnóstico somente leitura foi cancelada pelo Windows; não houve repetição,
> execução elevada, alteração de boot/BIOS/componentes ou reinicialização.
> A próxima etapa depende de acesso administrativo ao diagnóstico do host.
> Ler RESULTADO.md e o harness novo antes de executar containers.
> 14 protegidos, 1273 arquivos arquivados e estudos fechados reconferidos.
> Sem mudança do runtime, banco operacional, fit, capital, commit ou push.

'''
for relative, addition in [('HANDOFF.md', note), ('docs/continuation/RETOMADA.md', '''
> Etapa mais recente: [continuação Docker](docker_completion_2026-09-08/RESULTADO.md).
> Fixture de teste corrigida; validações offline passaram. Acesso administrativo
> não foi concedido pelo Windows; Compose continua sem execução em containers.
> Ler o primeiro checkpoint do HANDOFF e os limites do relatório.

''')]:
    path = REPO / relative
    heading, remainder = path.read_text(encoding='utf-8-sig').split('\n', 1)
    path.write_text(heading + '\n' + addition + remainder, encoding='utf-8')
for source in sorted(OUT.rglob('*')):
    if source.is_file():
        copy(source, DOCS / source.relative_to(OUT))
        copy(source, BACKUP / 'outputs/INTEGRACAO_DOCKER' / source.relative_to(OUT))
for relative in ['HANDOFF.md', 'docs/continuation/RETOMADA.md']:
    copy(REPO / relative, BACKUP / 'code' / relative)
entries = [{'path': path.relative_to(BACKUP).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}
           for path in sorted(BACKUP.rglob('*')) if path.is_file()]
write(BACKUP / 'BACKUP_MANIFEST.json', {'created_at_utc': datetime.now(UTC).isoformat(), 'files': entries})
for entry in entries:
    assert sha(BACKUP / entry['path']) == entry['sha256']
receipt = {'verified_at_utc': datetime.now(UTC).isoformat(), 'backup': str(BACKUP),
           'files': len(entries), 'total_bytes': sum(entry['bytes'] for entry in entries),
           'manifest_sha256': sha(BACKUP / 'BACKUP_MANIFEST.json'), 'all_copies_verified': True,
           'receipt_location_note': 'Outside manifest to avoid circular dependency.'}
write(OUT / 'backup_receipt.json', receipt)
copy(OUT / 'backup_receipt.json', DOCS / 'backup_receipt.json')
print(json.dumps({'status': 'ARCHIVE_VERIFIED; HOST_STILL_BLOCKED', 'protected': 14,
                  'previous_backup_files_reverified': 1273, 'new_backup': receipt}, indent=2))
