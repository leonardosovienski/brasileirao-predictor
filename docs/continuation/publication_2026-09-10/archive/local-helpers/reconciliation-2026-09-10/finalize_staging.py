"""Correct the chat phase export and recheck the entire already-reviewed index."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
docs = repo/'docs/continuation/reconciliation_2026-09-10'
evidence = docs/'evidence'
base = '6c850454418a1c7e878fdb6a461dea509571caec'

def git(*args):
    return subprocess.check_output(['git',*args],cwd=repo)

assert git('rev-parse','HEAD').decode().strip() == base
messages = json.loads((root/'chat-messages.json').read_text(encoding='utf-8'))
finals = [dict(visible_index=i+1, source_line=m['source_line'], timestamp=m['timestamp'],
               first_paragraph=m['text'].strip().split('\n\n')[0])
          for i,m in enumerate(messages) if m['role']=='assistant' and m['phase'] in ('final','final_answer')]
assert len(finals)==6
target = evidence/'chat-final-claims.json'
(root/'chat-final-claims-first-empty.json').write_bytes(target.read_bytes())
target.write_text(json.dumps(finals,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest = evidence/'manifest.json'
entries = json.loads(manifest.read_text(encoding='utf-8'))
raw = target.read_bytes()
entries[target.relative_to(docs).as_posix()] = dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
manifest.write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
git('add','-f','--',target.relative_to(repo).as_posix(),manifest.relative_to(repo).as_posix())
expected = json.loads((root/'staged-paths.json').read_text())
assert sorted(git('diff','--cached','--name-only').decode().splitlines()) == expected
for relative,value in entries.items():
    path=docs/relative
    raw=path.read_bytes()
    assert len(raw)==value['bytes'] and hashlib.sha256(raw).hexdigest()==value['sha256']
for path in evidence.rglob('*'):
    if path.is_file():
        assert git('show',':'+path.relative_to(repo).as_posix())==path.read_bytes()
wheel=next((root/'package-after-guides/dist').glob('*.whl'))
with zipfile.ZipFile(wheel) as z:
    metadata=z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))).decode('utf-8')
    assert (repo/'README.md').read_text(encoding='utf-8').strip() in metadata
git('diff','--cached','--check')
(root/'precommit.diff').write_bytes(git('diff','--cached','--binary'))
print(json.dumps({'staged_paths':len(expected),'chat_final_claims':len(finals),'indexed_evidence_equal':True,'wheel_current_readme_verified':True}))
