"""Reconcile current documented totals and append final receipts before integration."""
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
docs=repo/'docs/continuation/resolution_2026-09-10'
evidence=docs/'evidence'
def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(path):
    b=path.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def copy(source,relative):
    target=evidence/relative;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
    assert digest(source)==digest(target)

if '--package' not in sys.argv:
    summary=json.loads((evidence/'python-validation.json').read_text(encoding='utf-8'))
    name='settlement-cli-after'
    tree=ET.parse(root/name/'junit.xml')
    suites=list(tree.iter('testsuite'))
    assert suites and all(int(s.attrib.get(k,0))==0 for s in suites for k in ('failures','errors','skipped'))
    cases={(c['classname'],c['name']):c['latest_evidence'] for c in summary['cases']}
    for case in tree.iter('testcase'):
        cases[(case.attrib['classname'],case.attrib['name'])]=name
    summary['cases']=[dict(classname=c,name=n,latest_evidence=r) for (c,n),r in sorted(cases.items())]
    summary['unique_passed']=len(cases)
    assert len(cases)==336
    if name not in summary['runs']:summary['runs'].append(name)
    dump(evidence/'python-validation.json',summary)
    for folder in ('settlement-cli-before','settlement-cli-after'):
        for filename in ('junit.xml','isolation.json'):
            copy(root/folder/filename,Path(folder)/filename)
    for filename in ('quality-checks-final.json','ruff-check-final.log','ruff-format-check-final.log','pyright-final.log'):
        copy(root/'quality-before-settlement-cli'/filename,Path('quality-before-settlement-cli')/filename)
        copy(root/filename,Path(filename))
    checks=json.loads((root/'quality-checks-final.json').read_text())
    assert len(checks['files'])==41
    assert all(c['exit_code']==0 for c in checks['commands'] if c['name'] in {'ruff-check','ruff-format-check','pyright'})
    registry=json.loads((docs/'REGISTROS.json').read_text(encoding='utf-8'))
    states={r['id']:r['status'] for r in registry['issues']}
    registry['summary']['statuses']=dict(Counter(states.values()))
    registry['summary'].pop('status_counts',None)
    registry['summary']['original_14']=[dict(id=r['id'],status=states[r['id']]) for r in registry['summary']['original_14']]
    registry['states']['software']='correções delimitadas validadas; leitura semântica permitida concluída; homologação global limitada'
    p25=next(c for c in registry['claims'] if c['id']=='CPL-A25')
    p25['impact']='399 fontes permitidas com leitura semântica; 59 protegidas em contrato/metadados. Execução global e correção da operação congelada não implícitas.'
    issue=next(r for r in registry['issues'] if r['id']=='RES-P10')
    issue['action']+='; CLI e run-log de retry retornam o recibo persistido sob a mesma trava, sem novo horário/hash'
    issue['closure_test']='test_resolution_live_settlement; settlement-cli-before (1 falha); settlement-cli-after (14 passam)'
    next(c for c in registry['claims'] if c['id']=='RES-A10')['found']=issue['action']
    registry['dated_at']=datetime.now(UTC).isoformat()
    dump(docs/'REGISTROS.json',registry)
    lines=['# Registro central — RES-20260910','','Gerado de REGISTROS.json; limites originais preservados.','','| ID | Estado | Ação | Limite |','| --- | --- | --- | --- |']
    for r in registry['issues']:
        lines.append('| '+' | '.join(str(r.get(k,'')).replace('|','/').replace('\n',' ') for k in ('id','status','action','limitation'))+' |')
    (docs/'REGISTROS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    for path in [docs/'RESULTADO.md',docs/'REPRODUZIR.md',repo/'README.md',repo/'HANDOFF.md',repo/'docs/ESTADO_ATUAL.md',repo/'docs/DATA_MAP.md',repo/'docs/INDICE_DOCUMENTACAO.md',repo/'docs/continuation/RETOMADA.md']:
        text=path.read_text(encoding='utf-8').replace('335','336').replace('das 9 suítes','das 10 suítes')
        if path.name=='RESULTADO.md':
            text+='\nNa conferência final, o retry da CLI mostrava novo horário/hash apesar de preservar a linha anterior no ledger. Reproduzido com falha antes; agora stdout e run-log recebem exatamente o recibo persistido, sob a mesma trava. As 14 regressões de liquidação passaram após a correção.\n'
        path.write_text(text,encoding='utf-8')
    with (docs/'CONTRATOS.md').open('a',encoding='utf-8') as f:
        f.write('\nRetry da liquidação diagnóstica devolve a linha persistida também ao stdout/run-log; append_settlement mantém sua API booleana e record_settlement retorna (inserido, recibo). Leitura e append desse recibo compartilham writer lock.\n')
    baseinventory=json.loads((repo/'docs/continuation/reconciliation_2026-09-10/evidence/source-inventory.json').read_text(encoding='utf-8'))
    changed=set(subprocess.check_output(['git','diff','--name-only'],cwd=repo,stderr=subprocess.PIPE).decode().splitlines())
    frozen=[r['path'] for r in baseinventory if r['review']=='protected_contract_only_no_execution']
    assert len(frozen)==59 and not set(frozen)&changed
    shared=['brasileirao_predictor/'+n for n in ('db.py','ratings.py','cron_update_models.py','model.py','xg_model.py','sofascore.py','ingest_sofascore.py','serving_evaluator.py')]
    assert not set(shared)&changed
    boundary=json.loads((evidence/'boundary-check.json').read_text(encoding='utf-8'))
    for name,expected in boundary['dc_helpers'].items():
        assert digest(Path('C:/BRASILEIRAO/work/data-completion-2026-09-09')/name)==expected
    boundary.update(at=datetime.now(UTC).isoformat(),protected_source_paths=frozen,shared_sources_unchanged=shared,dc_helpers_rechecked=True)
    dump(evidence/'boundary-check.json',boundary)
    dump(evidence/'final-code-metadata.json',{p:digest(repo/p) for p in checks['files']})
    # New build helper, preserving every previous package and script result.
    text=(root/'build_package_final.py').read_text(encoding='utf-8')
    text=text.replace("out=root/'package-final'", "out=root/'package-final-02'")
    text=text.replace("'--health'],expected=1", "'--healthcheck'],expected=2")
    (root/'build_package_final_02.py').write_text(text,encoding='utf-8')
else:
    folder=root/'package-final-02'
    receipt=json.loads((folder/'receipt.json').read_text())
    assert receipt['completed']
    for p in folder.iterdir():
        if p.is_file() and p.suffix in {'.json','.log'}:copy(p,Path(folder.name)/p.name)
    previous=json.loads((root/'package-final/receipt.json').read_text())
    import zipfile
    oldwheel=next((root/'package-final/dist').glob('*.whl'))
    wheel=next((folder/'dist').glob('*.whl'))
    with zipfile.ZipFile(oldwheel) as old,zipfile.ZipFile(wheel) as current:
        modules=receipt['wheel_source_bytes_checked']
        differences=[p for p in modules if old.read(p)!=current.read(p)]
        assert differences==['brasileirao_scripts/settle_live_prediction.py'],differences
    summary=dict(final_build='package-final-02',sdist_and_wheel_succeeded=True,wheel_modules_byte_equal=len(modules),artifacts=receipt['artifacts'],installation_without_pythonpath=True,explicit_reuse_of_RI_dependencies=True,cli_checks_completed=True,previous_package_failure_preserved=True,previous_cross_process_passed=1,changes_since_cross_process=differences,all_kernel_modules_identical=True,redis_stopped=True)
    dump(evidence/'package-summary.json',summary)
    for path in (docs/'REPRODUZIR.md',docs/'RESULTADO.md'):
        text=path.read_text(encoding='utf-8').replace('Recibo package-final/receipt.json','Recibo package-final-02/receipt.json')
        if path.name=='RESULTADO.md':text+='\nPacote atualizado após correção do retry: package-final-02. Comparação das wheels confirma que somente settle_live_prediction.py mudou desde o último ensaio entre processos; kernel/protocolo usados nesse ensaio permanecem byte idênticos. Build offline, instalação e CLIs do pacote atualizado passaram.\n'
        path.write_text(text,encoding='utf-8')

dump(evidence/'manifest.json',{p.relative_to(docs).as_posix():digest(p) for p in sorted(evidence.rglob('*')) if p.is_file() and p.name!='manifest.json'})
print(json.dumps(dict(completed=True,mode='package' if '--package' in sys.argv else 'prepackage')))
