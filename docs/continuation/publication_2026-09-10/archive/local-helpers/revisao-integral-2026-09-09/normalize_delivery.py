import hashlib,json,re
from pathlib import Path
root=Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09')
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
ri=repo/'docs/continuation/integral_review_2026-09-09'
paths=list(ri.rglob('*'))+[repo/p for p in ['README.md','HANDOFF.md','docs/DATA_MAP.md','docs/ESTADO_ATUAL.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md','docs/continuation/data_completion_2026-09-09/reproducao/manifest.json']]
for p in paths:
 if p.is_file() and p.suffix in {'.md','.json','.py','.ps1','.log','.Config'}:
  text=p.read_text(encoding='utf-8-sig')
  text=text.replace('ac 22 c 56','ac22c56').replace('e.NETbuild','e .NET build')
  text=re.sub(r'SHA(?=[a-f0-9]{64})','SHA ',text)
  p.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n',encoding='utf-8',newline='\n')
extra=ri/'reproducao/reconcile_final_records.py'
extra.write_bytes((root/'reconcile_final_records.py').read_bytes())
repro=ri/'reproducao'
manifest=json.loads((repro/'manifest.json').read_text())
manifest['scripts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(repro.iterdir()) if p.is_file() and p.name!='manifest.json'}
manifest['canonical_work_scripts']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in manifest['scripts']}
manifest['text_encoding']='versioned copies UTF-8 LF; original run byte hashes retained separately'
(repro/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
Path('C:/BRASILEIRAO/INSTRUCOES/PROXIMO_PROMPT_APOS_REVISAO_2026-09-09.md').write_bytes((ri/'PROXIMO_PROMPT.md').read_bytes())
# Do not render or read any frozen report for the new evidence manifest.
files={str(p.relative_to(ri)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ri.rglob('*')) if p.is_file() and p.name!='MANIFESTO.json'}
(ri/'MANIFESTO.json').write_text(json.dumps({'base_commit':'ac22c56c3318623e07a722f34d44dc6cd877ea37','files':files},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'review_files':len(files),'repro_scripts':len(manifest['scripts'])}))
