"""Read-only reconciliation of session evidence, manifests and current source hashes."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
BACKUPS = Path('C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07')
OUT = ROOT / 'outputs/REVISAO_DO_CHAT'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


manifests, failures = [], []
for relative in ['', 'runtime_contracts_2026-09-07', 'model_research_2026-09-07',
                 'price_strength_2026-09-07', 'price_strength_evaluation_2026-09-07',
                 'price_strength_diagnosis_2026-09-07']:
    folder = BACKUPS / relative
    manifest_path = folder / 'BACKUP_MANIFEST.json'
    manifest = read(manifest_path)
    checks = []
    for item in manifest['files']:
        path = (folder / item['path']).resolve()
        if not path.is_relative_to(folder.resolve()):
            raise ValueError('manifest escapes archive')
        valid = path.is_file() and sha(path) == item['sha256']
        checks.append(valid)
        if not valid:
            failures.append(str(path))
    manifests.append({'archive': relative or 'initial_477', 'files': len(checks),
                      'passed': sum(checks), 'manifest_sha256': sha(manifest_path)})

runtime = read(ROOT / 'outputs/MELHORIA_RUNTIME/estado.json')
implementation = read(ROOT / 'outputs/IMPLEMENTACAO_PRECOS_XG/estado.json')
diagnosis = read(ROOT / 'outputs/DIAGNOSTICO_XG/estado.json')
expected = {**runtime['changed_sha256'], **implementation['source_sha256'], **diagnosis['source_sha256']}
source_checks = {name: {'expected': value, 'actual': sha(REPO / name)} for name, value in expected.items()}
assert all(value['actual'] == value['expected'] for value in source_checks.values())
protected = {name: sha(REPO / name) == value for name, value in runtime['protected_sha256'].items()}
assert len(protected) == 14 and all(protected.values())

closures = {}
for study in [ROOT / 'outputs/TESTE_XG_REAL', ROOT / 'outputs/DIAGNOSTICO_XG/CORRECAO']:
    files = read(study / 'MANIFEST.json')['files']
    checks = {name: sha(study / name) == value for name, value in files.items()}
    assert all(checks.values())
    closures[study.name] = {'files': len(checks), 'all_passed': True, 'manifest_sha256': sha(study / 'MANIFEST.json')}

helpers = {}
for name in ['evaluate.py', 'conditional_model.py', 'frozen_economics.py']:
    current = ROOT / 'work/price_strength_evaluation' / name
    archive = BACKUPS / 'price_strength_evaluation_2026-09-07/reproducao' / name
    helpers[name] = {'current_sha256': sha(current), 'earlier_archive_sha256': sha(archive),
                     'identical_to_archive_before_correction': sha(current) == sha(archive)}
assert all(value['identical_to_archive_before_correction'] for value in helpers.values())
result = {'verified_at_utc': datetime.now(UTC).isoformat(), 'status': 'PASS' if not failures else 'FAIL',
          'backup_manifests': manifests, 'total_archived_files': sum(item['files'] for item in manifests),
          'backup_failures': failures, 'current_sources': source_checks, 'protected_checks': protected,
          'study_manifests': closures, 'previous_helpers': helpers,
          'limits': 'Hashes prove agreement with saved bytes, not truth of input data, immutable timestamps or independent external validation.'}
(OUT / 'evidence_check.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'status': result['status'], 'archives': manifests, 'source_files': len(source_checks),
                  'protected_files': len(protected), 'helper_archive_identity': True}, indent=2))
assert not failures
