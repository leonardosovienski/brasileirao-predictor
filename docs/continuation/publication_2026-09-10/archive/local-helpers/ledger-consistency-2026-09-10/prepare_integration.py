"""Exact-path staging; preserve ignored evidence logs and verify indexed bytes."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
docs = repo / 'docs/continuation/ledger_consistency_2026-09-10'
base = 'c2fd45675cf84cf6ba4ed637a111eaf5d6ba74ac'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=repo)

assert git('rev-parse', 'HEAD').decode().strip() == base
assert not git('diff', '--name-only', '--cached')
expected_code = {'brasileirao_predictor/bet_log.py', 'tests/test_completion_ledger.py', 'tests/test_ledger_consistency.py'}
guides = {'README.md', 'HANDOFF.md', 'docs/ESTADO_ATUAL.md', 'docs/DATA_MAP.md', 'docs/INDICE_DOCUMENTACAO.md', 'docs/continuation/RETOMADA.md'}
actual = set(git('diff', '--name-only').decode().splitlines())
assert actual == (expected_code - {'tests/test_ledger_consistency.py'}) | guides, actual
new = set(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
assert all(p == 'tests/test_ledger_consistency.py' or p.startswith('docs/continuation/ledger_consistency_2026-09-10/') for p in new)
manifest = json.loads((docs / 'evidence/manifest.json').read_text(encoding='utf-8'))
for relative, expected in manifest.items():
    path = docs / relative
    raw = path.read_bytes()
    assert path.resolve().is_relative_to(docs) and len(raw) == expected['bytes']
    assert hashlib.sha256(raw).hexdigest() == expected['sha256'], relative
files = sorted(expected_code | guides | {p.relative_to(repo).as_posix() for p in docs.rglob('*') if p.is_file()})
for name in files:
    raw = (repo / name).read_bytes()
    assert not re.search(rb'(?:AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|sk-proj-[A-Za-z0-9_-]{30,})', raw), name
# Force only enumerated new evidence paths. Keep global ignore rules intact.
subprocess.run(['git', 'add', '-f', '--', *files], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
assert set(git('diff', '--cached', '--name-only').decode().splitlines()) == set(files)
subprocess.run(['git', 'diff', '--cached', '--check'], cwd=repo, check=True)
verified = []
for path in (docs / 'evidence').rglob('*'):
    if path.is_file():
        name = path.relative_to(repo).as_posix()
        assert git('show', ':' + name) == path.read_bytes(), name
        verified.append(name)
(root / 'precommit.diff').write_bytes(git('diff', '--cached', '--binary'))
(root / 'staged-paths.json').write_text(json.dumps(files, indent=2) + '\n')
(root / 'index-evidence-check.json').write_text(json.dumps(dict(files=sorted(verified), byte_equality=True), indent=2) + '\n')
print(json.dumps(dict(base=base, staged_files=len(files), evidence_files=len(verified), ready=True)))
