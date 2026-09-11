"""Repair the successor's text only; preserve frozen RI bytes and meanings."""

import hashlib
import json
from pathlib import Path

repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
source = repo / 'docs/continuation/integral_review_2026-09-09/REGISTROS.json'
out = repo / 'docs/continuation/implementation_2026-09-10'
out.mkdir(exist_ok=True)
raw = source.read_bytes()
changes = []


def repair(value, path='$'):
    if isinstance(value, dict):
        return {k:repair(v,path+'.'+k) for k,v in value.items()}
    if isinstance(value, list):
        return [repair(v,f'{path}[{i}]') for i,v in enumerate(value)]
    if not isinstance(value,str) or not any(c in value for c in ('Ã','Â','â€','â†','âˆ')):
        return value
    try:
        fixed = value.encode('cp1252').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        raise ValueError('mixed_encoding_requires_manual_review:'+path)
    assert fixed.encode('utf-8').decode('cp1252') == value
    changes.append({'path':path, 'before':value, 'after':fixed})
    return fixed


fixed = repair(json.loads(raw.decode('utf-8')))
target = out / 'REGISTROS_RI_UTF8.json'
target.write_text(json.dumps(fixed, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
receipt = {'kind':'text_encoding_erratum_only', 'source_path':str(source), 'source_sha256':hashlib.sha256(raw).hexdigest(), 'successor_sha256':hashlib.sha256(target.read_bytes()).hexdigest(), 'fields_repaired':len(changes), 'changes':changes}
(out/'ERRATA_UTF8.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert source.read_bytes() == raw
print(json.dumps({'fields_repaired':len(changes),'frozen_source_unchanged':True}))
