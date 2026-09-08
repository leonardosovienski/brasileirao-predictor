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
jobs={row['job']:row for row in health['jobs']}
fixture=jobs['fixture-refresh']
fixture_finished=fixture.get('status')=='finished' and fixture.get('exit_code')==0
fixture_text='concluiu com exit_code=0' if fixture_finished else 'esta em execucao; conclusao ainda nao atestada'
time=datetime.now(UTC).isoformat(timespec='seconds')
checkpoint=f'''> ## CHECKPOINT — RETOMADA PASSIVA PARCIAL; ACL H14/H15 (2026-09-07)
>
> Estado em {time}. **Supersede "retomada em preparacao"**
> abaixo somente no estado operacional. Horizonte (b) confirmado pelo operador.
> Cinco tarefas habilitadas: fixture-refresh, model-update e A1
> collect/discover/metrics. A1 discovery/coleta/metricas tiveram exit_code=0
> nas primeiras execucoes; permanecem REHEARSAL_ONLY, sem veredito economico.
> A atualizacao inicial dos insumos {fixture_text}.
>
> H14/H15 continuam Disabled: Windows retornou "Acesso negado" tanto no
> Set-ScheduledTask quanto no Enable-ScheduledTask. Nao foram criadas tarefas
> alternativas para substituir as protegidas. Finalizacao exige executar
> RETOMAR_H14_H15.ps1 como Administrador, preparado nas entregas da sessao
> Documents/Codex/2026-09-07/le/outputs. O script espera insumos atualizados,
> confere hashes, pre-valida as duas tarefas e mantem seus triggers de 15min.
>
> Launcher silencioso instalado: pythonw + CREATE_NO_WINDOW, allowlist de
> sete jobs, sem shell, heartbeat e logs locais data/runtime/passive/<job>/.
> A1 falha antes da API se inicializacao/fingerprint/rotacao/chave falharem.
> Manifesto de fixture-refresh corrigido para brasileirao_scripts/; tarefa
> tem limite de 95min (job 5400s), modelo 35min. Cadencias preservadas. A mudanca
> nao altera metricas, refits cientificos, modelos, thresholds ou coortes.
>
> Verificacao: 66 testes no ambiente operacional Python 3.14.6/core 3.1/ops 4.0;
> Ruff check/format OK. Um warning de cache do pytest; testes passaram.
> Os 14 arquivos protegidos conferem com o backup; os tres prefixes JSONL
> protegidos existentes foram preservados byte a byte. Nenhum upgrade,
> avaliacao de coorte, nova trial, aposta/gasto, commit ou push.
> Pesquisa ativa A PAUSE; B/C/D continuam DISCOVERY de viabilidade sem
> labels protegidos. Uma nova decisao sera necessaria antes de abrir
> fechamento/resultado para pesquisa; escolher (b) nao liberou esses dados.

'''
for repo in [ROOT,WORK/'brasileirao-predictor']:
    path=repo/'HANDOFF.md'
    original=path.read_bytes()
    nl=b'\r\n' if b'\r\n' in original[:200] else b'\n'
    first,rest=original.split(nl,1)
    path.write_bytes(first+nl+nl+checkpoint.replace('\n',nl.decode()).encode()+rest.lstrip(b'\r\n'))
receipt=f'''# Retomada passiva — opção (b), 07/09/2026

A escolha foi registrada. **Cinco tarefas estão habilitadas; H14/H15 continuam
desativadas por bloqueio de permissão do Windows.** O sistema retornou
“Acesso negado” ao alterar e ao habilitar essas duas tarefas.

| Tarefa | Estado observado |
|---|---|
| A1 descoberta semanal | Habilitada; primeira execução exit_code=0 |
| A1 coleta econômica, tarefa de 15min | Habilitada; primeira execução exit_code=0 |
| A1 métricas operacionais diárias | Habilitada; primeira execução exit_code=0 |
| Atualização de fixtures/espelho/cache, 6h | Habilitada; {fixture_text} |
| Atualização independente do cache, 6h | Habilitada; primeira execução exit_code=0 |
| H14/H15, 15min | **Disabled — requer administrador** |

Para concluir, abra PowerShell **como Administrador** e execute:

```powershell
& 'C:\\Users\\Superleo13\\Documents\\Codex\\2026-09-07\\le\\outputs\\RETOMAR_H14_H15.ps1'
```

O script espera a atualização inicial, se ainda estiver rodando (até 95min),
verifica hashes/insumos e configura/habilita somente as duas tarefas existentes.
Ele preserva os gatilhos de 15min e não executa avaliações científicas.
O recibo administrativo será salvo ao lado do script. O pacote inclui seu
arquivo de integridade; mantenha ambos na mesma pasta se mover as entregas.

Correções implantadas no repositório operacional: caminho quebrado do refresh;
launcher silencioso via pythonw e CREATE_NO_WINDOW; heartbeat por job;
guarda A1 antes de qualquer chamada do coletor; limites de execução de 95min
para refresh e 35min para cache. Não houve reinstalação geral das tarefas.
Os outros grupos de tarefas continuam desativados.

Preservação: backup consistente do SQLite, cópias de ledgers/estados e XML das
sete tarefas em `work/retomada_backup` da sessão. Os 14 arquivos principais
protegidos e os prefixos dos três JSONL existentes foram verificados. Código
operacional e dependências mantidos em 7b5f833/core 3.1.0/ops 4.0.0. Esta checagem
não é uma atestação integral de todo o ambiente.

**66 testes passaram no ambiente operacional**; Ruff e sintaxe PowerShell
validados. Houve um warning do cache do pytest, sem falha de teste. Não foi
rodado CI completo. Nenhum resultado científico, preço futuro, ROI ou CLV foi
avaliado. Ingestão e coleta usam os caminhos operacionais existentes; as
saídas detalhadas ficam nos logs locais e não foram exibidas.

Prioridade de pesquisa: outcomes em pausa ativa; B/C/D em descoberta de
viabilidade. A1 segue gratuito/econômico e REHEARSAL_ONLY. A escolha (b) não
autoriza uso de fechamento/resultado protegido, capital ou gasto.

Verificar saúde pelos heartbeats em `data/runtime/passive/<job>/heartbeat.json`.
Exit_code=0 confirma término do processo; não comprova cobertura, edge ou
homologação. A ingestão trata algumas falhas individualmente: a inspeção desta
sessão contou apenas marcadores de erro/etapas, sem expor placares. As tarefas
dependem desta máquina ligada e da sessão Windows do usuário.

Estado observado: {health['checked_at']}. Evidências: `retomada_tarefas.json`,
`retomada_saude.json`, `retomada_integridade.json` e `testes_retomada.txt`.
O patch operacional usa a base 7b5f833 e contém somente a mudança desta retomada;
não aplicar o patch anterior da auditoria à operação sem revisar versões.
'''
(OUT/'RETOMADA_PASSIVA.md').write_text(receipt,encoding='utf-8')
(OUT/'retomada_saude.json').write_text(json.dumps(health,indent=2)+'\n',encoding='utf-8')
# Build an operational patch without touching the operational Git index.
import difflib
files=['HANDOFF.md','jobs.market-research.example.json','brasileirao_scripts/run_passive_task.py','tests/test_run_passive_task.py']
patch=''
for name in files:
    original=subprocess.run(['git','show','HEAD:'+name],cwd=ROOT,capture_output=True)
    before=original.stdout.decode('utf-8').splitlines(keepends=True) if original.returncode==0 else []
    after=(ROOT/name).read_text(encoding='utf-8').splitlines(keepends=True)
    patch+=f'diff --git a/{name} b/{name}\n'
    if not before:
        patch+='new file mode 100644\n'
    patch+=''.join(difflib.unified_diff(before,after,fromfile='a/'+name if before else '/dev/null',tofile='b/'+name))
(OUT/'retomada_operacional.patch').write_text(patch,encoding='utf-8',newline='\n')
payloads={name:(OUT/name).read_bytes() for name in ['RETOMADA_PASSIVA.md','RETOMAR_H14_H15.ps1','retomada_integridade.json','retomada_tarefas.json','retomada_saude.json','testes_retomada.txt','retomada_operacional.patch']}
payloads.update({'arquivos/'+name:(ROOT/name).read_bytes() for name in files})
manifest={'base_commit':'7b5f8339730134e1df18e28c026752f1d913f183','horizon':'B_CONFIRMED',
          'h14_h15':'ADMIN_REQUIRED','files':{name:hashlib.sha256(data).hexdigest() for name,data in payloads.items()}}
payloads['manifesto_retomada.json']=(json.dumps(manifest,indent=2)+'\n').encode()
archive=OUT/'retomada_passiva.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in payloads.items():z.writestr(name,data)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'fixture_finished':fixture_finished}))
