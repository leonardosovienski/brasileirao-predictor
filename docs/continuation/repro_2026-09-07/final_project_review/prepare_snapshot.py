import hashlib
import json
from pathlib import Path
import shutil
import subprocess

LIVE = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
WORK = Path(__file__).resolve().parent
DEST = WORK/'repo'


def git(*args):
    return subprocess.check_output(['git', '-C', str(LIVE), *args], text=True, encoding='utf-8')


paths = set(git('diff', '--name-only', 'HEAD').splitlines())
paths.update(git('ls-files', '--others', '--exclude-standard').splitlines())
copied = {}
for name in sorted(paths):
    rel = Path(name)
    if rel.is_absolute() or '..' in rel.parts or rel.parts[0] in ('data', '.venv', 'work') or rel.name.startswith('.env'):
        raise ValueError(f'Unexpected overlay file: {name}')
    source, target = LIVE/rel, DEST/rel
    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    else:
        raise ValueError(f'Deletion needs explicit handling: {name}')
(WORK/'snapshot_manifest.json').write_text(json.dumps({'head':git('rev-parse','HEAD').strip(),
    'source':str(LIVE),'snapshot':str(DEST),'overlay_sha256':copied,
    'live_database_copied':False,'credentials_copied':False},indent=2)+'\n',encoding='utf-8')
print(f'Isolated snapshot updated: {len(copied)} overlay files')
