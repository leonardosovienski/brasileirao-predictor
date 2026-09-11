from pathlib import Path
import json,hashlib,re,shutil,subprocess
root=Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09');repo=Path('C:/BRASILEIRAO/brasileirao-predictor');ri=repo/'docs/continuation/integral_review_2026-09-09'
for src,dst in [('package-smoke-final/receipt.json','evidence/package-smoke-final.json'),('package-build-final.log','evidence/logs/package-build-final.log'),('package-smoke-final.log','evidence/logs/package-smoke-final.log'),('package_smoke_final.py','reproducao/package_smoke_final.py')]:
 text=(root/src).read_text(encoding='utf-8-sig')
 (ri/dst).write_text(text,encoding='utf-8',newline='\n')
m=ri/'reproducao/manifest.json';obj=json.loads(m.read_text())
name='package_smoke_final.py'
obj['scripts'][name]=hashlib.sha256((ri/'reproducao'/name).read_bytes()).hexdigest()
obj['canonical_work_scripts'][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
m.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
p=ri/'REPRODUZIR.md';text=p.read_text(encoding='utf-8').replace('Não demonstra previsões com dados reais.', 'Não demonstra previsões com dados reais. Após atualizar os guias, dist-final foi construído e package_smoke_final.py verificou novamente a ajuda e a igualdade byte a byte dos quatro módulos alterados com o checkout; recibo em evidence/package-smoke-final.json.')
p.write_text(text,encoding='utf-8',newline='\n')
files={p.relative_to(ri).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ri.rglob('*')) if p.is_file() and p.name!='MANIFESTO.json'}
(ri/'MANIFESTO.json').write_text(json.dumps({'base_commit':'ac22c56c3318623e07a722f34d44dc6cd877ea37','files':files},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
changed=subprocess.check_output(['git','diff','--name-only'],cwd=repo,text=True).splitlines()
new=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=repo,text=True).splitlines()
paths=changed+new
bad_paths=[p for p in paths if any(x in p.lower() for x in ['evaluate_h14','evaluate_h15','settle_h9','evaluate_gate_a1']) or p.startswith(('data/','research/','reports/')) or Path(p).suffix in {'.db','.sqlite3','.env'}]
assert not bad_paths,bad_paths
patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'AKIA[0-9A-Z]{16}',r'sk-[A-Za-z0-9]{40,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
findings=[]
for rel in paths:
 p=repo/rel
 if p.is_file():
  text=p.read_text(encoding='utf-8-sig')
  if any(re.search(pattern,text) for pattern in patterns):findings.append(rel)
assert not findings,findings
# Check current links without reading historical target content.
failures=[];count=0
for p in list(ri.glob('*.md'))+[repo/p for p in ['README.md','docs/ESTADO_ATUAL.md','docs/continuation/RETOMADA.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md']]:
 for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
  target=link.split('#')[0].strip('<>')
  if target and '://' not in target:
   count+=1
   if not (p.parent/target).resolve().exists():failures.append([str(p),target])
assert not failures,failures
receipt={'changed_paths':paths,'new_or_changed_files':len(paths),'protected_or_operational_paths_changed':bad_paths,'secret_pattern_findings':findings,'secret_scan_scope':'changed public text only; no credentials read','checked_local_links':count,'broken_links':failures,'bytes':sum((repo/p).stat().st_size for p in paths)}
(root/'preintegration-check.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k!='changed_paths'},ensure_ascii=False))
