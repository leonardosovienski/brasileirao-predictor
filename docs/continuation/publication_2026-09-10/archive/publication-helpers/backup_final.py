"""Create a complete versioned archive and restore-check a final Git bundle."""
import hashlib
import json
import os
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

base=Path('C:/BRASILEIRAO')
root=base/'work/publication-2026-09-10'
repo=base/'brasileirao-predictor'
clone=root/'remote-clone'
bundle=base/'BACKUPS/brasileirao-predictor-PUB-20260910.bundle'
archive=base/'ENTREGAS/BRASILEIRAO_PUB_20260910_entrega.zip'
restored=root/'restored-bundle-final.git'
for target in (bundle,archive,restored):
    assert target.resolve().is_relative_to(base.resolve()) and not target.exists(),str(target)
def git(path,*args):
    return subprocess.check_output(['git','-C',str(path),*args],stderr=subprocess.PIPE).decode().strip()
head=git(repo,'rev-parse','HEAD')
assert head==git(repo,'rev-parse','origin/main')==git(clone,'rev-parse','HEAD')
assert not git(repo,'status','--porcelain') and not git(clone,'status','--porcelain')
git(repo,'bundle','create',str(bundle),'--all')
git(repo,'bundle','verify',str(bundle))
subprocess.run(['git','clone','--bare',str(bundle),str(restored)],capture_output=True,check=True)
assert git(restored,'rev-parse','refs/heads/main')==head
git(restored,'fsck','--full')
git(repo,'-c','core.autocrlf=false','-c','core.eol=lf','archive','--format=zip','--prefix=brasileirao-predictor/','--output',str(archive),'HEAD')
listing=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','-z','HEAD'])
entries=[]
for row in listing.split(b'\0'):
    if not row:continue
    metadata,name=row.split(b'\t',1)
    mode,kind,oid=metadata.decode().split()
    assert kind=='blob'
    entries.append((oid,name.decode()))
raw=subprocess.run(['git','-C',str(repo),'cat-file','--batch'],input=('\n'.join(oid for oid,_ in entries)+'\n').encode(),capture_output=True,check=True).stdout
position=0
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for oid,name in entries:
        end=raw.index(b'\n',position)
        actual,kind,size=raw[position:end].decode().split()
        start=end+1
        content=raw[start:start+int(size)]
        position=start+int(size)+1
        assert actual==oid and kind=='blob'
        assert z.read('brasileirao-predictor/'+name)==content,name
del raw
package=json.loads((root/'package-final/receipt.json').read_text())
assert package['completed']
supplement=[]
with zipfile.ZipFile(archive,'a',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    sources=[(bundle,'BACKUPS/'+bundle.name),(base/'LEIA_PRIMEIRO.md','LEIA_PRIMEIRO.md')]
    for file in (root/'package-final/dist').iterdir():
        if file.suffix=='.whl' or file.name.endswith('.tar.gz'):
            sources.append((file,'PACOTES/'+file.name))
    sources.extend([(root/'package-final/receipt.json','AUDITORIA/package-receipt.json'),(root/'remote-final.json','AUDITORIA/remote-final.json')])
    for filename in ('PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md','MANDATO_RECEBIDO_2026-09-09.txt','PROXIMO_PROMPT_APOS_PUBLICACAO_2026-09-10.md'):
        sources.append((base/'INSTRUCOES'/filename,'INSTRUCOES/'+filename))
    for source,name in sources:
        content=source.read_bytes()
        z.writestr(name,content)
        supplement.append({'entry':name,'source':str(source),'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for item in supplement:
        raw=z.read(item['entry'])
        assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    member_count=len(z.namelist())
receipt={'at':datetime.now(UTC).isoformat(),'publication_complete':True,'head':head,'tree':git(repo,'rev-parse','HEAD^{tree}'),'remote':'https://github.com/leonardosovienski/brasileirao-predictor.git','branch':'main','worktree_clean':True,'independent_clone':str(clone),'remote_pull_receipt':str(root/'remote-final.json'),'versioned_blob_bytes_verified':len(entries),'archive_members':member_count,'zip_crc_verified':True,'bundle_restored':str(restored),'bundle_fsck_passed':True,'runtime_tested_head':'cc38b57bd3ba6f8c2cbdce6353eaf085d4ece14f','linux_ci':'https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34552247397','global_ci_executed':False,'financial_permission':False,'package_source_head':package['head'],'package_scope':'wheel and sdist from first published payload; final Git source archive and bundle include subsequent documentation/verification receipts','artifacts':{str(p):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (bundle,archive)},'supplement':supplement,'local_data_scope':'private/provider raw and preserved operational data remain in C:/BRASILEIRAO; not redistributed into public Git or this code archive','chat_continuity':'visible history, mandates, decisions, issue register and next prompt are versioned; preserve local folder and DC owner task'}
output=base/'AUDITORIA/PUBLICACAO_2026-09-10.json'
output.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
(root/'final-receipt.json').write_bytes(output.read_bytes())
print(json.dumps({'head':head,'blobs':len(entries),'zip_members':member_count,'artifacts':receipt['artifacts'],'receipt':str(output)}))
