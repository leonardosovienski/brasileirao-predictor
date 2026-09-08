"""Capture the pre-fix runtime and read-only preservation baselines."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[2]
repo = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
out = root / 'outputs/CORRECAO_RUNTIME'
out.mkdir(parents=True, exist_ok=True)
state = json.loads((root / 'outputs/REVISAO_DO_CHAT/estado.json').read_text(encoding='utf-8'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
protected = {name: sha(repo / name) for name in state['protected_sha256']}
assert protected == state['protected_sha256']
names = list(state['source_sha256']) + [
    'contracts/redis-protocol-v1.schema.json',
    'dotnet/LineupWorker/Models/LineupEvent.cs',
    'tests/test_kernel_runtime.py',
]
files = {}
for name in names:
    source = repo / name
    files[name] = sha(source)
    if name in state['source_sha256']:
        assert files[name] == state['source_sha256'][name], name
    target = root / 'work/runtime_fix/before' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert sha(target) == files[name]
record = {
    'created_at_utc': datetime.now(UTC).isoformat(),
    'source_sha256': files,
    'protected_sha256': protected,
    'closed_studies': state['closed_studies'],
    'parent_review_manifest_sha256': json.loads((root / 'outputs/REVISAO_DO_CHAT/backup_receipt.json').read_text())['manifest_sha256'],
    'scope': 'Correct runtime ordering, failure recovery and integration validation. No new economic study.',
}
(out / 'before.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'sources': len(files), 'protected': len(protected)}))
