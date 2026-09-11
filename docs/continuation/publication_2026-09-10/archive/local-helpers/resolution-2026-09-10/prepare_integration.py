"""Stage exactly reviewed code/guides and hashed public synthetic evidence."""
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
docs=repo/'docs/continuation/resolution_2026-09-10'
base='3bda4c4b0abd9b94902f77509d7d211ac30e96f7'
def git(*args):
    return subprocess.run(['git',*args],cwd=repo,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
def digest(path):
    b=path.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

assert git('rev-parse','HEAD').decode().strip()==base
assert git('branch','--show-current').decode().strip()=='main'
assert not git('diff','--name-only','--cached')
quality=json.loads((root/'quality-checks-final.json').read_text())
expected=set(quality['files'])
expected.update('dotnet/'+p for p in '''LineupWorker.Tests/FairOddsCorrelationTests.cs LineupWorker.Tests/KernelCrossProcessTests.cs LineupWorker.Tests/WorkerRuntimeFencingTests.cs LineupWorker.Tests/WorkerRuntimeTests.cs LineupWorker.Tests/LatencyOrderingTests.cs LineupWorker.Tests/MarketFeedContractTests.cs LineupWorker.Tests/WorkerInputContractTests.cs LineupWorker/Models/KernelContracts.cs LineupWorker/Models/LatencyRecord.cs LineupWorker/Models/LineupEvent.cs LineupWorker/Models/LineupModelInputs.cs LineupWorker/Services/LatencyAuditService.cs LineupWorker/Services/MarketOddsCache.cs LineupWorker/Services/MarketStateEngine.cs LineupWorker/Services/VorpStateService.cs LineupWorker/Worker.cs'''.split())
expected.update(['.env.example','.github/workflows/ci.yml','compose.yaml','pyproject.toml'])
assert len(expected)==61
guides={'README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md'}
changed=set(git('diff','--name-only').decode().splitlines())
new=set(git('ls-files','--others','--exclude-standard').decode().splitlines())
assert changed<=expected|guides,changed-(expected|guides)
assert all(p in expected or p.startswith('docs/continuation/resolution_2026-09-10/') for p in new)
assert (changed|new)&expected==expected
assert guides<=changed
metadata=json.loads((docs/'evidence/final-code-metadata.json').read_text())
assert all(digest(repo/p)==value for p,value in metadata.items())
inventory=json.loads((docs/'evidence/source-inventory.json').read_text(encoding='utf-8'))
for row in inventory:
    if row['review']=='protected_contract_only_no_execution':
        assert row['path'] not in changed and digest(repo/row['path'])==row['current_source_metadata']
    elif row['path'] in expected:
        row['current_source_metadata']=digest(repo/row['path'])
dump(docs/'evidence/source-inventory.json',inventory)
registry=json.loads((docs/'REGISTROS.json').read_text(encoding='utf-8'))
assert registry['summary']['issues']==len(registry['issues'])==59
assert registry['summary']['statuses']==dict(Counter(r['status'] for r in registry['issues']))=={'validado':52,'bloqueado':7}
byid={r['id']:r for r in registry['issues']}
assert all(byid[r['id']]['status']==r['status'] for r in registry['summary']['original_14'])
assert len(registry['summary']['original_14'])==14
assert registry['mandate_complete'] is False
assert json.loads((docs/'evidence/semantic-remaining.json').read_text())==[]
assert json.loads((docs/'evidence/python-validation.json').read_text())['unique_passed']==336
dump(docs/'evidence/integration-boundary.json',dict(base=base,checked_at=datetime.now(UTC).isoformat(),reviewed_code_paths=sorted(expected),source_review_counts=dict(Counter(r['review'] for r in inventory)),no_protected_source_changes=True,registered_counts_consistent=True,no_financial_execution=True,main_integration_only=True))
manifest={p.relative_to(docs).as_posix():digest(p) for p in sorted((docs/'evidence').rglob('*')) if p.is_file() and p.name!='manifest.json'}
dump(docs/'evidence/manifest.json',manifest)
for relative,value in manifest.items():
    path=docs/relative
    assert path.resolve().is_relative_to(docs) and digest(path)==value
files=sorted(expected|guides|{p.relative_to(repo).as_posix() for p in docs.rglob('*') if p.is_file()})
for name in files:
    assert (repo/name).resolve().is_relative_to(repo)
    assert not name.startswith(('data/','reports/','research/','DADOS_PRESERVADOS/'))
    assert Path(name).name not in {'.env','config.yaml'}
    raw=(repo/name).read_bytes()
    assert not re.search(rb'(?:AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|sk-proj-[A-Za-z0-9_-]{30,})',raw),name
for i in range(0,len(files),40):git('add','-f','--',*files[i:i+40])
assert set(git('diff','--cached','--name-only').decode().splitlines())==set(files)
git('diff','--cached','--check')
evidence_paths=sorted(p.relative_to(repo).as_posix() for p in (docs/'evidence').rglob('*') if p.is_file())
# Persistent cat-file avoids launching hundreds of Git processes.
with subprocess.Popen(['git','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as process:
    for name in evidence_paths:
        process.stdin.write((':'+name+'\n').encode());process.stdin.flush()
        header=process.stdout.readline().decode().split()
        assert len(header)==3 and header[1]=='blob',name
        raw=process.stdout.read(int(header[2]));assert process.stdout.read(1)==b'\n'
        assert raw==(repo/name).read_bytes(),name
    process.stdin.close();assert process.wait(timeout=30)==0
(root/'precommit.diff').write_bytes(git('diff','--cached','--binary'))
dump(root/'staged-paths.json',files)
dump(root/'index-evidence-check.json',dict(files=evidence_paths,byte_equality=True))
print(json.dumps(dict(base=base,staged_files=len(files),code_files=len(expected),evidence_files=len(evidence_paths),ready=True)))
