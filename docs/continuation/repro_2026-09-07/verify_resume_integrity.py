import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

WORK=Path(__file__).resolve().parent
OUT=WORK.parent/'outputs'
ROOT=Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
before=json.loads((WORK/'resume_preflight_result.json').read_text(encoding='utf-8'))
actual={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in before['protected_sha256']}
mismatch=[name for name,value in actual.items() if value!=before['protected_sha256'][name]]
prefix_checks={}
backup=WORK/'retomada_backup'
for old in list((backup/'data/research').glob('h1[45]*.jsonl'))+list((backup/'data/odds_snapshots').glob('*.jsonl')):
    relative=old.relative_to(backup)
    prefix_checks[relative.as_posix()]=(ROOT/relative).read_bytes().startswith(old.read_bytes())
assert not mismatch, mismatch
assert all(prefix_checks.values()), prefix_checks
report={
    'checked_at':datetime.now(UTC).isoformat(),
    'protected_sha256':before['protected_sha256'],
    'protected_files_unchanged':True,
    'original_ledger_prefixes_preserved':prefix_checks,
    'wrapper_sha256':hashlib.sha256((ROOT/'brasileirao_scripts/run_passive_task.py').read_bytes()).hexdigest(),
    'scientific_metrics_computed':False,
    'horizon_choice':'B_KEEP_PASSIVE_PROSPECTIVE_COLLECTION',
    'h14_h15_enablement':'BLOCKED_BY_WINDOWS_ACCESS_DENIED',
}
(OUT/'retomada_integridade.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'protected_files_unchanged':True,'ledger_prefixes_preserved':len(prefix_checks),'wrapper_sha256':report['wrapper_sha256']}))
