"""Explicit documentation edits after preserving earlier versions."""
from pathlib import Path

ROOT = Path('C:/BRASILEIRAO')
REPO = ROOT / 'brasileirao-predictor'
DOCUMENTS = {
'README.md': '''# brasileirao-predictor

Pesquisa quantitativa e software de previsão para o Brasileirão Série A.
**Raiz local: `C:/BRASILEIRAO`. Rentabilidade executável não demonstrada;
capital bloqueado.**

## Comece aqui

1. [Estado atual verificado](docs/ESTADO_ATUAL.md): código, ambiente, dados e operação.
2. [Retomada](docs/continuation/RETOMADA.md): sequência para a próxima sessão.
3. [Mandato vigente](docs/continuation/MANDATO_LUCRO_2026-09-09.md): objetivo e restrições.
4. [Mapa de dados](docs/DATA_MAP.md) e [índice de todos os Markdown](docs/INDICE_DOCUMENTACAO.md).
5. [Histórico de checkpoints](HANDOFF.md): resultados e protocolos de cada época.

## Resultado mais recente

A [rodada de preços de 09/09/2026](docs/continuation/price_feasibility_2026-09-09/RESULTADO.md)
examinou 380 jogos de 2025: 374 vetores 1X2 numéricos e nenhum par de preços
admissível para replay executável, por falta de casa/clocks. A melhoria de
cotação necessária foi 7,83% na mediana sob referência proporcional do próprio
vetor e custo hipotético de 2%. Nenhuma oferta independente dessa magnitude
foi observada. Foram 380 abstenções, sem labels avaliados ou lucro demonstrado.

Passaram 80 testes da rodada e 1.870 relações em conferência Decimal separada.
Isso valida o diagnóstico delimitado, não a instalação operacional completa.
Novos ajustes de xG perderam prioridade para preços e execução verificáveis.

## O que está instalado e preservado

| Componente | Situação em 09/09/2026 |
| --- | --- |
| Código e histórico Git | `C:/BRASILEIRAO/brasileirao-predictor`, branch `main` |
| Dados migrados | Extração verificada em `C:/BRASILEIRAO/DADOS_PRESERVADOS` |
| Pacotes originais | Preservados em `C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS` |
| Entrega da pesquisa | `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_PF_20260909` |
| Ambiente de pesquisa | Python 3.13.12, isolado em `C:/BRASILEIRAO/work/price-feasibility-2026-09-09` |
| Aplicação operacional | Não instalada/ativada nesta máquina pelas sessões atuais |

O lock do projeto fixa Core 3.2.0 / Ops 4.1.0. O ambiente de pesquisa contém
somente as ferramentas necessárias à rodada. Dependências declaradas, ambiente
instalado e operação efetiva são estados diferentes.

## Usar e desenvolver

A [reprodução offline da pesquisa](docs/continuation/price_feasibility_2026-09-09/REPRODUZIR.md)
usa entradas explícitas e diretórios novos. Para uma futura instalação completa,
consulte [migração e instalação](docs/MIGRACAO_WINDOWS.md) e os contratos do
runtime em [MODERNIZATION.md](docs/MODERNIZATION.md). Essa instalação exige
validação própria; não execute comandos de coleta/governança como inicialização.

O código possui modelos Elo/xG/gols, pesquisa PIT, scanner de preços e runtime
Python/Redis/.NET. Esses componentes são meios de investigação, não evidência
de lucro. Sofascore alimenta o histórico; outras integrações têm contratos,
quotas e reservas específicos. Fontes e relógios precisam ser demonstrados.

H14/H15/H9/A1, claims, agendas e dependências de coleta continuam protegidos.
Nenhum resultado intermediário, avaliador oficial, renovação de atestado ou
ação financeira está autorizado pela organização dos arquivos. CLV e métricas
probabilísticas isolados não autorizam capital.

Os [textos anteriores a esta consolidação](docs/history/antes_consolidacao_2026-09-09/README.md)
foram preservados, assim como todos os estudos e contratos congelados. Use o
estado atual para caminhos e situação do host; use documentos históricos para
reproduzir a época em que foram escritos.
''',
'docs/ESTADO_ATUAL.md': '''# Estado atual — 09/09/2026

Esta é a referência de estado local. O [mandato](continuation/MANDATO_LUCRO_2026-09-09.md)
define o objetivo e as restrições; documentos datados preservam seu significado
histórico. A raiz solicitada pelo usuário é **`C:/BRASILEIRAO`**.

## Código

O checkout fica em `C:/BRASILEIRAO/brasileirao-predictor`, na branch `main`.
A base remota verificada é `f00304574044ab9d18aa3603abc538fbb3102c64`; a rodada
de pesquisa está no commit local `f33f92b37bd2c56cf0db978e7f5ad58d9cbae3ec`.
A consolidação documental desta etapa fica no commit posterior, identificado
no recibo em `C:/BRASILEIRAO/AUDITORIA`. Nenhum push dessa pesquisa ou desta
organização foi realizado. O Git local contém o histórico recuperado; o bundle
original de migração permanece associado a d42a3e0.

`git fsck --full` não encontrou corrupção. Objetos soltos de preparações do
índice não são arquivos perdidos da árvore; não foi feita limpeza destrutiva.
Uma cópia Git completa da main consolidada acompanha o recibo final de backup.

## Ambiente

O projeto requer Python 3.13 ou 3.14. A pesquisa executada usa Python 3.13.12,
pytest 8.4.2, Ruff 0.12.12 e Pyright 1.1.405 em
`C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv`.
Seu Python gerenciado também fica sob `C:/BRASILEIRAO`.

Core 3.2.0 / Ops 4.1.0 estão fixados no lock do código. Eles não foram
instalados neste ambiente mínimo; a aplicação operacional e o ambiente completo
não foram montados. Ferramentas de sistema, .NET, Git, o aplicativo Codex e suas
bibliotecas não passam a ser portáveis apenas porque os arquivos do projeto
foram reunidos. Recriar um ambiente em outro caminho pode exigir reinstalação.

## Dados e integridade

O ZIP foi integralmente conferido por SHA-256, CRC e hashes dos arquivos:
**12.423 entradas do manifesto**, mais o próprio manifesto, totalizando
**9.477.623.208 bytes descompactados**. A extração fica em
`C:/BRASILEIRAO/DADOS_PRESERVADOS`. O [mapa de dados](DATA_MAP.md) identifica
os arquivos brutos, as cinco cópias SQLite consistentes e os caminhos antigos.

Recibo: `C:/BRASILEIRAO/AUDITORIA/verificacao_migracao_2026-09-09.json`.
O ZIP original e seu bundle foram mantidos. Configurações privadas, tarefas
exportadas e coortes foram preservadas como arquivos; não foram ativadas,
avaliadas ou usadas como dados novos de pesquisa. Não abrir conteúdo protegido
para verificar completude: usar manifesto, tamanhos e hashes.

As 21 entregas da pesquisa que estavam na pasta desta conversa foram copiadas
com igualdade de SHA-256 para `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_PF_20260909`.
O mandato recebido também está em `C:/BRASILEIRAO/INSTRUCOES`.
Os originais externos foram conservados; a continuidade do projeto não depende
de consultá-los. O Git guarda agregados e código, não o ZIP nem dados privados.

## Operação

A consulta local de tarefas/processos não encontrou operação do projeto.
Nenhum serviço, banco, Redis, tarefa Windows ou coletor foi iniciado pelas
sessões atuais. O estado do computador antigo não foi consultado remotamente.
As sete tarefas historicamente habilitadas na origem não comprovam execução
neste Windows. Copiar seus XMLs não equivale a importar ou ativar tarefas.

H14/H15/H9/A1, artefatos, claims, regras e calendários permanecem protegidos.
Não restaurar bancos por cima de dados ativos, não combinar snapshots com WAL
antigo, não renovar atestados nem executar avaliadores para organizar arquivos.

## Evidência econômica

Lucro líquido executável continua **não demonstrado**. A última rodada teve
374/380 vetores 1X2 numéricos, mas zero pares de preços com proveniência
suficiente. O requisito mediano de 7,83% de melhoria de cotação sob o cenário
de custo 2% é diagnóstico, não oferta encontrada. 80 testes e 1.870 relações
aritméticas foram validados nessa rodada. Nenhum label/coorte foi avaliado.

O próximo insumo decisivo é uma amostra independente e autorizada de oferta
e referência com clocks, estados, custos e capacidade de execução verificáveis.
A organização documental não abre nova rodada de modelagem ou aquisição.

## Limite da garantia de completude

Todos os arquivos **recebidos no pacote verificado**, o código Git recuperado
e as entregas conhecidas destas sessões estão sob `C:/BRASILEIRAO`.
O pacote é uma captura de 08/09/2026, não uma imagem integral do computador
antigo. Seu manifesto registra a omissão do cache `.pytest_cache` por acesso
negado na origem. Dados produzidos depois da captura ou nunca entregues não
podem ser atestados daqui. O inventário final distingue esses limites de
qualquer falha de cópia encontrada nesta máquina.
''',
'docs/continuation/RETOMADA.md': '''# Retomada — C:/BRASILEIRAO

Atualizado em 09/09/2026 após consolidação dos arquivos e da documentação.
O estado canônico é [ESTADO_ATUAL.md](../ESTADO_ATUAL.md). O mandato vigente
é [MANDATO_LUCRO_2026-09-09.md](MANDATO_LUCRO_2026-09-09.md).

## Sequência de leitura e trabalho

1. Leia estado atual, mandato, [DATA_MAP](../DATA_MAP.md) e o início do
   [HANDOFF](../../HANDOFF.md).
2. Confira `git status --short --branch`, `git rev-parse HEAD` e remotes no
   checkout `C:/BRASILEIRAO/brasileirao-predictor`. Não faça reset para SHA histórico.
3. Identifique se precisa de fonte técnica, contrato ou resultado arquivado no
   [índice de documentação](../INDICE_DOCUMENTACAO.md). Data antiga não é ordem atual.
4. Para pesquisa, escolha a pergunta e congele protocolo antes de novos valores.
   Confirme disponibilidade, execução, custo e isolamento antes de modelos.
5. Use somente dados explicitamente admissíveis em área de pesquisa; a extração
   de migração é preservação, não autorização para consultar coortes protegidas.

## Onde continuar

| Conteúdo | Caminho |
| --- | --- |
| Código, Git e documentos atuais | `C:/BRASILEIRAO/brasileirao-predictor` |
| Pacotes originais | `C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS` |
| Extração completa verificada | `C:/BRASILEIRAO/DADOS_PRESERVADOS` |
| Sessões antigas | `C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor-sessoes/2026-09-07` |
| Pesquisa de preços atual | `C:/BRASILEIRAO/work/price-feasibility-2026-09-09` |
| Entrega da pesquisa atual | `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_PF_20260909` |
| Auditorias de cópia e backup | `C:/BRASILEIRAO/AUDITORIA` |

Scripts congelados podem mencionar `Superleo13` ou a antiga pasta da conversa.
O [mapa de caminhos](../DATA_MAP.md) resolve os prefixos sem modificar hashes
ou conteúdo desses scripts. Não execute arquivos históricos em lote.

## Última decisão econômica

A [rodada de 09/09](price_feasibility_2026-09-09/RESULTADO.md) terminou com
bloqueio de preço: 380 jogos, 374 vetores 1X2 numéricos, nenhum par admissível
de casa/clocks. Não houve apostas ou labels avaliados. O aumento mediano de
cotação de 7,83% no cenário de custo 2% não é uma oferta observada nem lucro.
Os 80 testes e a conferência Decimal são específicos dessa medição.

Novos ajustes de xG não resolvem esse bloqueio. O próximo passo depende de
oferta/referência independentes e simultâneas, com custos e capacidade. Nenhuma
coleta recorrente foi criada. O mandato proíbe ações financeiras e preserva
H14/H15/H9/A1, inclusive avaliadores, estados, agendas e dependências.

## Histórico preservado

O texto anterior desta retomada está [arquivado integralmente](../history/antes_consolidacao_2026-09-09/docs/continuation/RETOMADA.md)
e no commit f33f92b. Estudos de 2025/2026 já explorados não são holdouts novos.
Os resultados negativos, hipóteses descartadas e protocolos não foram reescritos.
''',
'docs/continuation/PROMPT_MELHORIA_LUCRO.md': '''# Ponto de entrada para o mandato vigente

O mandato atual é [MANDATO_LUCRO_2026-09-09.md](MANDATO_LUCRO_2026-09-09.md).
Use o [estado atual](../ESTADO_ATUAL.md) e a [retomada](RETOMADA.md) para os
caminhos e a situação efetivamente verificada neste Windows.

Raiz: `C:/BRASILEIRAO`. Checkout: `C:/BRASILEIRAO/brasileirao-predictor`.
O objetivo continua encontrar e validar oportunidades econômicas executáveis
com integridade, preservando coortes e mantendo toda execução financeira simulada.

O prompt de 07/09 foi [arquivado sem reescrever seu conteúdo](../history/antes_consolidacao_2026-09-09/docs/continuation/PROMPT_MELHORIA_LUCRO.md).
Seus caminhos, estado de ambiente e tarefas pendentes representam aquela época;
não são a fila de execução atual. Não renovar atestados ou operar coortes por
seguir um comando de documento histórico.
''',
'docs/PROMPT_PROXIMA_SESSAO.md': '''# Próxima sessão

Trabalhe em `C:/BRASILEIRAO/brasileirao-predictor`.

Leia o [estado atual](ESTADO_ATUAL.md), a [retomada](continuation/RETOMADA.md),
o [mandato vigente](continuation/MANDATO_LUCRO_2026-09-09.md) e o início do
[HANDOFF](../HANDOFF.md). O [índice](INDICE_DOCUMENTACAO.md) identifica os
documentos ativos, os contratos protegidos e os arquivos históricos.

O projeto e os dados recebidos estão sob `C:/BRASILEIRAO`; consulte
[DATA_MAP.md](DATA_MAP.md). Não dependa da antiga pasta da conversa ou do
usuário `Superleo13`. Não confunda preservação dos dados com operação ativa.
''',
'docs/DATA_MAP.md': '''# Mapa de dados — C:/BRASILEIRAO

Atualizado em 09/09/2026. [Estado atual](ESTADO_ATUAL.md) e
[migração](MIGRACAO_WINDOWS.md) distinguem preservação, ambiente e operação.
O detalhamento anterior do schema e das coletas está
[arquivado](history/antes_consolidacao_2026-09-09/docs/DATA_MAP.md); seus números
de linhas e estados datados não foram recalculados nesta etapa.

## Armazenamento atual

| Área | Conteúdo e regra |
| --- | --- |
| `C:/BRASILEIRAO/brasileirao-predictor` | Checkout e histórico Git atual; código, contratos, testes e documentação |
| `C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS` | ZIP e bundle originais, checksums, manifesto e recibos da origem; preservar |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS` | Extração integral verificada, sem execução ou ajuste dos arquivos |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor` | Dados, relatórios e configurações recebidos do projeto na origem |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor-sessoes` | Insumos, saídas e evidências das sessões antigas |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/externos` | Dados externos e backups incluídos; não são novas fontes de pesquisa autorizadas |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/tarefa` | Evidências selecionadas da tarefa anterior |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/dados_recuperados_de_zips_mistos` | Dados únicos separados de ZIPs mistos na origem |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/migracao` | Configurações privadas e 27 definições de tarefas; não importadas |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/snapshots_sqlite` | Cinco snapshots consistentes, sem consultas de conteúdo nesta etapa |
| `C:/BRASILEIRAO/work` | Ambientes, scripts e insumos de pesquisa/organização desta máquina |
| `C:/BRASILEIRAO/ENTREGAS` | Entregas completas copiadas com igualdade de hash |
| `C:/BRASILEIRAO/INSTRUCOES` | Mandato original recebido, com hash preservado |
| `C:/BRASILEIRAO/AUDITORIA` | Completude, integridade, mapa dos Markdown e verificação de backup |

O banco operacional não foi instalado em `brasileirao-predictor/data/matches.db`.
A presença de arquivos versionados em `data/` não significa existência de
serving ou de banco populado no checkout. Credenciais e dados privados não
devem ser copiados para o Git, para a área executável de pesquisa ou para logs.

## Como resolver caminhos antigos

| Prefixo histórico | Local preservado nesta máquina |
| --- | --- |
| `C:/Users/Superleo13/projetos/brasileirao-predictor` | Código atual: `C:/BRASILEIRAO/brasileirao-predictor`; dados da captura: `C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor` |
| `C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes` | `C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor-sessoes` |
| `C:/Users/Superleo13/Documents/Codex/2026-09-07/le` | Consulte o sufixo de sessão sob `DADOS_PRESERVADOS/projetos/brasileirao-predictor-sessoes/2026-09-07`; entradas selecionadas também estão sob `DADOS_PRESERVADOS/tarefa` |
| `C:/predictor/data` | `C:/BRASILEIRAO/DADOS_PRESERVADOS/externos/predictor-data` |
| Entrega da conversa atual `...le/outputs/BRASILEIRAO_PF_20260909` | `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_PF_20260909` |

O manifesto é a referência para cada arquivo exato; não assumir que a troca
de prefixo basta para um insumo excluído do pacote. Código histórico excluído
do ZIP permanece no Git/bundle e nas fontes arquivadas versionadas.

## Snapshots SQLite

O campo `snapshot_restore_map` de
`C:/BRASILEIRAO/DADOS_PRESERVADOS/MANIFESTO_SHA256.json` associa os cinco snapshots
a `matches.db`, `odds_operational.db`, `research/prospective.db`,
`binance_spot_microstructure.sqlite3` e `feature_store.db`.
O recibo de extração conferiu seus hashes sem consultar tabelas.

Em eventual restauração operacional, usar o snapshot correspondente e nunca
misturá-lo com WAL/SHM brutos antigos. Dados de pesquisa protegida, ledgers,
travas/claims e calendários mantêm seus contratos; ter cópia não autoriza
consultar resultados ou avaliar coortes. Nenhum snapshot foi promovido a banco
operacional por esta consolidação.

## Verificação e limites

O recibo `AUDITORIA/verificacao_migracao_2026-09-09.json` confirma 12.423
entradas mais o manifesto, SHA-256/CRC e 9.477.623.208 bytes descompactados.
O inventário final confere também as cópias da entrega e arquivos Markdown.
Os dados refletem a captura de 08/09: alterações posteriores em outro PC
precisariam ser fornecidas para serem incluídas e verificadas.
''',
'docs/MIGRACAO_WINDOWS.md': '''# Migração e preservação — situação em C:/BRASILEIRAO

## O que já foi concluído

O código foi recuperado do bundle e atualizado por avanço direto para a main
remota f003045; a pesquisa posterior foi registrada localmente em f33f92b.
O histórico Git e os commits desta organização ficam no checkout
`C:/BRASILEIRAO/brasileirao-predictor`. Consulte [ESTADO_ATUAL](ESTADO_ATUAL.md)
e o recibo final em `C:/BRASILEIRAO/AUDITORIA` para o SHA consolidado.

O pacote em `C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS` foi preservado.
A extração integral foi verificada em `C:/BRASILEIRAO/DADOS_PRESERVADOS`:
12.423 entradas do manifesto mais o manifesto, conferidas por CRC e SHA-256.
Recibo: `C:/BRASILEIRAO/AUDITORIA/verificacao_migracao_2026-09-09.json`.

Código, dados recebidos, entregas e documentação estão na raiz solicitada.
A operação completa ainda não foi instalada/ativada; o ambiente Python existente
é o de pesquisa isolada. Não houve importação de tarefas, abertura de bancos,
renovação de atestados ou alteração de coortes.

## Repetir a conferência do pacote sem extrair novamente

```powershell
$migrationPython = 'C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Scripts/python.exe'
& $migrationPython -I 'C:/BRASILEIRAO/brasileirao-predictor/scripts/migration/verify_archive.py' 'C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS/brasileirao-predictor-dados.zip' --recibo 'C:/BRASILEIRAO/AUDITORIA/verificacao_repetida.json'
if ($LASTEXITCODE -ne 0) { throw 'Falha na verificação' }
```

O recibo deve ser novo. Essa ferramenta lê bytes e metadados; não importa a
aplicação nem consulta bancos. Não reextrair por cima de `DADOS_PRESERVADOS`.
Para uma extração adicional, usar uma pasta nova e manter a original intacta.

## Preparar outra instalação no futuro

O [mapa de dados](DATA_MAP.md) e `snapshot_restore_map` indicam os destinos
corretos. A captura dos dados está vinculada a d42a3e0 e não deve sobrescrever
governança versionada mais nova. Preservar as duas versões, inclusive claims
e bloqueios de avaliação única eventualmente recebidos depois da captura.

O lock do código atual fixa Core 3.2.0 / Ops 4.1.0 e requer Python >=3.13,<3.15.
Uma instalação completa deve usar esse lock em ambiente novo; copiar um venv
não torna seus caminhos portáveis. Não iniciar coleta/serving como teste de
instalação. Dependências externas e serviços precisam de validação própria.

As 27 definições de tarefas foram apenas preservadas. A ativação depende de
definir qual máquina será responsável por cada rotina e de conservar os contratos
protegidos, evitando duplicação. Agendas não serão adaptadas automaticamente.

Arquivos gerados no computador antigo depois de 08/09 não estão comprovados
por esta captura. O pacote contém dados privados e chaves; mantê-lo privado.
As [instruções originais de migração](history/antes_consolidacao_2026-09-09/docs/MIGRACAO_WINDOWS.md)
continuam arquivadas com seus caminhos e contexto históricos.
''',
}

for relative, text in DOCUMENTS.items():
    target = REPO / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8', newline='\n')

entry = '''# BRASILEIRAO — leia primeiro

Esta pasta reúne o código, o histórico Git, os dados recebidos, os artefatos e
a documentação do projeto. Estado verificado em 09/09/2026.

- [Estado atual](brasileirao-predictor/docs/ESTADO_ATUAL.md)
- [Retomada e sequência de trabalho](brasileirao-predictor/docs/continuation/RETOMADA.md)
- [Mandato vigente](brasileirao-predictor/docs/continuation/MANDATO_LUCRO_2026-09-09.md)
- [Mapa de dados e caminhos antigos](brasileirao-predictor/docs/DATA_MAP.md)
- [Índice de todos os Markdown do código](brasileirao-predictor/docs/INDICE_DOCUMENTACAO.md)
- [Resultado econômico mais recente](brasileirao-predictor/docs/continuation/price_feasibility_2026-09-09/RESULTADO.md)

| Pasta | Conteúdo |
| --- | --- |
| `brasileirao-predictor` | Repositório principal e documentação atual |
| `MIGRACAO_DADOS/MIGRACAO_DADOS` | Pacotes originais e recibos da origem |
| `DADOS_PRESERVADOS` | Extração integral verificada de 12.423 arquivos mais o manifesto |
| `ENTREGAS` | Relatórios e entregas completas desta máquina |
| `INSTRUCOES` | Mandato original recebido |
| `AUDITORIA` | Inventários, hashes e verificação de completude |
| `BACKUPS` | Bundle Git completo do estado consolidado |
| `work` | Ambientes e trabalho técnico isolado |

Os dados da migração são preservação, não operação ativa. Nenhum banco, serviço,
coletor ou tarefa foi iniciado. H14/H15/H9/A1 continuam protegidos e o capital
permanece bloqueado. Lucro executável não foi demonstrado.

A garantia de completude cobre o pacote recebido e os artefatos conhecidos
destas sessões. Não atesta arquivos posteriores à captura de 08/09 nem conteúdo
que permaneça somente no computador antigo. A omissão registrada na origem foi
o cache `.pytest_cache`, sem acesso naquele momento.
'''
(ROOT / 'LEIA_PRIMEIRO.md').write_text(entry, encoding='utf-8', newline='\n')
print(f'Updated {len(DOCUMENTS)} repository documents and root entry point')
