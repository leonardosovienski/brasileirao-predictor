"""Check the type/status hardening against frozen pilot data, without network."""
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
out = root/'pilot_hardening_check.json'
if out.exists():
    raise SystemExit('NO_OVERWRITE')
for name in list(os.environ):
    if name.upper() not in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC','PATHEXT'}:
        del os.environ[name]
sys.dont_write_bytecode=True
sys.path.insert(0,str(repo))


def guard(event,args):
    if event.startswith(('socket.','sqlite3.','subprocess.','os.system')):
        raise PermissionError('offline_only')
    if event=='open' and isinstance(args[0],str|bytes|os.PathLike):
        p=Path(os.fsdecode(args[0])).resolve()
        mode,flags=args[1] or '',args[2] or 0
        if (any(c in mode for c in 'wax+') or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT)) and p!=out:
            raise PermissionError('receipt_only')
        if p.is_relative_to(Path('C:/BRASILEIRAO/DADOS_PRESERVADOS')) or p.is_relative_to(repo/'data') or p.name=='.env':
            raise PermissionError('private_or_protected')


sys.addaudithook(guard)
from brasileirao_predictor.research.price_strength.live_capture_admission import audit_capture

pilot=root/'prospective_pilot'
records=json.loads((pilot/'receipt.json').read_text(encoding='utf-8'))['requests']
expected=json.loads((root/'admission-01/pilot_events.json').read_text(encoding='utf-8'))
actual=[]
for r in records:
    if r['endpoint'].endswith('/odds') and r['status']=='SAVED':
        raw=(pilot/r['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==r['sha256']
        audit=audit_capture(json.loads(raw),r,'id1000032566887012')
        audit['file']=r['file']
        actual.append(audit)
assert actual==expected and len(actual)==3
receipt={'completed_at':datetime.now(UTC).isoformat(),'status':'PASS','captures':3,
         'original_pilot_audits_unchanged':True,'new_source_sha256':hashlib.sha256(
             (repo/'brasileirao_predictor/research/price_strength/live_capture_admission.py').read_bytes()).hexdigest(),
         'old_source_preserved':'executed_modules/live_capture_admission.py',
         'old_source_sha256':hashlib.sha256((root/'executed_modules/live_capture_admission.py').read_bytes()).hexdigest()}
out.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
