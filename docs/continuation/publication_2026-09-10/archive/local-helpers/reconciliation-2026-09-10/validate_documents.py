"""Check new documentation links, source coverage and byte preservation before integration."""
import hashlib
import json
import re
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
docs = repo / 'docs/continuation/reconciliation_2026-09-10'
ev = docs / 'evidence'

def digest(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

files = list(docs.glob('*.md')) + [repo/p for p in ['README.md','HANDOFF.md','docs/ESTADO_ATUAL.md',
     'docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md']]
broken = []
checked = 0
for path in files:
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('#'):
            continue
        checked += 1
        dest = (path.parent / target.split('#')[0]).resolve()
        if not dest.is_file():
            broken.append({'file':str(path),'link':target})
preserved = json.loads((ev/'previous-guides.json').read_text(encoding='utf-8'))
for item in preserved.values():
    assert digest(Path(item['path'])) == {k:item[k] for k in ('bytes','sha256')}
registry = json.loads((docs/'REGISTROS.json').read_text(encoding='utf-8'))
issues = {r['id'] for r in registry['issues']}
assert len(issues) == len(registry['issues']) == 49
assert all(c['issue'] in issues for c in registry['claims'])
assert all(i in issues for h in registry['historical_reconciliation'] for i in h['current_related_issues'])
sections = json.loads((ev/'mandate-sections.json').read_text(encoding='utf-8'))
assert [int(r[0]) for r in sections['consolidated']] == list(range(1,14))
assert [int(r[0]) for r in sections['original']] == list(range(1,21))
report = {'local_markdown_links_checked':checked,'broken_links':broken,'preserved_guides':len(preserved),
          'issues':len(issues),'historical_issue_links':len(registry['historical_reconciliation']),
          'all_mandate_section_ids_present':True}
dump(root/'document-validation.json', report)
assert not broken, broken

# Preserve the initial build receipts/logs, then point final evidence at the
# successful rebuild containing the final README package metadata.
initial = ev/'package-initial'
initial.mkdir(exist_ok=False)
shutil.copyfile(ev/'package-receipt-final.json', initial/'package-receipt.json')
for path in (ev/'package-smoke-final').glob('*.log'):
    shutil.copyfile(path, initial/path.name)
latest = json.loads((root/'package-receipt-after-guides.json').read_text())
assert len(latest['commands']) == 7 and all(c['exit_code'] == c['expected'] for c in latest['commands'])
shutil.copyfile(root/'package-receipt-after-guides.json', ev/'package-receipt-final.json')
for path in (root/'package-after-guides').glob('*.log'):
    shutil.copyfile(path, ev/'package-smoke-final'/path.name)
shutil.copyfile(root/'document-validation.json',ev/'document-validation.json')
dump(ev/'manifest.json', {p.relative_to(docs).as_posix():digest(p) for p in sorted(ev.rglob('*')) if p.is_file() and p.name != 'manifest.json'})
print(json.dumps(report))
