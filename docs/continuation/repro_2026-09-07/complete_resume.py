import difflib
import hashlib
import json
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

WORK=Path(__file__).resolve().parent
OUT=WORK.parent/'outputs'
ROOT=Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
health=json.loads((WORK/'operational_health_result.json').read_text(encoding='utf-8'))
tasks=json.loads((OUT/'retomada_tarefas.json').read_text(encoding='utf-8-sig'))
integrity=json.loads((OUT/'retomada_integridade.json').read_text(encoding='utf-8'))
admin=json.loads((OUT/'retomada_h14_h15_administrador.json').read_text(encoding='utf-8-sig'))
assert len(tasks['tasks'])==7
assert all(row['enabled'] and row['last_result']==0 for row in tasks['tasks'])
assert all(row['status']=='finished' and row['exit_code']==0 for row in health['jobs'])
admin_at=datetime.fromisoformat(admin['changed_at_utc'].replace('Z','+00:00'))
for job in ['h14-persist','h15-persist']:
    heartbeat=json.loads((ROOT/'data/runtime/passive'/job/'heartbeat.json').read_text(encoding='utf-8'))
    assert datetime.fromisoformat(heartbeat['started_at'])>=admin_at
    assert heartbeat['wrapper_sha256']==integrity['wrapper_sha256']
for name,digest in integrity['protected_sha256'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
prefixes={}
backup=WORK/'retomada_backup'
for old in (backup/'data').rglob('*.jsonl'):
    relative=old.relative_to(backup)
    prefixes[relative.as_posix()]=(ROOT/relative).read_bytes().startswith(old.read_bytes())
assert all(prefixes.values())
integrity.update(checked_at=datetime.now(UTC).isoformat(),h14_h15_enablement='ENABLED_FIRST_RUN_VERIFIED',
                 original_ledger_prefixes_preserved=prefixes)
(OUT/'retomada_integridade.json').write_text(json.dumps(integrity,indent=2)+'\n',encoding='utf-8')
(OUT/'retomada_saude.json').write_text(json.dumps(health,indent=2)+'\n',encoding='utf-8')
checkpoint='''> ## CHECKPOINT — RETOMADA PASSIVA CONCLUIDA (2026-09-07, 18:34 UTC)
>
> O operador executou o script administrativo em 18:33 UTC. **Supersede o
> bloqueio ACL e o estado de retomada parcial do checkpoint abaixo.** H14/H15
> estao habilitadas, triggers de 15min preservados, e ambas concluiram a
> primeira execucao em 18:33:32 UTC com heartbeat finished/exit_code=0 e
> LastTaskResult=0. As sete tarefas do escopo estao habilitadas; todas tiveram
> execucao concluida com codigo zero, inclusive insumos/cache/A1.
>
> Verificados 14 hashes de fontes/configuracoes protegidas e os prefixos dos
> cinco JSONL do backup. Nenhuma incoerencia; nenhuma avaliacao cientifica,
> leitura de resultado parcial para pesquisa ou alteracao de protocolo.
> O codigo zero comprova termino do processo, nao cobertura ou edge.
>
> Horizonte (b) em vigor: H14/H15 em coleta passiva; pesquisa ativa voltada a
> B/C/D, sem abrir labels protegidos. A1 segue REHEARSAL_ONLY no modo gratuito.
> Os demais grupos permanecem desativados. A operacao depende da maquina
> ligada/sessao Windows ativa. Recibo e evidencias atualizados em
> Documents/Codex/2026-09-07/le/outputs/RETOMADA_PASSIVA.md.

'''
for repo in [ROOT,WORK/'brasileirao-predictor']:
    path=repo/'HANDOFF.md'
    original=path.read_bytes()
    nl=b'\r\n' if b'\r\n' in original[:200] else b'\n'
    first,rest=original.split(nl,1)
    path.write_bytes(first+nl+nl+checkpoint.replace('\n',nl.decode()).encode()+rest.lstrip(b'\r\n'))
receipt='''# Retomada passiva concluída — opção (b)

**H14/H15 foram habilitadas pelo operador e ambas concluíram a primeira
execução sem erro, às 15:33:32 BRT de 07/09/2026.** Heartbeats `finished`,
`exit_code=0`; Agendador com `LastTaskResult=0`, estado `Ready` e habilitação
ativa. A cadência de 15 minutos foi preservada.

As sete tarefas do escopo estão habilitadas e tiveram execução concluída com
código zero: H14, H15, atualização dos jogos/espelho/cache, atualização
independente do modelo, A1 descoberta, A1 coleta e A1 métricas operacionais.

A opção (b) está em vigor: coleta prospectiva passiva, pesquisa ativa
direcionada a preço/execução/estrutura. A1 continua gratuito, econômico e
`REHEARSAL_ONLY`; não houve avaliação intermediária, confirmação de edge,
alteração de protocolo, aposta ou gasto. Os demais grupos seguem desativados.

Preservação confirmada: 14 arquivos principais protegidos com hashes intactos
e prefixos dos cinco JSONL originais do backup preservados. A verificação
comparou bytes, sem exibir conteúdo nem calcular métricas científicas.

Validação de código da retomada: 66 testes passaram no ambiente operacional;
Ruff e sintaxe do script PowerShell validados. Dependências/modelos mantidos
em `7b5f833`, core 3.1.0 e ops 4.0.0; launcher silencioso e caminho do refresh
corrigido. Houve um warning de cache do pytest, sem falha nos testes.

Não é necessário executar novamente o script de administrador. O bloqueio
anterior fica apenas como histórico. O código zero comprova término dos jobs,
não cobertura, quantidade de jogos elegíveis ou vantagem econômica. As tarefas
dependem desta máquina ligada e da sessão Windows do usuário.

Evidências atualizadas: [tarefas](retomada_tarefas.json),
[heartbeats](retomada_saude.json), [integridade](retomada_integridade.json),
[recibo administrativo](retomada_h14_h15_administrador.json) e
[testes](testes_retomada.txt). O HANDOFF operacional recebeu checkpoint de
conclusão que supersede a retomada parcial e o bloqueio de permissão.
'''
(OUT/'RETOMADA_PASSIVA.md').write_text(receipt,encoding='utf-8')
files=['HANDOFF.md','jobs.market-research.example.json','brasileirao_scripts/run_passive_task.py','tests/test_run_passive_task.py']
patch=''
for name in files:
    original=subprocess.run(['git','show','HEAD:'+name],cwd=ROOT,capture_output=True)
    before=original.stdout.decode('utf-8').splitlines(keepends=True) if original.returncode==0 else []
    after=(ROOT/name).read_text(encoding='utf-8').splitlines(keepends=True)
    patch+=f'diff --git a/{name} b/{name}\n'
    if not before:patch+='new file mode 100644\n'
    patch+=''.join(difflib.unified_diff(before,after,fromfile='a/'+name if before else '/dev/null',tofile='b/'+name))
(OUT/'retomada_operacional.patch').write_text(patch,encoding='utf-8',newline='\n')
deliveries=['RETOMADA_PASSIVA.md','RETOMAR_H14_H15.ps1','retomada_h14_h15_administrador.json','retomada_integridade.json','retomada_tarefas.json','retomada_saude.json','testes_retomada.txt','retomada_operacional.patch']
payloads={name:(OUT/name).read_bytes() for name in deliveries}
payloads.update({'arquivos/'+name:(ROOT/name).read_bytes() for name in files})
manifest={'base_commit':'7b5f8339730134e1df18e28c026752f1d913f183','horizon':'B_CONFIRMED',
          'h14_h15':'ENABLED_FIRST_RUN_VERIFIED','files':{name:hashlib.sha256(data).hexdigest() for name,data in payloads.items()}}
payloads['manifesto_retomada.json']=(json.dumps(manifest,indent=2)+'\n').encode()
with zipfile.ZipFile(OUT/'retomada_passiva.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name,data in payloads.items():archive.writestr(name,data)
with zipfile.ZipFile(OUT/'retomada_passiva.zip') as archive:
    assert archive.testzip() is None
    for name,digest in manifest['files'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==digest
print(json.dumps({'tasks_enabled':7,'first_runs_exit_zero':7,'protected_files_verified':14,'jsonl_prefixes_verified':len(prefixes),'delivery_updated':True}))
