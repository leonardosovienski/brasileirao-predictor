import json
import hashlib
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
script=root/'write_docs.py'
text=script.read_text(encoding='utf-8').replace('194','196').replace('192 integrados e2 do inicializador','192 integrados,3 do inicializador e1 adicional de schema legado')
text=text.replace('2 casos do init em compose-init-after','3 casos do init e1 adicional de schema legado em storage-final')
text=text.replace('package-receipt.json','package-receipt-final.json')
text=text.replace('compose-init-before; compose-init-after','compose-init-before; storage-final')
script.write_text(text,encoding='utf-8')
for rel in ['HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md']:
    path=repo/rel
    value=path.read_text(encoding='utf-8')
    head,sep,tail=value.partition('\n---\n')
    path.write_text(head.replace('194 testes','196 testes')+sep+tail,encoding='utf-8')
path=Path('C:/BRASILEIRAO/LEIA_PRIMEIRO.md')
value=path.read_text(encoding='utf-8');head,sep,tail=value.partition('\n---\n')
path.write_text(head.replace('194 testes','196 testes')+sep+tail,encoding='utf-8')
dc=Path('C:/BRASILEIRAO/work/data-completion-2026-09-09')
expected={'followup_capture.py':'31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88','audit_followup.py':'ebce7ddeb384b347be4985b7a3812a1b83c7dfaceafdb3e2a6cb00f7e2d09a24'}
actual={name:hashlib.sha256((dc/name).read_bytes()).hexdigest() for name in expected}
assert actual==expected
receipt={'verified_at':datetime.now(UTC).isoformat(),'helpers':actual,
         'followup_receipt_exists':(dc/'followup/receipt.json').exists(),
         'followup_marker_exists':(dc/'followup/attempt.json').exists(),
         'capture_invoked':False,'decision_at':'2026-09-11T23:00:00Z',
         'note':'Existence checks only. No receipt content or quota endpoint read; hashes do not verify active schedule.'}
(repo/'docs/continuation/completion_2026-09-10/evidence/frozen-followup.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
