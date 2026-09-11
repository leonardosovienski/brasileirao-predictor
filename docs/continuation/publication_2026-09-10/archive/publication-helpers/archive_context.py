"""Archive visible decisions, instructions and local reproduction helpers."""
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

base = Path('C:/BRASILEIRAO')
repo = base / 'brasileirao-predictor'
work = base / 'work/publication-2026-09-10'
dest = repo / 'docs/continuation/publication_2026-09-10'
dest.mkdir(exist_ok=True)
(dest / 'evidence').mkdir(exist_ok=True)
(dest / '.gitattributes').write_text('evidence/** -text whitespace=cr-at-eol\narchive/** -text whitespace=cr-at-eol\n',encoding='utf-8')
manifest = []
def archive(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = source.read_bytes()
    if target.exists() and target.read_bytes() != raw:
        raise ValueError('archive_already_exists_with_other_bytes')
    target.write_bytes(raw)
    manifest.append({'source': str(source), 'archive':str(target.relative_to(repo)).replace('\\','/'), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()})

for name in ['PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md', 'MANDATO_RECEBIDO_2026-09-09.txt']:
    archive(base / 'INSTRUCOES' / name, dest / 'archive/instructions' / name)
for name in ['chat-visible.txt', 'chat-visible.json', 'chat-receipt.json', 'checkpoint.json']:
    archive(work / name, dest / 'archive/chat' / name)
for stage in sorted((base / 'work').iterdir()):
    if not stage.is_dir() or stage.name.endswith('.git') or stage == work:
        continue
    for source in sorted(stage.iterdir()):
        if source.is_file() and source.suffix.lower() in {'.py', '.ps1', '.md'}:
            archive(source, dest / 'archive/local-helpers' / stage.name / source.name)

for name in ['python-portable-first', 'python-portable-final']:
    for filename in ['isolation.json', 'junit.xml']:
        archive(work/name/filename,dest/'evidence'/name/filename)
    archive(work/(name+'.log'),dest/'evidence'/(name+'.log'))

(dest / 'evidence/archive-manifest.json').write_text(json.dumps({'at':datetime.now(UTC).isoformat(),'items':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
paths = [base/'work/data-completion-2026-09-09/public_sources/football_data_bra_origin_csv.csv',base/'work/data-completion-2026-09-09/followup_capture.py',base/'work/data-completion-2026-09-09/audit_followup.py']
data = [{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
followup = base/'work/data-completion-2026-09-09/followup'
receipt = {'at':datetime.now(UTC).isoformat(),'scope':'hash/existence only, no outcomes, APIs, quota or operation changes','files':data,'followup_attempt_exists':(followup/'attempt.json').exists(),'followup_receipt_exists':(followup/'receipt.json').exists(),'followup_capture_exists':(followup/'capture.json').exists(),'decision_utc':'2026-09-11T23:00:00Z','automation_active_status':'not verifiable from prior app text; not inferred from missing local definition'}
(dest/'evidence/source-metadata.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
# Only immediate folder metadata: no protected database/content inspection.
folders = [{'name':p.name,'kind':'directory' if p.is_dir() else 'file','bytes':None if p.is_dir() else p.stat().st_size} for p in sorted(base.iterdir())]
(dest/'evidence/folder-index.json').write_text(json.dumps({'at':datetime.now(UTC).isoformat(),'root':str(base),'items':folders},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'archived':len(manifest),'bytes':sum(x['bytes'] for x in manifest),'source_metadata':receipt}))
