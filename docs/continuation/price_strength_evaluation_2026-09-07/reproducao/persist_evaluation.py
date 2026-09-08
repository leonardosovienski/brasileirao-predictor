"""Preserve this concluded single-run study, keeping raw inputs outside Git."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
OUTPUT = WORKSPACE / 'outputs/TESTE_XG_REAL'
DOCS = REPO / 'docs/continuation/price_strength_evaluation_2026-09-07'
BACKUP = Path('C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07/price_strength_evaluation_2026-09-07')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert sha(source) == sha(target)


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


result = json.loads((OUTPUT / 'results.json').read_text())
audit = json.loads((OUTPUT / 'audit.json').read_text())
assert audit['status'] == 'PASS'
assert sha(OUTPUT / 'PLANO.json') == '507c69fc01aaabd9d78734b1153f740c3c347f601f5b1609cd54839a1698aaaa'
stage = json.loads((REPO / 'docs/continuation/price_strength_2026-09-07/estado.json').read_text())
unchanged = {name: sha(REPO / name) == expected for name, expected in stage['source_sha256'].items()}
assert all(unchanged.values())
protected_state = json.loads((REPO / 'docs/continuation/review_2026-09-07/estado_final.json').read_text())
protected = {name: sha(REPO / name) == value for name, value in protected_state['protected_sha256'].items()}
assert all(protected.values())
receipts = {name: json.loads((WORKSPACE / f'work/validation/{name}.json').read_text()) for name in (
    'price_strength_conditional_tests', 'price_strength_conditional_real', 'price_strength_conditional_audit')}
assert all(item['exit_code'] == 0 for item in receipts.values())
state = {
    'completed_at_utc': datetime.now(UTC).isoformat(), 'study_status': 'CLOSED_NEGATIVE_OR_MIXED_NO_GENERAL_IMPROVEMENT',
    'plan_sha256': sha(OUTPUT / 'PLANO.json'), 'results_sha256': sha(OUTPUT / 'results.json'),
    'audit_sha256': sha(OUTPUT / 'audit.json'), 'audit_status': 'PASS',
    'config_fingerprint': result['config_fingerprint'], 'coverage': result['coverage'],
    'economic_results': result['economics'], 'availability_policy': result['availability_policy'],
    'historical_real_data_used': True, 'operational_database_opened': False,
    'candidate_and_tests_unchanged_since_implementation': unchanged, 'protected_hash_checks': protected,
    'validation_receipts': receipts, 'synthetic_tests_passed': 26,
    'cross_book_comparison_evaluated': False, 'new_hyperparameter_search': False,
    'live_execution_proven': False, 'candidate_promoted': False, 'operational_schedules_changed': False,
    'previous_2026_T2_net_units_preserved': -1.23,
    'conclusion': 'Calibrated xG worsened hypothetical return; raw reduced loss but remained negative. Predictive improvement against old raw only in 1x2; market stronger than new candidates across all three.',
}
dump(OUTPUT / 'estado.json', state)
for name in ('RESULTADO.md', 'REPRODUZIR.md', 'PLANO.json', 'results.json', 'audit.json', 'estado.json'):
    copy(OUTPUT / name, DOCS / name)
for source in sorted(HERE.glob('*.py')):
    copy(source, DOCS / 'reproducao' / source.name)
    copy(source, BACKUP / 'reproducao' / source.name)
for source in sorted((HERE / 'inputs').glob('*.json')):
    copy(source, BACKUP / 'inputs' / source.name)
for source in sorted(OUTPUT.iterdir()):
    if source.is_file():
        copy(source, BACKUP / 'outputs' / source.name)
for name in receipts:
    for extension in ('json', 'log'):
        source = WORKSPACE / f'work/validation/{name}.{extension}'
        copy(source, DOCS / 'evidencias' / source.name)
        copy(source, BACKUP / 'validation' / source.name)
for name in ('validation_runner.py', 'guard/sitecustomize.py'):
    copy(WORKSPACE / 'work' / name, BACKUP / 'validation' / name)
for source in sorted((REPO / 'brasileirao_predictor/research/price_strength').glob('*')):
    if source.is_file():
        copy(source, BACKUP / 'candidate_code' / source.relative_to(REPO))
for relative in ('brasileirao_predictor/__init__.py', 'brasileirao_predictor/research/__init__.py'):
    copy(REPO / relative, BACKUP / 'candidate_code' / relative)
copy(REPO / 'HANDOFF.md', BACKUP / 'HANDOFF_snapshot.md')
copy(REPO / 'docs/continuation/RETOMADA.md', BACKUP / 'RETOMADA_snapshot.md')
files = [{'path': source.relative_to(BACKUP).as_posix(), 'bytes': source.stat().st_size, 'sha256': sha(source)}
         for source in sorted(BACKUP.rglob('*')) if source.is_file() and source.name != 'BACKUP_MANIFEST.json']
dump(BACKUP / 'BACKUP_MANIFEST.json', {'created_at_utc': datetime.now(UTC).isoformat(), 'files': files})
assert all(sha(BACKUP / item['path']) == item['sha256'] for item in files)
print(json.dumps({'candidate_files_unchanged': len(unchanged), 'protected_files_unchanged': len(protected),
                  'backup_files_verified': len(files), 'study_closed': True, 'audit': 'PASS'}, indent=2))
