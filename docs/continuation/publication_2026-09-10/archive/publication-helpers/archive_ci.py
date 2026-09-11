"""Verify artifact digests and retain durable CI logs and selected evidence."""
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from pathlib import Path

base=Path('C:/BRASILEIRAO')
root=base/'work/publication-2026-09-10'/f'ci-{int(sys.argv[1])}'
dest=base/'brasileirao-predictor/docs/continuation/publication_2026-09-10/evidence'/root.name
dest.mkdir(exist_ok=False)
run=json.loads((root/'run.json').read_text())
jobs=json.loads((root/'jobs.json').read_text())
artifacts=json.loads((root/'artifacts.json').read_text())
assert run['status']=='completed' and run['conclusion']=='success'
assert len(jobs['jobs'])==4 and all(j['conclusion']=='success' for j in jobs['jobs'])
for name in ('run.json','jobs.json','artifacts.json'):
    shutil.copyfile(root/name,dest/name)
shutil.copytree(root/'jobs',dest/'jobs')
summary={'run_id':run['id'],'head':run['head_sha'],'url':run['html_url'],'conclusion':run['conclusion'],'at':datetime.now(UTC).isoformat(),'artifacts':[],'python':{},'dotnet':{},'global_ci_executed':False,'financial_permission':False}
for item in artifacts['artifacts']:
    source=root/'artifacts'/f'{item["id"]}.zip'
    raw=source.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    assert item['digest']=='sha256:'+digest and len(raw)==item['size_in_bytes']
    selected=[]
    with zipfile.ZipFile(source) as z:
        assert z.testzip() is None
        for name in z.namelist():
            path=Path(name)
            if path.name in {'junit.xml','isolation.json','coverage.cobertura.xml','compose-validation.log'} and 'tmp/' not in name and len(path.parts)<8:
                output=dest/'extracted'/str(item['id'])/path
                assert not path.is_absolute() and '..' not in path.parts
                output.parent.mkdir(parents=True,exist_ok=True)
                content=z.read(name)
                output.write_bytes(content)
                selected.append({'name':name,'sha256':hashlib.sha256(content).hexdigest()})
                if path.name=='junit.xml':
                    xml=ET.fromstring(content)
                    suites=list(xml.iter('testsuite'))
                    counts={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
                    assert counts=={'tests':345,'failures':0,'errors':0,'skipped':0}
                    summary['python'][item['name']]=counts
                if path.name=='coverage.cobertura.xml':
                    xml=ET.fromstring(content)
                    rates={k:float(xml.get(k)) for k in ('line-rate','branch-rate')}
                    assert min(rates.values())>=.8
                    summary['dotnet']['coverage']=rates
    summary['artifacts'].append({'id':item['id'],'name':item['name'],'bytes':len(raw),'sha256':digest,'local_zip':str(source),'crc_verified':True,'archived':selected})
assert len(summary['python'])==2 and summary['dotnet'].get('coverage')
dotnet_logs=[(root/'jobs'/f'{j["id"]}.log').read_text(encoding='utf-8') for j in jobs['jobs'] if '.NET 10' in j['name']]
assert len(dotnet_logs)==1 and 'Passed:   160' in dotnet_logs[0] and 'Skipped:     0' in dotnet_logs[0]
summary['dotnet']['passed']=160
summary['dotnet']['skipped']=0
(dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
(root/'receipt.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['run_id','head','conclusion','python','dotnet']}))
