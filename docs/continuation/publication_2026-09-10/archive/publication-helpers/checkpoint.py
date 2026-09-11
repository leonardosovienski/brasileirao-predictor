"""Capture this exact task's visible conversation and publication checkpoint."""
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
source=Path('C:/Users/leona/.codex/sessions/2026/09/09/rollout-2026-09-09T21-05-07-01a088a1-e7c6-7e93-9ae6-dacd3b43b2a5.jsonl')
raw=source.read_bytes()
messages=[]
for number,line in enumerate(raw.splitlines(),1):
    row=json.loads(line);p=row.get('payload',{})
    if row.get('type')!='response_item' or p.get('type')!='message':continue
    if p.get('role') not in {'user','assistant'} or p.get('channel') in {'analysis','summary'}:continue
    text='\n'.join(item['text'] for item in p.get('content',[]) if item.get('type') in {'input_text','output_text','text'} and 'text' in item)
    if not text or text.startswith(('<recommended_plugins>','<environment_context>')):continue
    text=re.sub(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{30,}|AKIA[0-9A-Z]{16}','[REDACTED_TOKEN]',text)
    messages.append(dict(source_line=number,timestamp=row.get('timestamp'),role=p['role'],phase=p.get('phase'),text=text))
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
dump(root/'chat-visible.json',messages)
text='\n\n'.join(f'[{i+1:03}] {m["role"]} / {m["phase"]}\n{m["text"]}' for i,m in enumerate(messages))
(root/'chat-visible.txt').write_text(text,encoding='utf-8')
dump(root/'chat-receipt.json',dict(thread_id='01a088a1-e7c6-7e93-9ae6-dacd3b43b2a5',source_snapshot_bytes=len(raw),source_snapshot_sha256=hashlib.sha256(raw).hexdigest(),messages=len(messages),characters=len(text),visible_text_sha256=hashlib.sha256(text.encode()).hexdigest(),excluded='tools, reasoning, system/developer and UI environment blocks',snapshot_at=datetime.now(UTC).isoformat(),app_limitation='read_thread returned 10 turns, 7 with no items; exact local task record supplied visible messages'))
def git(*args):return subprocess.check_output(['git',*args],cwd=repo,stderr=subprocess.PIPE).decode().strip()
dump(root/'checkpoint.json',dict(at=datetime.now(UTC).isoformat(),base=git('rev-parse','HEAD'),branch=git('branch','--show-current'),initial_worktree_clean=not git('status','--porcelain=v1'),remote='https://github.com/leonardosovienski/brasileirao-predictor.git',remote_visibility='public',remote_main='ac22c56c3318623e07a722f34d44dc6cd877ea37',authorized='review, correct, validate, archive under C:/BRASILEIRAO, commit/push and fresh remote clone/pull verification',protected_operation='no change or reads of protected results',financial_execution=False,plan=['recover and read visible chat; reconcile decisions against artifacts','inspect CI effects before any push; isolate protected data/evaluators','verify source/data/documentation inventories and recovered dependencies','test corrections and publish authorized text/code/public evidence','fetch/clone/pull and verify hashes, indexes, local backup and Explorer organization'],no_chat_deletion_performed=True))
print(json.dumps(dict(messages=len(messages),characters=len(text),checkpoint=str(root/'checkpoint.json'))))
