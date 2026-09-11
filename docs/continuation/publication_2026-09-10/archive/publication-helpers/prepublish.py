"""Inventory new Git blobs and check high-confidence credential patterns."""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path('C:/BRASILEIRAO/work/publication-2026-09-10')
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
base = 'ac22c56c3318623e07a722f34d44dc6cd877ea37'
def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args])

objects = git('rev-list', '--objects', f'{base}..HEAD').decode().splitlines()
names = dict(line.split(' ', 1) if ' ' in line else (line, '') for line in objects)
raw = subprocess.run(['git', '-C', str(repo), 'cat-file', '--batch'], input=('\n'.join(names)+'\n').encode(), capture_output=True, check=True).stdout
patterns = {
    'github_token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b',
    'aws_access_key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'private_key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'openai_key': rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}\b',
    'slack_token': rb'\bxox[baprs]-[A-Za-z0-9-]{30,}\b',
}
findings, inventory = [], []
def check(path, content, oid):
    inventory.append({'path': path, 'git_object': oid, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
    for name, pattern in patterns.items():
        for match in re.finditer(pattern, content):
            findings.append({'path': path, 'object': oid, 'line': content[:match.start()].count(b'\n')+1, 'kind': name})

pos = 0
while pos < len(raw):
    end = raw.index(b'\n', pos)
    oid, kind, size = raw[pos:end].decode().split()
    start = end+1
    content = raw[start:start+int(size)]
    pos = start+int(size)+1
    if kind == 'blob':
        check(names[oid], content, oid)
for item in git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0'):
    if item:
        check(item, (repo/item).read_bytes(), None)
receipt = {'at_utc': datetime.now(timezone.utc).isoformat(), 'base':base, 'head':git('rev-parse','HEAD').decode().strip(), 'scope':'new historical Git blobs plus untracked publication files; pattern scan does not prove absence of every secret', 'findings':findings, 'files':inventory}
(root/'prepublish-scan.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps({'blob_versions':len(inventory),'bytes':sum(x['bytes'] for x in inventory),'findings':findings}))
raise SystemExit(bool(findings))
