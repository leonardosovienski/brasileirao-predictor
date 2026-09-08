import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[2]
repo = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
old = json.loads((root / 'outputs/CORRECAO_RUNTIME/estado.json').read_text(encoding='utf-8'))
names = set(old['source_sha256']) | set(old['unchanged_prior_sources_sha256']) | set(old['protected_sha256'])
names |= {'dotnet/LineupWorker/OperationalSettings.cs', 'dotnet/LineupWorker/Program.cs',
          'dotnet/LineupWorker/appsettings.json', 'compose.yaml', 'Dockerfile.kernel', 'Dockerfile.cli', 'Dockerfile.worker'}
out = root / 'work/pending_closure/before'
out.mkdir(exist_ok=True)
files = {}
for name in sorted(names):
    source = repo / name
    # Other agents own their changes; their immediate snapshots attest those sources.
    files[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    target = out / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
(out.parent / 'root_before.json').write_text(json.dumps({'created_at_utc': datetime.now(UTC).isoformat(),
    'files_sha256': files, 'prior_stage_sources_sha256': old['source_sha256'],
    'protected_sha256': old['protected_sha256']}, indent=2) + '\n', encoding='utf-8')
print('Snapshot recorded; original prior-stage hashes retained separately.')
