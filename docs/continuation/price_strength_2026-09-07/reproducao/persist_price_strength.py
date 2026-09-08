"""Verify and preserve the isolated implementation without changing frozen backups."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

workspace = Path(__file__).resolve().parent.parent
repo = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
isolated = workspace / 'work/integration-repo'
output = workspace / 'outputs/IMPLEMENTACAO_PRECOS_XG'
docs = repo / 'docs/continuation/price_strength_2026-09-07'
backup = Path('C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07/price_strength_2026-09-07')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert sha(source) == sha(target)


code = sorted((repo / 'brasileirao_predictor/research/price_strength').glob('*.py'))
tests = sorted((repo / 'tests').glob('test_price_strength_*.py'))
assert len(code) == 7 and len(tests) == 4
source_hashes = {}
for source in code + tests:
    relative = source.relative_to(repo)
    source_hashes[relative.as_posix()] = sha(source)
    assert sha(source) == sha(isolated / relative), f'Untested source mismatch: {relative}'
reference = json.loads((repo / 'docs/continuation/review_2026-09-07/estado_final.json').read_text())
protected = {name: sha(repo / name) == expected for name, expected in reference['protected_sha256'].items()}
assert all(protected.values())
checks = ['price_strength_final_tests', 'price_strength_lint_green', 'price_strength_format',
          'price_strength_typecheck_green', 'price_strength_gates', 'price_strength_demo']
receipts = {name: json.loads((workspace / f'work/validation/{name}.json').read_text()) for name in checks}
assert all(receipt['exit_code'] == 0 for receipt in receipts.values())
assert 'Total files checked: 7' in (workspace / 'work/validation/price_strength_typecheck_green.log').read_text()
demo = output / 'demo/run'
manifest = json.loads((demo / 'manifest.json').read_text())
for name, item in manifest['artifacts'].items():
    assert sha(demo / name) == item['sha256']
for source in code:
    assert sha(source) == manifest['source_code'][source.name]['sha256']
summary = json.loads((demo / 'summary.json').read_text())
assert summary['calibrated_forecasts'] == 4 and summary['calibration']['n_matches'] == 8
assert summary['data_kind'] == 'SYNTHETIC_DEMONSTRATION' and not summary['profitability_established']
copy(repo / 'brasileirao_predictor/research/price_strength/README.md', output / 'GUIA.md')
state = {
    'created_at_utc': datetime.now(UTC).isoformat(),
    'request': 'Implementar comparação entre casas e candidato dinâmico xG independente.',
    'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
    'source_sha256': source_hashes,
    'protected_hash_checks': protected,
    'checks': receipts,
    'test_result': {'passed': 141, 'skipped': 1, 'reason': 'Windows denied synthetic symlink creation'},
    'demo': {'synthetic_only': True, 'historical_matches': 24, 'calibration_targets': 8, 'evaluation_fixtures': 4,
             'manifest_sha256': sha(demo / 'manifest.json')},
    'discarded_check': 'price_strength_typecheck checked zero files due to inherited research exclusion; replaced by explicit config.',
    'real_data_backtest_run': False, 'real_capital_enabled': False, 'profitability_established': False,
    'legacy_training_gate_changed': False, 'new_dependencies': False, 'commit_created': False,
    'previous_pending': 'Redis/Compose integration from runtime stage remains pending; not required by offline research.',
    'reproduction': 'See GUIA.md and copied validation_runner.py, guard/sitecustomize.py, price_strength_pyright.json.',
}
dump(output / 'estado.json', state)
for name in ['RESULTADO.md', 'GUIA.md', 'estado.json']:
    copy(output / name, docs / name)
for path in sorted((workspace / 'work/validation').glob('price_strength_*')):
    if path.is_file():
        copy(path, docs / 'evidencias' / path.name)
for source in code + tests:
    copy(source, docs / 'codigo' / source.relative_to(repo))
auxiliary = ['validation_runner.py', 'guard/sitecustomize.py', 'price_strength_pyright.json',
             'check_price_strength_gates.py', 'persist_price_strength.py']
for name in auxiliary:
    copy(workspace / 'work' / name, docs / 'reproducao' / name)
for source in sorted(docs.rglob('*')):
    if source.is_file():
        copy(source, backup / 'documentacao' / source.relative_to(docs))
for source in sorted((output / 'demo').rglob('*')):
    if source.is_file():
        copy(source, backup / 'demo' / source.relative_to(output / 'demo'))
copy(repo / 'HANDOFF.md', backup / 'HANDOFF_snapshot.md')
copy(repo / 'docs/continuation/RETOMADA.md', backup / 'RETOMADA_snapshot.md')
entries = [{'path': path.relative_to(backup).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}
           for path in sorted(backup.rglob('*')) if path.is_file() and path.name != 'BACKUP_MANIFEST.json']
dump(backup / 'BACKUP_MANIFEST.json', {'created_at_utc': datetime.now(UTC).isoformat(), 'files': entries})
for item in entries:
    assert sha(backup / item['path']) == item['sha256']
print(json.dumps({'source_files_verified': len(source_hashes), 'protected_files_verified': len(protected),
                  'backup_files_verified': len(entries), 'tests_passed': 141, 'synthetic_demo_verified': True,
                  'docs': str(docs), 'backup': str(backup)}, ensure_ascii=False, indent=2))
