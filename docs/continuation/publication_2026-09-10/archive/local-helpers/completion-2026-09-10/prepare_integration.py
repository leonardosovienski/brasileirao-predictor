import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
docs=repo/'docs/continuation/completion_2026-09-10'; ev=docs/'evidence'
base='456b9025cfa3a596e754088ec3001fbeb5fcc7de'
def git(*args):return subprocess.check_output(['git',*args],cwd=repo).decode('utf-8').strip()
assert git('rev-parse','HEAD')==base and git('branch','--show-current')=='main'
quality=json.loads((root/'quality-checks-final.json').read_text())
assert all(c['exit_code']==0 for c in quality['commands'])
package=json.loads((root/'package-receipt-final.json').read_text())
assert len(package['commands'])==7 and all(c['exit_code']==c['expected'] for c in package['commands'])
assert any(str(root.parent.parent) in arg and 'revisao-integral' in arg for arg in package['commands'][1]['argv'])
passed=set()
for name in ['integrated-python-03','storage-final']:
    tree=ET.parse(root/name/'junit.xml')
    for case in tree.iter('testcase'):
        assert not list(case.iter('failure')) and not list(case.iter('error')) and not list(case.iter('skipped'))
        passed.add((case.get('classname'),case.get('name')))
assert len(passed)==196
for name in ('package-receipt.json','package-receipt-final.json'):
    shutil.copyfile(root/name,ev/name)
for name in ('odds-empty.log','odds-invalid.log','readiness-False.log','readiness-True.log','installed-path.log','install.log','build.log'):
    dst=ev/'package-smoke-final'/name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(root/'package-smoke-final'/name,dst)
changes=git('diff','HEAD','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()
secrets=[]
for rel in changes:
    path=repo/rel
    if not path.is_file():continue
    assert '.env' not in path.parts
    content=path.read_bytes()
    for pattern in [rb'ghp_[A-Za-z0-9]{30,}',rb'sk-(?:proj-)?[A-Za-z0-9_-]{40,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']:
        if re.search(pattern,content):secrets.append(rel)
assert not secrets,secrets
record=dict(verified_at=datetime.now(UTC).isoformat(),base=base,branch='main',python_unique_passed=196,
            redis_python_passed=27,dotnet_unique_passed_across_runs=119,dotnet_last_full_passed=118,
            dotnet_last_full_failed=1,dotnet_cross_recheck_passed=1,full_stable_dotnet_run=False,
            quality=quality,package=package,obvious_secret_patterns_found=[],
            installation_correction='Initial uv install autodetected another project interpreter. Final install explicitly uses RI Python; all package destinations were inside this work root.',
            full_semantic_review_complete=False,economic_profit_proven=False)
(ev/'validation-summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
note=docs/'NOTAS_DE_VERIFICACAO.md'
note.write_text('''# Notas de verificação e falhas preservadas

O registro validation-summary.json distingue testes únicos de repetições.196 casos Python únicos aprovados no conjunto integrado/storage;27 Redis;119.NET entre execuções. A execução.NET runtime-after-02 teve uma falha de bootstrap, seguida de passagem do caso em runtime-cross-diagnostic, com import9s/JIT8s. A causa da primeira ocorrência permanece aberta.

O primeiro lote integrated-python usou dois nomes incorretos de arquivos e não executou testes. integrated-python-02 expôs dois subprocessos bloqueados pelo runner e um teste que esperava texto bruto da API. A CLI de prontidão foi testada em processo no teste unitário e novamente em subprocesso no pacote isolado. O erro da API foi sanitizado e a expectativa atualizada, sem reduzir a condição de falha. integrated-python-03 passou192.

Ruff corrigiu imports/formato; Pyright identificou duas anotações numéricas que foram corrigidas sem alterar resultados. As primeiras falhas e logs continuam na pasta de trabalho; o resumo final exige zero erro dos checks finais.

Na primeira instalação da wheel, uv autodetectou um Python de C:/Cripto, embora o destino de instalação e caches estivessem em C:/BRASILEIRAO. A descoberta foi registrada; a instalação final fixa --python no ambiente RI e limita PATH. Os testes de CLI em ambas as etapas usaram o Python RI explicitamente. Nenhum arquivo ou processo do outro projeto foi alterado por uma ação direcionada desta tarefa. A descoberta automática inicial não é apresentada como isolamento perfeito.

O sdist/wheel foram construídos antes desta nota de auditoria final; contêm o código testado e README vigente. Nota, manifestos e recibos de integração são entregues separadamente e não são falsamente atribuídos ao conteúdo do pacote.
''',encoding='utf-8')
files={}
for path in sorted(docs.rglob('*')):
    if path.is_file() and path.name!='manifest.json':
        raw=path.read_bytes();files[path.relative_to(docs).as_posix()]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
(ev/'manifest.json').write_text(json.dumps(dict(round='CPL-20260910',base=base,files=files),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
subprocess.run(['git','diff','--check'],cwd=repo,check=True)
(root/'precommit.diff').write_bytes(subprocess.check_output(['git','diff','HEAD','--binary'],cwd=repo))
all_changes=git('diff','HEAD','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()
assert all(p.startswith(('brasileirao_predictor/','brasileirao_scripts/','tests/','dotnet/','tools/runtime_lab/','docs/continuation/completion_2026-09-10/')) or p in {'HANDOFF.md','README.md','compose.yaml','docs/DATA_MAP.md','docs/ESTADO_ATUAL.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md'} for p in all_changes)
(root/'staged-paths.json').write_text(json.dumps(sorted(set(all_changes)),indent=2),encoding='utf-8')
subprocess.run(['git','add','--',*sorted(set(all_changes))],cwd=repo,check=True)
subprocess.run(['git','diff','--cached','--check'],cwd=repo,check=True)
print(json.dumps(dict(staged_files=len(set(all_changes)),evidence_files=len(files),python_passed=len(passed),ready_for_checkpoint_commit=True)))
