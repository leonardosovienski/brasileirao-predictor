"""Publish one current state while preserving all dated reports and evidence."""
import collections
import hashlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

base=Path('C:/BRASILEIRAO')
repo=base/'brasileirao-predictor'
work=base/'work/publication-2026-09-10'
dest=repo/'docs/continuation/publication_2026-09-10'
run_id=34552247397
ci=json.loads((dest/f'evidence/ci-{run_id}/summary.json').read_text())
assert ci['conclusion']=='success'
prefix='docs/continuation/publication_2026-09-10'
def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
def dump(path,value): write(path,json.dumps(value,ensure_ascii=False,indent=2))
guides=['README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md']
for name in guides:
    target=dest/'archive/previous-guides'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists(): shutil.copyfile(repo/name,target)
previous=dest/'archive/previous-guides/LEIA_PRIMEIRO.md'
if not previous.exists(): shutil.copyfile(base/'LEIA_PRIMEIRO.md',previous)
reg=json.loads((repo/'docs/continuation/resolution_2026-09-10/REGISTROS.json').read_text())
reg.update(round='PUB-20260910',dated_at=datetime.now(UTC).isoformat(),base='ec493c8ec263ca9c11213cf3378d436b32279c44',previous_registry='docs/continuation/resolution_2026-09-10/REGISTROS.json',supersedes_current_register=True,mandate_complete=False)
for issue in reg['issues']:
    if issue['id']=='RCA-P09':
        issue.update(problem='Compose Linux e CI delimitada agora executados; CI global inclui avaliações protegidas e permanece fora do escopo autorizado.',action='Python 3.13/3.14 instalados com uv.lock, 345 testes por versão, .NET 160/160 e Compose build/health/hotpath/queda Redis/reconexão/desligamento aprovados em runner Linux descartável.',limitation='CI global não executada: test discovery importa avaliadores protegidos e lê registries reais. Ambiente operacional Windows e conexões comerciais não homologados por esse ensaio.',updated_in='PUB-20260910',evidence=f'{prefix}/evidence/ci-{run_id}/summary.json',closure_test='Ensaio Linux fechado no escopo sintético; homologação global exige respeitar as fronteiras específicas do mandato. Status bloqueado não foi removido por renomear a CI.')
for claim in reg['claims']:
    if claim['id']=='RCA-A09':
        claim.update(found='Compose e cadeia Python/Redis/.NET validados em Linux no GitHub, com dados sintéticos e volumes próprios.',conclusion='confirmada no escopo delimitado; homologação global continua não verificada',evidence=f'{prefix}/evidence/ci-{run_id}/summary.json')
reg['summary']['statuses']=dict(collections.Counter(i['status'] for i in reg['issues']))
reg['publication']={'reviewed_visible_messages':134,'archived_helper_files':len(list((dest/'archive/local-helpers').rglob('*.*'))),'ci_run':run_id,'tested_head':ci['head'],'global_ci':False,'remote_main_publication':'verify publication receipt; this registry is not a push receipt','current_work':'C:/BRASILEIRAO/work/publication-2026-09-10'}
dump(dest/'REGISTROS.json',reg)
rows=['# Registro corrente — PUB-20260910','','Deriva de REGISTROS.json. O histórico RES foi preservado. 59 itens: 52 validados e sete bloqueados. A parcela Linux de RCA-P09 foi resolvida; o escopo global protegido permanece aberto.','','| ID | Estado | Problema |','| --- | --- | --- |']
for issue in reg['issues']: rows.append(f'| {issue["id"]} | {issue["status"]} | {issue["problem"].replace("|","/")} |')
write(dest/'REGISTROS.md','\n'.join(rows))
result=f'''# Resultado — PUB-20260910

Releitura integral do histórico visível recuperado e dos dois mandatos concluída. Mantidas as correções RES após confronto com código, testes, registros e limites. Acrescentados runner portátil, configuração Compose isolada, controles de I/O, verificação de tipagem, arquivo do contexto e índices de recuperação. O GitHub e o checkout final devem ser conferidos pelo recibo de publicação; este documento não substitui o recibo do push/pull.

- Python 3.13 e 3.14: **345 testes aprovados por versão**, sem falhas, erros ou skips. São os 336 casos RES mais nove provas do isolamento; não são 690 casos distintos.
- .NET 10: **160 testes aprovados**, zero skips; **86,91% de linhas e 81,90% de ramos**, mantendo os pisos de 80%.
- Compose Linux: build, inicialização, health, hotpath sintético, interrupção/retorno do Redis, novo hotpath e desligamento normal aprovados. Volumes próprios removidos ao final; nenhum serviço operacional utilizado.
- Dependências instaladas a partir dos lockfiles no runner; wheel/sdist gerados. Ruff, formatação e Pyright aprovados para as ferramentas novas.
- [Execução final no GitHub](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/{run_id}), commit `{ci['head']}`. Logs, XML, hashes e resumos preservados em evidence. A execução anterior 34544695904 também foi mantida; houve correção posterior de duas anotações de retorno do guard.

**A CI global não foi executada.** `ci.yml` inclui avaliadores H14/H15/A1 e registries reais; rodá-lo indiscriminadamente contrariaria o mandato. Seus critérios não foram reduzidos. A publicação em main usa `[skip ci]`, e o workflow delimitado tem nome e escopo próprios. Verde nesse workflow não significa autorização financeira, homologação comercial ou sistema integralmente pronto.

O registro corrente conserva **52 itens validados e sete bloqueados**. A falta do ensaio Linux foi resolvida; o restante de RCA-P09 diz respeito ao escopo global. Permanecem requisitos de operação protegida, fonte/entrada comercial autenticada, estado verificável da automação, ofertas/aceite/capacidade/custos e restauração operacional. Lucro líquido futuro executável continua não demonstrado; capital desabilitado.

O arquivo do contexto contém as 134 mensagens visíveis até o checkpoint, os mandatos integrais e {reg['publication']['archived_helper_files']} roteiros/documentos locais de trabalho. Esta etapa adicional está registrada aqui e em PROXIMO_PROMPT.md. Não foram arquivados raciocínio interno, mensagens de sistema ou credenciais. Roteiros históricos são evidência e não autorização para reexecutar comandos sobre caminhos existentes.

[Reavaliação das decisões](REVISAO_DO_CHAT.md), [registro completo](REGISTROS.json), [dados/fontes](DADOS_E_FONTES.md), [reprodução](REPRODUZIR.md), [retomada](PROXIMO_PROMPT.md). Os seis guias principais apontam para este estado; os documentos antigos continuam datados e preservados.

O clone Git recupera conteúdo versionado. Dados privados e raws sem redistribuição estabelecida continuam sob C:/BRASILEIRAO, com seus inventários e backups. Preservar a pasta é necessário; GitHub público não equivale a backup integral de toda a máquina. A conversa não precisa ser a fonte de continuidade depois que o recibo de recuperação estiver aprovado.
'''
write(dest/'RESULTADO.md',result)
write(dest/'REPRODUZIR.md',f'''# Reprodução e conferência da publicação

O ensaio Linux completo está em [Actions](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/{run_id}). O código executado é `{ci['head']}`. `tools/publication_validation/README.md`, scope.json e workflow descrevem os comandos exatos; logs e artefatos têm hashes verificados. O ambiente do runner foi descartável e sua instalação veio dos lockfiles.

No Windows, use um diretório novo sob C:/BRASILEIRAO. `git clone https://github.com/leonardosovienski/brasileirao-predictor.git DIRETORIO_NOVO` e `git -C DIRETORIO_NOVO pull --ff-only origin main` recuperam o código. Não substituir o checkout ou dados existentes. Verifique `git status --short`, HEAD, origin/main e o recibo em C:/BRASILEIRAO/AUDITORIA/PUBLICACAO_2026-09-10.json. A cópia de conferência desta entrega fica em C:/BRASILEIRAO/work/publication-2026-09-10/remote-clone.

Instale a cadeia fixada com `uv sync --locked --all-extras`; não execute coletores ou pytest global. Para a lista sintética revisada, use o Python do ambiente com `-I -B tools/publication_validation/run.py C:/BRASILEIRAO/work/NOVA_SAIDA`. Ela recusa saída dentro do checkout ou que já exista. Runtimes, provedores e instalação da cadeia requerem dependências externas; não vêm embutidos no Git.

O pacote e bundle finais possuem recibo separado na pasta AUDITORIA. A restauração de Git/arquivos não migra bancos, não restaura Redis operacional e não prova disponibilidade de dados nunca recebidos. Recibos CI referem-se ao commit testado; alterações posteriores somente documentais têm relação de árvore verificada na publicação.
''')
write(repo/'README.md',f'''# brasileirao-predictor

Estado **PUB-20260910**: correções de dados temporais, caixa, persistência e runtime validadas em laboratório Windows e Linux. **345 testes Python por versão (3.13/3.14), 160 .NET e Compose Linux aprovados no escopo sintético.** Lucro executável e homologação global ainda não demonstrados; capital desabilitado.

[Resultado e limites]({prefix}/RESULTADO.md) · [registro corrente]({prefix}/REGISTROS.md) · [reprodução]({prefix}/REPRODUZIR.md) · [retomada sem o chat]({prefix}/PROXIMO_PROMPT.md) · [CI delimitada](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/{run_id}).

O histórico visível, os mandatos e os roteiros locais estão arquivados na entrega. [Revisão das decisões]({prefix}/REVISAO_DO_CHAT.md), [dados/fontes]({prefix}/DADOS_E_FONTES.md) e [índice documental](docs/INDICE_DOCUMENTACAO.md). Conteúdo versionado é recuperável por clone/pull; dados privados e fontes com restrição de redistribuição permanecem em C:/BRASILEIRAO.

Registro: 52 itens validados e sete bloqueados; Compose Linux fechado dentro de RCA-P09, CI global ainda não executada por incluir avaliações protegidas. Inventário base: 399 arquivos com leitura semântica e 59 protegidos restritos a contratos/metadados. H14/H15/H9/A1 permanecem preservados. Trabalho local em C:/BRASILEIRAO, solo. Não confundir testes sintéticos com oferta aceita ou autorização financeira.
''')
write(repo/'HANDOFF.md',f'''# Handoff — PUB-20260910

Comece por [resultado]({prefix}/RESULTADO.md), [retomada]({prefix}/PROXIMO_PROMPT.md), [registro]({prefix}/REGISTROS.json) e [revisão do chat]({prefix}/REVISAO_DO_CHAT.md). O contexto visível e os dois mandatos integrais estão arquivados na mesma pasta; não é necessário depender da conversa para saber o que foi feito ou o que continua pendente.

345 testes Python por versão, 160 .NET e Compose Linux passaram no workflow delimitado. CI global não executada; seus critérios foram preservados. Não executar avaliadores protegidos ou pytest global. Publicação e recuperação são atestadas por seus próprios recibos, não apenas por esta afirmação documental.

Mantenha C:/BRASILEIRAO: código em brasileirao-predictor; acervo em DADOS_PRESERVADOS; roteiros/evidências em work; pacotes em ENTREGAS; bundles em BACKUPS; recibos em AUDITORIA. Sete requisitos externos/protegidos continuam no registro. Capital false; lucro executável não demonstrado. A automação DC pertence a outra tarefa identificada no próximo prompt; não a excluir junto com esta conversa.
''')
write(repo/'docs/ESTADO_ATUAL.md',f'''# Estado atual — PUB-20260910

Correções RES mantidas e reprodução ampliada para Linux. 345 testes Python por versão 3.13/3.14, 160 .NET e Compose com recuperação/desligamento aprovados. [Resultado](continuation/publication_2026-09-10/RESULTADO.md), [registro corrente](continuation/publication_2026-09-10/REGISTROS.json) e [recibos CI](continuation/publication_2026-09-10/evidence/ci-{run_id}/summary.json).

O sistema não está integralmente homologado: CI global protegida não executada, dados comerciais insuficientes e sete requisitos ainda bloqueados. A parcela Linux de RCA-P09 foi fechada. Não há lucro executável comprovado; capital false. Conteúdo e cobertura anteriores foram preservados, com 399 leituras semânticas e 59 arquivos restritos a contratos/metadados.

Publicação/clone/pull/backup: consultar C:/BRASILEIRAO/AUDITORIA/PUBLICACAO_2026-09-10.json e a evidência de recuperação na entrega. Guias históricos são fotografias de suas datas, não estados concorrentes.
''')
write(repo/'docs/DATA_MAP.md','''# Mapa corrente de dados e fontes — PUB-20260910

Leia [dados, fontes e recuperação](continuation/publication_2026-09-10/DADOS_E_FONTES.md), [metadados reconferidos](continuation/publication_2026-09-10/evidence/source-metadata.json) e [contratos RES](continuation/resolution_2026-09-10/CONTRATOS.md). Os mapas históricos permanecem acessíveis pelo índice.

Atualizar este mapa não torna as bases completas. CSV histórico e helpers conservam seus hashes; coleta futura e lacunas comerciais têm estado explícito. Coortes protegidas não foram lidas. Os dados recebidos permanecem em C:/BRASILEIRAO/DADOS_PRESERVADOS e nos trabalhos DC/BE; raws/privados não são substituídos pelo clone do GitHub público.
''')
write(repo/'docs/continuation/RETOMADA.md','''# Retomada — PUB-20260910

Leia [próximo prompt](publication_2026-09-10/PROXIMO_PROMPT.md), [resultado](publication_2026-09-10/RESULTADO.md), [registro](publication_2026-09-10/REGISTROS.json) e [releitura do chat](publication_2026-09-10/REVISAO_DO_CHAT.md). Mandatos e histórico visível estão arquivados na pasta PUB. Trabalho atual: C:/BRASILEIRAO/work/publication-2026-09-10.

Não supor conclusão do primeiro mandato ou liberação de capital. O escopo Linux sintético foi validado; CI global e requisitos externos/protegidos permanecem limitados. Preservar coletas, agenda DC, dados locais e arquivos históricos. Confirmar recibo de publicação/recuperação antes de tratar o checkout remoto como entregue.
''')
write(repo/'docs/INDICE_DOCUMENTACAO.md',f'''# Índice corrente — PUB-20260910

- [Resultado](continuation/publication_2026-09-10/RESULTADO.md)
- [Registro corrente](continuation/publication_2026-09-10/REGISTROS.md)
- [Releitura e decisões](continuation/publication_2026-09-10/REVISAO_DO_CHAT.md)
- [Dados, fontes e recuperação](continuation/publication_2026-09-10/DADOS_E_FONTES.md)
- [Reprodução](continuation/publication_2026-09-10/REPRODUZIR.md)
- [Próximo prompt](continuation/publication_2026-09-10/PROXIMO_PROMPT.md)
- [Todos os Markdown](continuation/publication_2026-09-10/INDICE_TODOS_MDS.md)
- [Matriz integral do mandato](continuation/reconciliation_2026-09-10/MATRIZ_MANDATO.md)
- [Contratos das correções RES](continuation/resolution_2026-09-10/CONTRATOS.md)
- [Mandato consolidado preservado](continuation/publication_2026-09-10/archive/instructions/PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md)
- [Mandato original preservado](continuation/publication_2026-09-10/archive/instructions/MANDATO_RECEBIDO_2026-09-09.txt)
- [Histórico visível arquivado](continuation/publication_2026-09-10/archive/chat/chat-visible.txt)
- [Validação Linux final](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/{run_id})

Documentos anteriores e roteiros em archive são fotografias datadas. Não foram reescritos para aparentar atualização ou aprovar requisitos abertos. Estado corrente deriva de PUB/REGISTROS.json; hashes e recibos preservam as referências históricas.
''')
write(base/'LEIA_PRIMEIRO.md','''# BRASILEIRAO — PUB-20260910

Projeto: C:/BRASILEIRAO/brasileirao-predictor. Comece pelo README.md e docs/continuation/publication_2026-09-10/RESULTADO.md. Mandatos, contexto visível, decisões e próximos passos estão versionados na pasta PUB. Registro de publicação e recuperação: AUDITORIA/PUBLICACAO_2026-09-10.json.

Organização: brasileirao-predictor = código e documentação; DADOS_PRESERVADOS/MIGRACAO_DADOS = acervo recebido; work = ambientes, fontes e ensaios datados; INSTRUCOES = mandatos e retomada; ENTREGAS = pacotes; BACKUPS = bundles/arquivos; AUDITORIA = recibos. Nenhum banco ou caminho ativo foi movido para arrumar a navegação.

Python, .NET e Compose Linux passaram no escopo sintético. Sete requisitos externos/protegidos continuam registrados; CI global não executada e lucro executável não demonstrado. Capital desabilitado. H14/H15/H9/A1 protegidos; trabalho solo. Preserve toda esta pasta: o GitHub público não contém dados privados ou raws sem redistribuição estabelecida. Próximo prompt: INSTRUCOES/PROXIMO_PROMPT_APOS_PUBLICACAO_2026-09-10.md.
''')
shutil.copyfile(dest/'PROXIMO_PROMPT.md',base/'INSTRUCOES/PROXIMO_PROMPT_APOS_PUBLICACAO_2026-09-10.md')
dump(dest/'evidence/publication-plan.json',{'at':datetime.now(UTC).isoformat(),'tested_head':ci['head'],'integration':'fast-forward the reviewed branch into main, commit documentation with [skip ci], push main without force','verification':'fresh clone started at old remote ac22c56; pull --ff-only after publication, compare HEAD/tree and versioned evidence, build final package, bundle/fsck/restore','archive_notes':'historical records immutable; final local Git/audit receipt cannot contain its own commit hash recursively','no_operational_or_financial_change':True})
print(json.dumps({'guides_updated':6,'registry':reg['summary']['statuses'],'ci_run':run_id,'helpers':reg['publication']['archived_helper_files']}))
