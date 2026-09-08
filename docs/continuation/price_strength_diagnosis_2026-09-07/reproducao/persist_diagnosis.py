"""Preserve one completed diagnostic/correction and its executable evidence."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
OUTPUT = ROOT / 'outputs/DIAGNOSTICO_XG'
DOCS = REPO / 'docs/continuation/price_strength_diagnosis_2026-09-07'
BACKUP = Path('C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07/price_strength_diagnosis_2026-09-07')
SOURCES = [
    'brasileirao_predictor/data/xg_quality.py', 'brasileirao_predictor/data/missingness_audit.py',
    'brasileirao_predictor/ingest_sofascore.py', 'brasileirao_predictor/research/price_strength/dynamic_xg.py',
    'brasileirao_predictor/research/price_strength_reliability.py',
    'tests/test_xg_input_quality.py', 'tests/test_missingness_audit.py',
    'tests/test_price_strength_dynamic_xg.py', 'tests/test_price_strength_reliability.py',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert sha(source) == sha(target)


audit = read(OUTPUT / 'CORRECAO/audit.json')
assert audit['status'].startswith('PASS')
bootstrap = read(OUTPUT / 'CORRECAO/bootstrap_audit.json')
assert bootstrap['status'].startswith('PASS')
result = read(OUTPUT / 'CORRECAO/results.json')
plan = read(OUTPUT / 'CORRECAO/PLANO.json')
assert sha(OUTPUT / 'CORRECAO/PLANO.json') == '2c9a6615f77c2568ecc70868ce8283f6bb6a5796c622df898bc3858927e11a92'
assert all(sha(ROOT / path) == expected for path, expected in plan['inputs'].items())
assert all(sha(Path(path)) == expected for path, expected in read(OUTPUT / 'CORRECAO/EXECUTION_LOCK.json')['source_sha256'].items())
before = read(HERE / 'protected_before.json')
protected = {row['path']: sha(REPO / row['path']) == row['sha256'] for row in before}
assert len(protected) == 14 and all(protected.values())
original = read(REPO / 'docs/continuation/price_strength_2026-09-07/estado.json')['source_sha256']
old_candidate_comparison = {name: sha(REPO / name) == expected for name, expected in original.items()}
assert {name for name, same in old_candidate_comparison.items() if not same} == {
    'brasileirao_predictor/research/price_strength/dynamic_xg.py', 'tests/test_price_strength_dynamic_xg.py'}
assert all(sha(REPO / name) == sha(ROOT / 'work/integration-repo' / name) for name in SOURCES)
required = ['xg_correction_plan', 'xg_correction_unit_tests', 'xg_correction_real',
            'xg_diagnosis_final_tests', 'xg_diagnosis_typecheck', 'xg_diagnosis_gates', 'xg_diagnosis_lint_final',
            'xg_diagnosis_format', 'price_strength_model_structure_synthetic', 'price_strength_frozen_diagnosis',
            'correction_audit_selfcheck', 'correction_independent_audit', 'price_strength_correction_bootstrap_audit']
assert all(read(ROOT / f'work/validation/{name}.json')['exit_code'] == 0 for name in required)
state = {
    'completed_at_utc': datetime.now(UTC).isoformat(), 'status': 'CLOSED_PARTIAL_LOSS_REDUCTION_NO_PROFIT',
    'new_study_plan_sha256': sha(OUTPUT / 'CORRECAO/PLANO.json'),
    'new_study_results_sha256': sha(OUTPUT / 'CORRECAO/results.json'),
    'audit_sha256': sha(OUTPUT / 'CORRECAO/audit.json'),
    'bootstrap_audit_sha256': sha(OUTPUT / 'CORRECAO/bootstrap_audit.json'),
    'audit_status': audit['status'], 'bootstrap_audit_status': bootstrap['status'],
    'coverage': result['coverage'], 'economics_common': result['economics_common'],
    'source_sha256': {name: sha(REPO / name) for name in SOURCES},
    'protected_hash_checks': protected,
    'previous_candidate_comparison': old_candidate_comparison,
    'previous_change_explanation': 'Only current revision-validation implementation and its tests changed; archived original source and studies untouched.',
    'historical_real_data_used': True, 'operational_database_opened': False,
    'tests_project_passed': 318, 'tests_skipped': 1, 'runner_tests_passed': 6, 'structural_tests_passed': 4,
    'audit_selfcheck_tests_passed': 6,
    'typechecked_source_files': 5, 'lint_format_and_static_gates_passed': True,
    'single_new_candidate_recipe': True, 'fit_year': 2024, 'evaluation_year': 2025,
    'evaluation_previously_seen': True, 'new_parameters_tuned_on_evaluation': False,
    'quality_only_changed_common_bets': False,
    'calibration_rates_2024_unchanged': True,
    'cross_book_comparison_evaluated': False, 'candidate_promoted': False,
    'real_capital_enabled': False, 'schedules_or_cohorts_changed': False,
    'previous_2026_T2_net_units_preserved': -1.23,
    'pending_integration': 'Redis/Compose unchanged; not exercised this stage.',
    'conclusion': 'Fewer/lower total hypothetical losses than calibrated xG, worse ROI than raw xG, no improvement in all markets and no edge over market.',
}
dump(OUTPUT / 'estado.json', state)
BACKUP.mkdir(parents=True, exist_ok=False)
DOCS.mkdir(parents=True, exist_ok=False)
for source in OUTPUT.rglob('*'):
    if source.is_file():
        copy(source, BACKUP / 'outputs/DIAGNOSTICO_XG' / source.relative_to(OUTPUT))
for source in (ROOT / 'outputs/TESTE_XG_REAL').rglob('*'):
    if source.is_file():
        copy(source, BACKUP / source.relative_to(ROOT))
for folder in (HERE, ROOT / 'work/price_strength_evaluation'):
    for source in folder.iterdir():
        if source.is_file() and source.suffix in ('.py', '.md', '.json'):
            copy(source, BACKUP / source.relative_to(ROOT))
for source in (ROOT / 'work/price_strength_evaluation/inputs').glob('*.json'):
    copy(source, BACKUP / source.relative_to(ROOT))
for name in ('RESULTADO.md', 'ACHADOS.md', 'REPRODUZIR.md', 'estado.json'):
    copy(OUTPUT / name, DOCS / name)
for name in ('PLANO.json', 'results.json', 'audit.json', 'bootstrap_audit.json', 'AUDITORIA_INDEPENDENTE.md'):
    copy(OUTPUT / 'CORRECAO' / name, DOCS / 'correcao' / name)
for source in HERE.iterdir():
    if source.is_file() and source.suffix in ('.py', '.md'):
        copy(source, DOCS / 'reproducao' / source.name)
for name in SOURCES:
    copy(REPO / name, BACKUP / 'codigo' / name)
    copy(REPO / name, DOCS / 'codigo' / name)
# Minimal package dependencies for reproducing pure experiments, not operational data.
for relative in ['brasileirao_predictor/__init__.py', 'brasileirao_predictor/research/__init__.py',
                 'brasileirao_predictor/data/__init__.py']:
    source = REPO / relative
    if source.exists():
        copy(source, BACKUP / 'codigo' / relative)
for source in (REPO / 'brasileirao_predictor/research/price_strength').glob('*.py'):
    copy(source, BACKUP / 'codigo' / source.relative_to(REPO))
for name in ('validation_runner.py', 'guard/sitecustomize.py', 'xg_diagnosis_pyright.json', 'check_price_strength_gates.py'):
    copy(ROOT / 'work' / name, BACKUP / 'work' / name)
    copy(ROOT / 'work' / name, DOCS / 'reproducao' / name)
for source in (ROOT / 'work/validation').glob('*'):
    if source.suffix not in ('.json', '.log'):
        continue
    if source.name.startswith(('xg_', 'correction_', 'price_strength_revision_', 'price_strength_reliability_',
                               'price_strength_model_structure_', 'price_strength_frozen_diagnosis',
                               'price_strength_correction_')):
        copy(source, BACKUP / 'work/validation' / source.name)
        copy(source, DOCS / 'evidencias' / source.name)
for name in ('HANDOFF.md', 'docs/continuation/RETOMADA.md'):
    copy(REPO / name, BACKUP / 'documentacao' / name)
files = [{'path': path.relative_to(BACKUP).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}
         for path in sorted(BACKUP.rglob('*')) if path.is_file()]
dump(BACKUP / 'BACKUP_MANIFEST.json', {'created_at_utc': datetime.now(UTC).isoformat(), 'files': files})
assert all(sha(BACKUP / row['path']) == row['sha256'] for row in files)
print(json.dumps({'backup_files_verified': len(files), 'protected_unchanged': len(protected),
                  'source_files': len(SOURCES), 'study_closed': True, 'audit': audit['status']}, indent=2))
