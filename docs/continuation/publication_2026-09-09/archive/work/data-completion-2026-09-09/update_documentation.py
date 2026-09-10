"""Reconcile current entry documents; preserve frozen studies and contracts."""
from pathlib import Path

REPO = Path('C:/BRASILEIRAO/brasileirao-predictor')
DOC = REPO / 'docs/continuation/data_completion_2026-09-09'
texts = {
'docs/ESTADO_ATUAL.md': '''# Estado atual — 09/09/2026, rodada DC-20260909

Referência vigente para a raiz **`C:/BRASILEIRAO`**. O
[mandato](continuation/MANDATO_LUCRO_2026-09-09.md) define objetivo e restrições.
**Dados adicionais obtidos; lucro executável não demonstrado; capital bloqueado.**

## Código e ambiente

Checkout `C:/BRASILEIRAO/brasileirao-predictor`, branch `main`. A base desta
rodada foi `5dec2521bab581d5dda104d954f4cc6274b74702`, posterior à pesquisa PF
e à consolidação documental. O SHA final, diff e backup constam do recibo
`C:/BRASILEIRAO/AUDITORIA/DADOS_COMPLEMENTARES_2026-09-09.json`.
Nenhum push desta rodada foi realizado. O pacote original permanece associado
a d42a3e0; não houve reset ou recriação de branches antigas.

Python 3.13.12, pytest 8.4.2, Ruff 0.12.12 e Pyright 1.1.405 em
`C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv`.
Core 3.2.0 / Ops 4.1.0 continuam fixados no lock, mas não foram instalados no
ambiente mínimo. Aplicação operacional completa, .NET/Redis/Compose não foram
instalados ou validados por esta rodada. Ferramentas de sistema e o aplicativo
Codex continuam sendo dependências externas à pasta; mover um venv pode exigir
reinstalação. Não confundir código versionado, ambiente instalado e serviço ativo.

## Dados e integridade

A migração foi conferida por SHA-256 e CRC: **12.423 entradas mais o manifesto**,
9.477.623.208 bytes descompactados, em `C:/BRASILEIRAO/DADOS_PRESERVADOS`.
Recibo original: `C:/BRASILEIRAO/AUDITORIA/verificacao_migracao_2026-09-09.json`.
ZIP, bundle, cinco snapshots SQLite e configurações recebidas foram preservados.
As 21 entregas PF foram copiadas com igualdade de hash para `ENTREGAS`;
o mandato original está em `INSTRUCOES`.

Os novos insumos ficam em `C:/BRASILEIRAO/work/data-completion-2026-09-09`:

| Insumo | Resultado e interpretação |
| --- | --- |
| OddsPapi Jan–Jun/2026 | 177/177 timelines verificadas; 623.271.596 bytes; 22 reutilizadas e 155 novas |
| Football-Data oficial | CSV recuperado; 380 jogos de 2025, 158 pares closing numericamente completos |
| Catálogos atuais | Identidades de bookmaker e 21 fixtures elegíveis; evento escolhido antes das odds |
| Capturas prospectivas iniciais | Três capturas de um evento com recibos reais; Bet365 Brasil inativa nas três |
| Acesso/custo de dados | Plano gratuito existente verificado; contador 62 → 67/250; reserva 20 preservada |

Os 177 arquivos estão completos para o universo declarado. Isso não equivale
à completude dos campos exigidos: faltam procedência temporal histórica,
capacidade, condições reais de custo e validação futura. O
[resultado atual](continuation/data_completion_2026-09-09/RESULTADO.md) e a
[matriz de pendências](continuation/data_completion_2026-09-09/PENDENCIAS.md)
detalham a diferença. Nenhum resultado de 2026 ou de coorte protegida foi usado.

## Operação e continuidade

Nenhum banco operacional, Redis, serviço ou tarefa Windows do projeto foi
iniciado. As coletas pontuais DC foram processos de aquisição independentes,
encerrados após gravar seus recibos. A chave existente de API de dados foi lida
somente por esses processos; os testes e a pesquisa offline ficaram sem credenciais.

Está ativo um acompanhamento **nesta tarefa do Codex**, diário às **19:57 de
São Paulo**, para a captura fixa de 11/09 antes das 20:00. Sua janela, quota,
idempotência e encerramento estão em
[CONTINUIDADE.md](continuation/data_completion_2026-09-09/CONTINUIDADE.md).
A definição ativa reside no armazenamento do aplicativo; uma cópia documental
fica em `C:/BRASILEIRAO/AUDITORIA/automacao_dados_2026-09-09.toml`.
O computador precisa estar ligado e o aplicativo em execução para acessar os
arquivos locais. Agendamento não garante chegada na janela nem disponibilidade da API.

H14/H15/H9/A1, resultados, observadores, contratos, claims e agendas permanecem
intactos. As tarefas exportadas da migração não foram importadas. Não restaurar
bancos por cima de dados ativos nem executar avaliadores para organizar arquivos.

## Evidência e checks

Zero pares admitidos para execução. O replay closing de 2025 congelou 32
escolhas antes dos labels e apurou −9,24u no cenário de fricção 2%, banca 100u.
Todas as seleções ocorreram no período em que a fonte avisa desatualização da
referência Pinnacle; o saldo é aritmético condicional, não validação econômica.

**137 testes passaram**: 80 existentes e 57 novos. Ruff e Pyright dos três
novos módulos passaram; uma conferência com Fraction confirmou a conta sem
importar esses módulos. Seis fronteiras UTC e execução fora da janela
verificaram a espera sem consumo de API. Checks são delimitados à pesquisa,
não evidência de CI remoto atualizado ou instalação operacional completa.

## Limite da garantia da pasta

Todos os arquivos recebidos no pacote verificado, o Git recuperado e as
entregas e dados conhecidos destas sessões estão sob `C:/BRASILEIRAO`.
A captura de 08/09 não é imagem integral do computador antigo: o manifesto
registra omissão do cache `.pytest_cache` por acesso negado na origem.
Arquivos nunca enviados ou criados depois da captura não podem ser atestados.
Os documentos históricos e contratos congelados são indexados e preservados;
os guias atuais foram reconciliados com a rodada DC.
''',
'docs/continuation/RETOMADA.md': '''# Retomada — C:/BRASILEIRAO, DC-20260909

Leia [estado atual](../ESTADO_ATUAL.md), [mandato](MANDATO_LUCRO_2026-09-09.md),
[resultado DC](data_completion_2026-09-09/RESULTADO.md) e
[continuidade](data_completion_2026-09-09/CONTINUIDADE.md).
Trabalhe sozinho. Lucro executável não está demonstrado; capital bloqueado.

## Checkpoint

Base da rodada `main` em `5dec2521bab581d5dda104d954f4cc6274b74702`; commit
de integração no recibo `C:/BRASILEIRAO/AUDITORIA/DADOS_COMPLEMENTARES_2026-09-09.json`.
177/177 históricos verificados, CSV de 380 jogos de 2025 recuperado e três
capturas atuais de um único evento. Não repetir downloads completos.
O fechamento tem aviso de referência Pinnacle desatualizada; no piloto a
oferta Bet365 Brasil tinha `bookmakerIsActive=false`. Seleções ativas nos
filhos não anulam o estado inativo do bookmaker. Zero admissões para execução.

O replay closing condicional perdeu 9,24u; não ajustar filtros após esse saldo
nem chamar a fonte comprometida de validação. Os 137 testes da pesquisa
passaram. Nenhuma coorte protegida ou resultado de 2026 foi avaliado.

## Próxima ação concreta

O acompanhamento diário às 19:57 de São Paulo executa a rotina delimitada
`C:/BRASILEIRAO/work/data-completion-2026-09-09/followup_capture.py`.
Antes de 11/09 19:55, retorna WAITING sem API. Na janela, no máximo uma
consulta de odds para o fixture congelado `id1000032566887012`, par
Pinnacle / bet365.bet.br, antes da decisão de 11/09 20:00.
Conta gratuita e reserva mínima são novamente verificadas. Chegada tardia
não autoriza redefinir o corte ou fabricar disponibilidade.

Depois da captura, executar `audit_followup.py` em processo separado e sem
credenciais. Exigir clocks, calendário congelado e todos os estados ativos
antes de admitir a observação; aceite, capacidade e custos continuam separados.
Até duas consultas públicas oficiais úteis por rodada diária são permitidas.
Não repetir testes sem mudança ou falha que justifique. Em 12/09, ou ao
terminar a captura auditada, reavaliar o próximo passo dentro do mandato e
pausar o acompanhamento se nenhuma ação útil autorizada restar.

## Caminhos e reprodução

Código: `C:/BRASILEIRAO/brasileirao-predictor`. Novos dados, recibos e scripts:
`C:/BRASILEIRAO/work/data-completion-2026-09-09`. Entrega atual:
`C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_DC_20260909`.
[Reprodução offline](data_completion_2026-09-09/REPRODUZIR.md),
[pendências](data_completion_2026-09-09/PENDENCIAS.md) e [mapa de dados](../DATA_MAP.md).

Preservar H14/H15/H9/A1, artefatos, contratos, observadores, quotas reservadas,
claims, agendas e avaliadores. Não importar tarefas antigas nem ligar runtime
para reproduzir essa pesquisa. Nenhuma aposta, conta de apostas, compra ou
alteração financeira está autorizada. O ambiente mínimo Python não é uma
instalação operacional completa.

A [rodada PF anterior](price_feasibility_2026-09-09/RESULTADO.md) e os
[guias anteriores à consolidação](../history/antes_consolidacao_2026-09-09/README.md)
preservam seu contexto histórico. Não atualizar resultados congelados para
fazê-los parecer vigentes; atualizar os guias de entrada e acrescentar novo checkpoint.
''',
'docs/PROMPT_PROXIMA_SESSAO.md': '''# Próxima sessão — dados e execução verificáveis

Trabalhe sozinho em `C:/BRASILEIRAO/brasileirao-predictor`, mantendo os dados
e entregas em `C:/BRASILEIRAO`. Leia [ESTADO_ATUAL](ESTADO_ATUAL.md),
[RETOMADA](continuation/RETOMADA.md),
[mandato](continuation/MANDATO_LUCRO_2026-09-09.md),
[resultado DC](continuation/data_completion_2026-09-09/RESULTADO.md) e
[CONTINUIDADE](continuation/data_completion_2026-09-09/CONTINUIDADE.md).

Continue resolvendo as pendências concretas de preços, procedência temporal,
capacidade, custos e validação. Os 177 históricos já foram adquiridos e
verificados; não repetir o lote nem alterar filtros com base no saldo closing.
A fonte pública avisa referência Pinnacle desatualizada. No piloto, a Bet365
Brasil estava inativa no estado do bookmaker. Nada disso demonstra lucro.

O acompanhamento já está configurado na tarefa atual, diariamente às 19:57
de São Paulo. Use a rotina e a janela UTC congeladas para a captura de 11/09,
respeitando idempotência, quota e reserva. A auditoria deve rodar em processo
separado sem credenciais. Não recrie a automação nem force aquisição fora da janela.

Preserve H14/H15/H9/A1 integralmente. Não execute avaliadores, apostas,
logins de casas ou compras; não abra coortes como holdout. Novas decisões
materiais precisam de protocolo anterior ao desempenho. Atualize apenas os
guias atuais e novos checkpoints; conserve os documentos históricos.

Verifique HEAD e diff antes de editar; o recibo final está em
`C:/BRASILEIRAO/AUDITORIA/DADOS_COMPLEMENTARES_2026-09-09.json`.
[HANDOFF](../HANDOFF.md) e [índice documental](INDICE_DOCUMENTACAO.md) mantêm
o histórico. Não usar caminhos do computador antigo como destinos de escrita.
''',
}
for name, body in texts.items():
    (REPO / name).write_text(body, encoding='utf-8')

path = REPO / 'HANDOFF.md'
old = path.read_text(encoding='utf-8')
checkpoint = '''## 2026-09-09 — DC-20260909: aquisição concluída, admissibilidade pendente

Base `5dec2521bab581d5dda104d954f4cc6274b74702`, main consolidada em
`C:/BRASILEIRAO/brasileirao-predictor`. [Estado atual](docs/ESTADO_ATUAL.md),
[resultado](docs/continuation/data_completion_2026-09-09/RESULTADO.md) e
[continuidade](docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md).

Obtidos 177/177 históricos OddsPapi verificados (623.271.596 bytes), CSV oficial
de 380 jogos de 2025, catálogos atuais e três capturas de um evento. Cinco
requisições de quota gratuita; conta 67/250 ao término e reserva 20 intacta.
Zero pares admitidos para execução. Oferta Bet365 Brasil inativa no piloto.
Replay closing condicional: 32 seleções, −9,24u com fricção 2%; todas no período
do aviso de referência Pinnacle desatualizada. Não constitui validação econômica.

137 testes passaram, Ruff e Pyright dos três novos módulos, conta independente
com Fraction. Coletas pontuais encerradas; acompanhamento diário às 19:57 de
São Paulo ativo nesta tarefa para uma captura antes de T−60 em 11/09. Sem
apostas, compra, ativação operacional ou alteração de H14/H15/H9/A1.
Dados brutos e scripts em `C:/BRASILEIRAO/work/data-completion-2026-09-09`;
entrega em `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_DC_20260909`.
Commit final e backup constam de `C:/BRASILEIRAO/AUDITORIA`.

---

'''
first, rest = old.split('\n', 1)
path.write_text(first + '\n\n' + checkpoint + rest.lstrip('\n'), encoding='utf-8')

path = REPO / 'docs/DATA_MAP.md'
old = path.read_text(encoding='utf-8')
section = '''## Aquisição DC-20260909

Área canônica `C:/BRASILEIRAO/work/data-completion-2026-09-09`:

| Subárea | Conteúdo e limite |
| --- | --- |
| `raw` | 177 timelines OddsPapi Jan–Jun/2026, 623.271.596 bytes; exploração sem recibo PIT da época |
| `universe.json`, `acquisition.json`, `transport_repair.json` | Universo congelado, tentativas, reaproveitamento verificado, hashes e um reparo de conexão |
| `public_sources`, `extra_docs/public_sources` | CSV Football-Data, páginas oficiais e recibos HTTP; não versionar os corpos das páginas |
| `prospective_pilot` | Catálogos, fixture escolhido antes das odds, três capturas reais e recibos sanitizados |
| `closing-01` | Escolhas congeladas antes dos labels 2025 e liquidação exclusivamente condicional |
| `admission-01` | Auditoria de identidade/estado/clocks, qualidade closing e manifestos |
| `tests-02` | JUnit e log da execução de 137 testes isolados |
| `followup`, `followup_audit` | Saídas futuras, criadas somente quando houver tentativa/captura na janela |

Os 22 históricos reutilizados vieram de entradas antigas explicitamente
permitidas de Jan–Jun/2026; os demais 155 foram adquiridos. O universo de 177
fixtures tem SHA-256 `6264b2a1b795928fdf0dc6476e311535a42fbc96c12caf5cf881777b7779caba`.
O CSV bruto tem SHA-256 `ba3e9ea79ab4091b117a901f3914940cea07f1fe06de0deb57af5076f664ccb6`.
Somente linhas de 2025 foram usadas no replay de preços e labels; nenhum
resultado de 2026 ou de coorte protegida foi avaliado.

A configuração privada preservada foi consultada apenas pelos processos de
aquisição da API existente. Não há cópia de credenciais no checkout, nos
scripts, nos recibos públicos ou no processo de pesquisa offline. O fato de
um arquivo ter hash válido não comprova disponibilidade passada, autenticidade
da oferta, capacidade ou aceite.

Código, protocolos, resumos e recibos sanitizados ficam em
`docs/continuation/data_completion_2026-09-09`; entrega em
`C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_DC_20260909`. A automação do aplicativo
tem cópia de sua definição em `C:/BRASILEIRAO/AUDITORIA`.
[Resultado e lacunas](continuation/data_completion_2026-09-09/RESULTADO.md),
[reprodução](continuation/data_completion_2026-09-09/REPRODUZIR.md).

'''
old = old.replace('## Como resolver caminhos antigos\n', section + '## Como resolver caminhos antigos\n')
path.write_text(old, encoding='utf-8')

path = REPO / 'docs/HISTORICAL_SOURCE_REGISTER.md'
old = path.read_text(encoding='utf-8')
_, rest = old.split('\n', 1)
path.write_text('''# Registro de fontes históricas

## Verificação DC-20260909 — 09/09/2026

Aceitação de uma fonte para um uso técnico não significa aceitação econômica
de todos os seus dados. Contratos, captura, estado e período são avaliados
por observação. [Resultado e recibos](continuation/data_completion_2026-09-09/RESULTADO.md).

| Fonte verificada | Aquisição e cobertura | Estado para esta rodada | Pendência decisiva |
| --- | --- | --- | --- |
| [OddsPapi histórico](https://oddspapi.io/us/docs/get-historical-odds) | 177/177 timelines Jan–Jun/2026, Pinnacle e Bet365; conta existente e histórico sem incremento de quota | Histórico exploratório adquirido | Sem receipt histórico local, calendário PIT e prova de disponibilidade contínua |
| [OddsPapi atual](https://oddspapi.io/us/docs/get-odds) | Três capturas reais, Pinnacle / bet365.bet.br | Oferta rejeitada por bookmakerIsActive=false | Nova observação ativa antes do corte; limite/custos não demonstrados |
| [Football-Data Brasil](https://football-data.co.uk/brazil.php) | BRA.csv oficial recuperado sem www; 380 jogos de 2025, 158 pares closing numéricos | Cenário condicional com referência comprometida | [Aviso oficial](https://football-data.co.uk/data) de Pinnacle desatualizada desde 23/07/2025; clocks e execução ausentes |
| [The Odds API histórico](https://the-odds-api.com/historical-odds-data/) | Documentação pública; API autenticada não consumida | Alternativa paga, não adquirida | Plano, acesso e custo não autorizam compra nesta rodada |
| [Odds-API.io gratuito](https://odds-api.io/pricing/free) | Documentação pública; sem nova conta | Alternativa não adquirida | Restrições de casas sharp no plano gratuito |
| [Betfair histórico](https://betfair-datascientists.github.io/data/usingHistoricDataSite/) | Guia público; basic com preço negociado, níveis superiores com mais dados | Download não realizado | Login necessário; preço negociado não equivale a ladder executável com volume |

As fontes novas não fornecem por si só limites pessoais, slippage, confirmação
de aceite, custo total ou amostra prospectiva de validação. Campos ausentes
permanecem desconhecidos. Não reutilizar resultados H14/H15/H9/A1 para completá-los.

## Registro anterior preservado

Os estados abaixo são a classificação histórica do projeto. Não comprovam
configuração, cobertura, disponibilidade ou operação ativa nesta máquina.

''' + rest.lstrip('\n'), encoding='utf-8')

path = REPO / 'brasileirao_predictor/research/price_strength/README.md'
old = path.read_text(encoding='utf-8')
first, rest = old.split('\n', 1)
path.write_text(first + '''

## Complemento DC-20260909: admissibilidade e contabilidade

Três módulos puros e aditivos, sem chamadas de API ou banco:

- `historical_admission.py`: último estado antes de T−60, rejeição de estados
  conflitantes/inativos e validação dos clocks; timeline não ganha receipt histórico inventado.
- `live_capture_admission.py`: identidade e estados de bookmaker, mercado e
  seleção; receipt local não vira publicação do bookmaker ou fill garantido.
- `closing_scenario.py`: congela escolhas usando somente preços, depois
  liquida labels; reserva exposição diária e reconcilia principal, retornos e custos.

São usados pelos scripts isolados da
[rodada DC](../../../docs/continuation/data_completion_2026-09-09/REPRODUZIR.md).
Não ativam scanner operacional, capital ou coortes. O cenário closing não é
validação econômica e a fonte teve problema documentado na referência.
Os resultados anteriores abaixo mantêm seu escopo.

''' + rest.lstrip('\n'), encoding='utf-8')

path = Path('C:/BRASILEIRAO/LEIA_PRIMEIRO.md')
old = path.read_text(encoding='utf-8')
old = old.replace('continuation/price_feasibility_2026-09-09/RESULTADO.md', 'continuation/data_completion_2026-09-09/RESULTADO.md')
old = old.replace('Os dados da migração são preservação, não operação ativa. Nenhum banco, serviço,\ncoletor ou tarefa foi iniciado. H14/H15/H9/A1 continuam protegidos e o capital\npermanece bloqueado. Lucro executável não foi demonstrado.', '''A rodada DC obteve 177/177 históricos verificados, CSV oficial de 380 jogos
de 2025 e três capturas atuais. Passaram 137 testes delimitados. Zero pares
admitidos para execução; faltam condições temporais, capacidade, custos reais
e validação futura. [Pendências](brasileirao-predictor/docs/continuation/data_completion_2026-09-09/PENDENCIAS.md).

As coletas pontuais independentes foram encerradas. Está ativo um
[acompanhamento nesta tarefa do Codex](brasileirao-predictor/docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md),
diário às 19:57 de São Paulo, preparando uma captura antes de T−60 em 11/09.
Sua definição foi copiada para AUDITORIA; a agenda ativa pertence ao aplicativo,
que precisa estar em execução com o computador ligado.

Os dados da migração permanecem preservados. Nenhum banco operacional,
serviço ou tarefa Windows do projeto foi iniciado. H14/H15/H9/A1 continuam
protegidos; capital bloqueado. Lucro executável não foi demonstrado.''')
old = old.replace('- [Conferência de completude desta pasta]', '- [Auditoria dos novos dados](AUDITORIA/DADOS_COMPLEMENTARES_2026-09-09.md)\n- [Conferência de completude desta pasta]')
path.write_text(old, encoding='utf-8')
print('Current entry documents reconciled; frozen protocols and studies untouched.')
