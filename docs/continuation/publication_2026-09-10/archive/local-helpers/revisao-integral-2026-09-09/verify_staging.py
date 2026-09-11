from pathlib import Path
import hashlib,json,subprocess,re
root=Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09');repo=Path('C:/BRASILEIRAO/brasileirao-predictor');ri=repo/'docs/continuation/integral_review_2026-09-09'
manifest=json.loads((ri/'MANIFESTO.json').read_text())
manifest['files']['.gitattributes']=hashlib.sha256((ri/'.gitattributes').read_bytes()).hexdigest()
(ri/'MANIFESTO.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
subprocess.run(['git','add','--',str(ri/'.gitattributes'),str(ri/'MANIFESTO.json')],cwd=repo,check=True)
staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=repo,text=True).splitlines()
patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'AKIA[0-9A-Z]{16}',r'sk-[A-Za-z0-9]{40,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
for name in staged:
 blob=subprocess.check_output(['git','show',':'+name],cwd=repo)
 assert not any(re.search(p,blob.decode('utf-8-sig')) for p in patterns),name
 if name.startswith('docs/continuation/integral_review_2026-09-09/'):
  assert blob==(repo/name).read_bytes(),name
assert subprocess.check_output(['git','diff','--name-only'],cwd=repo,text=True).strip()=='','Unstaged changes'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()=='ac22c56c3318623e07a722f34d44dc6cd877ea37'
(root/'staged-verification.json').write_text(json.dumps({'files':len(staged),'secret_pattern_findings':0,'review_blob_bytes_equal_to_working_files':True,'base_unchanged':True,'paths':staged},indent=2),encoding='utf-8')
print(json.dumps({'files':len(staged),'secret_pattern_findings':0,'review_blobs_match':True}))
