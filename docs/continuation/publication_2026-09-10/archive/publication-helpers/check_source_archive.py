"""Check every Git blob against the archive with explicit LF export policy."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
root=Path('C:/BRASILEIRAO/work/publication-2026-09-10')
archive=root/'archive-full-eol.zip'
assert not archive.exists()
subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','-c','core.eol=lf','archive','--format=zip','--prefix=brasileirao-predictor/','--output',str(archive),'HEAD'],check=True)
listing=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','-z','HEAD'])
entries=[]
for row in listing.split(b'\0'):
    if row:
        meta,name=row.split(b'\t',1)
        entries.append((meta.decode().split()[2],name.decode()))
raw=subprocess.run(['git','-C',str(repo),'cat-file','--batch'],input=('\n'.join(oid for oid,_ in entries)+'\n').encode(),capture_output=True,check=True).stdout
position=0
mismatches=[]
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for oid,name in entries:
        end=raw.index(b'\n',position)
        actual,kind,size=raw[position:end].decode().split()
        start=end+1
        content=raw[start:start+int(size)]
        position=start+int(size)+1
        assert actual==oid and kind=='blob'
        if z.read('brasileirao-predictor/'+name)!=content:mismatches.append(name)
receipt={'head':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip(),'blob_count':len(entries),'mismatches':mismatches,'crc_valid':True,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'fix':'core.autocrlf=false AND core.eol=lf, only for this export; archive/evidence -text attributes preserved'}
(root/'archive-full-eol.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
assert not mismatches
