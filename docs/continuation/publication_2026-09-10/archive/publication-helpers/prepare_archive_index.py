"""Index Markdown and archive current publication work before integration."""
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

base=Path('C:/BRASILEIRAO')
repo=base/'brasileirao-predictor'
work=base/'work/publication-2026-09-10'
dest=repo/'docs/continuation/publication_2026-09-10'
def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')
def dump(path,data):write(path,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
for file in work.iterdir():
    if file.is_file() and file.suffix in {'.py','.ps1'}:
        target=dest/'archive/publication-helpers'/file.name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(file,target)
for src,name in [('pyright.log','pyright-before.log'),('pyright-final.log','pyright-final.log')]:
    shutil.copyfile(work/src,dest/'evidence'/name)
dump(dest/'evidence/download-recovery.json',{'recorded_at':datetime.now(UTC).isoformat(),'first_transport':'GitHub API authenticated with credential already used for git; values never logged','failure':'ConnectionResetError 10054 while downloading the first large Python artifact; small artifacts and job logs preserved','recovery':'GitHub connector materialized the two large ZIPs; downloaded using its returned file references; SHA256 and sizes match official artifact metadata; ZIP CRC verified','failed_run_id':34544695904,'ci_run_failed':False})
# Save only new visible conversation content; the initial snapshot remains immutable.
source=Path('C:/Users/leona/.codex/sessions/2026/09/09/rollout-2026-09-09T21-05-07-01a088a1-e7c6-7e93-9ae6-dacd3b43b2a5.jsonl')
raw=source.read_bytes()
messages=[]
for line in raw.splitlines():
    row=json.loads(line); p=row.get('payload',{})
    if row.get('type')!='response_item' or p.get('type')!='message' or p.get('role') not in {'user','assistant'} or p.get('channel') in {'analysis','summary'}:continue
    content='\n'.join(v['text'] for v in p.get('content',[]) if v.get('type') in {'input_text','output_text','text'} and 'text' in v)
    if not content or content.startswith(('<recommended_plugins>','<environment_context>')):continue
    content=re.sub(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{30,}|AKIA[0-9A-Z]{16}','[REDACTED_TOKEN]',content)
    messages.append({'timestamp':row.get('timestamp'),'role':p['role'],'phase':p.get('phase'),'text':content})
dump(dest/'archive/chat/publication-continuation.json',messages[134:])
dump(dest/'archive/chat/publication-continuation-receipt.json',{'at':datetime.now(UTC).isoformat(),'source_snapshot_sha256':hashlib.sha256(raw).hexdigest(),'source_bytes':len(raw),'initial_messages':134,'additional_visible_messages':len(messages[134:]),'cutoff':'before final Git integration; subsequent execution is described by publication/recovery receipts, not a future final answer'})
tracked=subprocess.check_output(['git','-C',str(repo),'ls-files','-z']).decode().split('\0')
untracked=subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard','-z']).decode().split('\0')
paths=sorted({p for p in tracked+untracked if p.endswith('.md') and (repo/p).is_file()})
current={'README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md'}
rows=['# Todos os Markdown versionados ou preparados para publicação','','Índice de navegação, sem reescrever relatórios históricos. Atual designa os guias PUB e os pontos de entrada; histórico/contrato exige leitura da data e do escopo. Arquivos sob archive são cópias preservadas.','','| Documento | Classificação |','| --- | --- |']
inventory=[]
for name in paths:
    if name.endswith('/INDICE_TODOS_MDS.md'):continue
    status='atual' if name in current or (name.startswith('docs/continuation/publication_2026-09-10/') and '/archive/' not in name and '/evidence/' not in name) else ('arquivo preservado' if '/archive/' in name else 'histórico ou contrato: conferir data/escopo')
    link=os.path.relpath(repo/name,dest).replace('\\','/')
    rows.append(f'| [{name}](<{link}>) | {status} |')
    inventory.append({'path':name,'classification':status})
write(dest/'INDICE_TODOS_MDS.md','\n'.join(rows)+'\n')
dump(dest/'evidence/document-index.json',{'at':datetime.now(UTC).isoformat(),'markdown_files':len(paths),'indexed_excluding_self':len(inventory),'files':inventory})
# Validate local file links in current guides; historic external/local references are preserved.
errors=[]; checked=0
active=[repo/p for p in current]+list(dest.glob('*.md'))
for file in active:
    for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',file.read_text(encoding='utf-8')):
        link=(match.group(1) or match.group(2)).split('#',1)[0]
        if not link or re.match(r'[a-zA-Z]+:',link) or link.startswith('/'):continue
        checked+=1
        if not (file.parent/link).resolve().exists():errors.append({'file':str(file.relative_to(repo)),'link':link})
dump(dest/'evidence/document-links.json',{'checked_local_links':checked,'missing':errors,'scope':'current six guides and top-level PUB Markdown including complete index; historical document internals not rewritten'})
assert not errors,errors
print(json.dumps({'markdown_indexed':len(inventory),'links_checked':checked,'additional_messages':len(messages[134:])}))
