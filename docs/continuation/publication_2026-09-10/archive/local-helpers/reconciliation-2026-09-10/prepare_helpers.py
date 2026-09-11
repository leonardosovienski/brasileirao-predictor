"""Adapt previously inspected integration helpers with an exact-path allowlist."""
from pathlib import Path

root = Path(__file__).resolve().parent
prior = Path('C:/BRASILEIRAO/work/artifact-integrity-2026-09-10')
old_base = '2220b42810aea6f656ed196507ff14a62349b83e'
new_base = '6c850454418a1c7e878fdb6a461dea509571caec'
for name in ('prepare_integration.py', 'backup_delivery.py'):
    text = (prior / name).read_text(encoding='utf-8')
    for old, new in [(old_base, new_base), ('artifact_integrity_2026-09-10','reconciliation_2026-09-10'),
                     ('BRASILEIRAO_ARI_20260910','BRASILEIRAO_RCA_20260910'),
                     ('brasileirao-predictor-ARI-20260910','brasileirao-predictor-RCA-20260910'),
                     ('INTEGRIDADE_ARTEFATOS_2026-09-10.json','CONCILIACAO_MANDATO_2026-09-10.json'),
                     ('ARI-20260910','RCA-20260910'),
                     ('PROXIMO_PROMPT_APOS_INTEGRIDADE_ARTEFATOS_2026-09-10.md','PROXIMO_PROMPT_APOS_CONCILIACAO_2026-09-10.md')]:
        text = text.replace(old, new)
    if name == 'prepare_integration.py':
        text = text.replace("'brasileirao_predictor/research/market_residual.py', 'tests/test_residual_artifact_integrity.py'",
                            "'brasileirao_predictor/research/calibration_gate.py', 'brasileirao_predictor/research/residual_gate.py', 'tests/test_reconciliation_gate_contracts.py'")
        text = text.replace('tests/test_residual_artifact_integrity.py', 'tests/test_reconciliation_gate_contracts.py')
    else:
        text = text.replace('package-smoke-final', 'package-after-guides')
        text = text.replace("'index-evidence-check.json', 'PLANO.md', 'pyright.json'",
                            "'index-evidence-check.json', 'PLANO.md', 'pyright.json', 'prepare_helpers.py', 'validate_documents.py', 'check_dependencies.py', 'verify_current_evidence.py', 'recover_chat.py', 'build_package_after_guides.py'")
        text = text.replace("git('bundle', 'create', str(bundle), '--all')", """for path in sorted((root / 'previous-guides').rglob('*')):
    if path.is_file():
        copy(path, Path('previous-guides') / path.relative_to(root / 'previous-guides'))
git('bundle', 'create', str(bundle), '--all')""")
    assert old_base not in text and 'artifact_integrity_2026-09-10' not in text
    (root / name).write_text(text, encoding='utf-8')

# README is package metadata and has changed since the first smoke. Preserve
# the first build and run a second, exclusively named output after guide edits.
text = (root / 'build_package.py').read_text(encoding='utf-8')
text = text.replace('package-smoke-final', 'package-after-guides')
text = text.replace('package-receipt-final.json', 'package-receipt-after-guides.json')
(root / 'build_package_after_guides.py').write_text(text, encoding='utf-8')
