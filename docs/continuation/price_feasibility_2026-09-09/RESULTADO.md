# Preço executável: bloqueio demonstrado e fronteira econômica medida

Rodada PF-20260909, encerrada em 09/09/2026. **Lucro não demonstrado.** O
experimento de admissão foi executado; o replay entre casas não foi executado
por falta de preços admissíveis. Não confundir esse bloqueio com ausência de
oportunidades no mercado. A rodada não reabriu nenhum estudo anterior.

## 1. Pergunta, prioridade e hipótese

A pergunta escolhida foi: uma oferta 1X2 de casa identificada supera uma
referência independente, observável no mesmo instante, após custos?
O mecanismo seria uma diferença de preço entre casas. A casa ofertante seria
excluída da referência; o instante seria 60 minutos antes do kickoff, idade
máxima de 120 segundos e diferença máxima de 30 segundos entre capturas.

Essa pergunta recebeu prioridade porque os estudos anteriores de xG já
perderam dinheiro e o blend reduziu o prejuízo principalmente ao reduzir
exposição/custos. Um modelo adicional não resolveria a falta de ofertas
rastreáveis. Nenhuma alternativa permaneceu ativa e nenhuma variante foi
escolhida pelo saldo.

## 2. Experimento e disponibilidade temporal

O [protocolo](PROTOCOL.md) foi salvo e teve seu SHA calculado antes da leitura
de novos valores de preço ou desempenho. Após conhecer apenas a estrutura
do export e as falhas da fonte pública, um [adendo de medição](MEASUREMENT_ADDENDUM.md)
fixou a medição descritiva da fronteira de preço, também antes dos valores.

Foi recuperado **um único export** do ZIP migrado, por nome exato e hash:
`projetos/brasileirao-predictor-sessoes/2026-09-07/price_strength_evaluation_2026-09-07/inputs/history.json`.
O insumo é o histórico Sofascore agregado utilizado em pesquisa encerrada.
O mapa e a documentação não o transformam em payload de uma casa. Os cálculos
selecionaram 2025 e descartaram labels; nenhuma previsão foi ajustada.

O registro oferece identidade, kickoff e vetores de odds, mas não oferece
bookmaker, estado da cotação, relógios de observação/disponibilidade/recebimento,
timeline de suspensão/revisões, referência independente nem capacidade aceita.
O kickoff do jogo **não é** o timestamp da odd. O hash da migração comprova
igualdade dos bytes transferidos, não autenticidade ou execução do preço.

O scanner existente `quotes.py` foi reutilizado, sem modificação. Todos os
380 registros de 2025 foram recusados sem preencher artificialmente campos.

## 3. Resultado econômico parcial

| Medida | Resultado |
| --- | ---: |
| Universo 2025 preservado | 380 partidas |
| Vetores 1X2 numericamente completos | 374 (98,42%) |
| Partidas sem vetor numérico completo | 6 |
| Pares de preços admitidos para execução | 0 |
| Oportunidades econômicas existentes | Não mensuráveis com esses dados |
| Abstenções | 380 |
| Apostas simuladas/total apostado | 0 / 0 u |
| Margem implícita positiva | 374 de 374 vetores completos |

Para cada vetor completo, a soma implícita é S e a referência **diagnóstica**
é `p_i = (1/odd_i)/S`. Ela não é probabilidade verdadeira nem referência de
outra casa. O cálculo nas próprias odds produz `1/S - 1`, negativo em todos
os 374 vetores: mediana **−5,41% antes de custos**. Isso é EV calculado a partir
das próprias odds, não ROI observado e não prejuízo liquidado.

O preço de empate com custo fixo c por unidade é `(1+c)/p_i`. Em relação à
odd do mesmo vetor, o aumento necessário é `S*(1+c)-1`.

| Custo adicional hipotético | Aumento de cotação necessário, mediana |
| --- | ---: |
| 0% | 5,72% |
| 1% | 6,77% |
| **2% — cenário fixado** | **7,83%** |
| 3% | 8,89% |
| 5% | 11,00% |

No cenário de 2%, o aumento necessário vai de **5,58% a 15,18%**; o percentil
90 é **9,10%**. O cálculo usa uma única fórmula previamente definida em todas
as partidas, sem selecionar casa, janela ou linha depois do resultado.
As medianas mensais variam de 7,63% a 9,23%; são descrições de preço, sem
inferência de vantagem ou extrapolação para renda. Março tem apenas cinco jogos.

**Não foi observada uma oferta 7,83% melhor.** Esse número apenas quantifica
uma condição de empate sob a referência diagnóstica e as fricções estipuladas.
Uma referência independente pode implicar outro preço de empate.

## 4. Contabilidade, comparadores e custos

A trilha executável só permite abstenção. Na carteira ilustrativa de 100 u:
banca inicial 100 u, final 100 u **antes de custos fixos desconhecidos**;
aportes, stakes, responsabilidade, capital preso, principal devolvido, prêmios,
custos variáveis de apostas e resultado de apostas são todos 0 u. Exposição
simultânea e retorno da banca antes de custos fixos são zero; ROI sobre stakes
é indefinido porque o denominador é zero. Nenhuma partida foi liquidada.

Isso coincide com o comparador de abstenção; não é desempenho de uma estratégia
apostadora. A margem embutida S e o custo adicional de 2% aparecem separados,
sem dupla contagem. Os 2% e a comissão zero são hipóteses de cenário.
Impostos, recusas, limite, liquidez, slippage, capacidade, manutenção e custo
fixo total permanecem desconhecidos. Nenhum serviço foi comprado ou API com
chave consumida. Não foi estimado lucro total de um negócio.

## 5. Tentativas de resolver o bloqueio externo

Foram feitas três requisições diretas, públicas, sem autenticação, com timeout
e recibos de horário: página Brasil, notas e CSV oficial de Football-Data.
Todas retornaram **HTTP 503**, entre 18:09 e 18:10 UTC. A tentativa pelo navegador
de pesquisa também retornou 503 para página e notas. Não houve bypass nem
mudança de fonte/casas para perseguir um resultado positivo.

- [Página Brasil](https://www.football-data.co.uk/brazil.php)
- [Dicionário de dados](https://www.football-data.co.uk/notes.txt)
- [CSV oficial tentado](https://www.football-data.co.uk/new/BRA.csv)

503 é uma falha de acesso nesta sessão, não demonstra que a fonte não tenha
dados nem que inexistam oportunidades. Não foi possível examinar seu esquema
nem realizar o replay condicional Bet365/Pinnacle previamente previsto.

A [documentação primária da The Odds API](https://the-odds-api.com/historical-odds-data/)
declara histórico disponível apenas em planos pagos e custo de 10 créditos
por região/mercado; declara cobertura histórica do Brasileirão e snapshots
de cinco minutos desde setembro de 2022. Esse documento foi consultado;
nenhum endpoint autenticado foi chamado. Plano efetivo do usuário, saldo,
reserva para coletores e autorização para consumir histórico não foram
comprovados. Cinco minutos de grade também não garantem simultaneidade de
30 segundos nem aceitação/liquidez de uma cotação.

## 6. Testes e limites estatísticos

- **80 testes passaram:** 30 novos casos de aritmética/admissão e 50 casos
  sintéticos do scanner existente. Cobrem devolução do principal, custo
  adicional, comissão só sobre lucro vencedor, sinais S<1/S=1/S>1, odds
  inválidas, identidade duplicada, conflito temporal, exclusão de 2026,
  independência da saída em relação a labels, auto-referência e suspensão.
- Conferência separada com Decimal de 45 dígitos: **1.870 relações verificadas**
  em 374 vetores, com 380 identidades reconciliadas. É uma implementação
  separada do mesmo pesquisador, não auditoria de outra equipe.
- Ruff/lint, formatação e Pyright direcionados passaram. Detalhes finais de
  validação e SHA estão nos recibos. Nenhum teste .NET/Redis/Compose foi
  necessário ou executado: a alteração é pesquisa Python offline, sem integração
  com o runtime. Os checks antigos não foram relaxados.
- A primeira tentativa de pytest foi bloqueada pelo isolamento de escrita
  ao tentar abrir seu log padrão fora da área de teste. O log foi direcionado
  para a área permitida; a trava foi preservada. Ajustes iniciais de formatação
  também foram concluídos, sem mudar os parâmetros econômicos.
- Uma configuração temporária de Pyright com caminhos absolutos em `include`
  foi ignorada pela ferramenta e a execução foi interrompida. A configuração
  corrigida usa caminhos relativos e inclui explicitamente os quatro fontes,
  inclusive o módulo de pesquisa que o projeto exclui da checagem padrão:
  quatro arquivos conferidos, zero erros/avisos de tipagem. A tentativa anterior
  não foi contabilizada como aprovação.

Não há apostas ou labels avaliados para calcular calibração, bootstrap de
retornos, concentração de acertos, CLV ou significância de lucro. O bootstrap
previsto dependia de um replay com apostas e não se aplica. Nenhum snapshot
foi contado como observação independente adicional. 2025 permanece exploratório.

## 7. Estado real do ambiente e preservação

- Diretório solicitado: `C:/BRASILEIRAO`. Inicialmente havia somente a migração.
- Código: bundle d42a3e0 recuperado após conferir hash; avanço direto para a
  main remota **f00304574044ab9d18aa3603abc538fbb3102c64**. Nenhum reset ou
  branch histórica foi recriada. O ZIP continua vinculado a d42a3e0.
- Ambiente instalado desta rodada: Python **3.13.12** e ferramentas isoladas
  em `C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv`. O Python empacotado
  do aplicativo era 3.12 e não foi usado para testes/execução científica.
  Core/Ops e a aplicação operacional completa não foram instalados.
- Dados: ZIP original preservado, sem restauração geral de bancos, credenciais,
  agendas ou ledgers. Só um export histórico foi extraído por allowlist e SHA.
- Operação: a consulta local não encontrou tarefas/processos correspondentes
  ao projeto. Isso não determina o estado do computador antigo. Nenhum serviço,
  coletor, banco, Redis ou agenda foi iniciado/alterado por esta rodada.
- Execução principal: ambiente sem credenciais, rede/subprocessos/SQLite
  bloqueados por audit hook, leitura de `data/` negada e escrita limitada a uma
  saída nova. H14/H15/H9/A1 não foram usados, avaliados ou promovidos.

## 8. Decisão e próxima informação

**Decisão:** encerrar a rodada com o bloqueio de proveniência demonstrado.
Não promover candidato, não ativar capital e não retunar xG. O limite se aplica
ao export auditado e às fontes acessíveis nesta sessão; não refuta o mecanismo
de divergência entre casas em todo o mercado.

**Descoberta que mais mudou a decisão:** cobertura de odds de 98,42% coexistiu
com zero pares admissíveis. Muitos números de preço não equivalem a uma oferta
utilizável; a fronteira mediana de 7,83% dá escala ao obstáculo sob o cenário.

**Hipótese que perdeu prioridade:** desenvolver/calibrar outro modelo xG antes
de demonstrar preço e execução. Nenhum resultado negativo anterior foi apagado.

**Informação que decide o próximo passo:** uma amostra independente e autorizada
de oferta e referência completas, com os clocks efetivos, revisão/suspensão,
identidades e condições de execução. Uma amostra válida pode desbloquear o
replay; não é evidência suficiente para afirmar lucro. Requisitos adicionais:
plano/cota/reserva de fonte comprovados e custo/capacidade de execução mensuráveis.
Uma captura prospectiva deverá excluir coortes protegidas e ter protocolo
próprio antes de coletar. Nenhuma coleta recorrente foi criada nesta sessão.

## Reprodução e hashes

Ver [REPRODUZIR.md](REPRODUZIR.md), `summary.json`, `manifest.json`,
`decimal-verification.json`, `validation.json` e `source_attempts.json` nesta pasta.
Os eventos individuais, o insumo privado e rejeições detalhadas permanecem em
`C:/BRASILEIRAO/work/price-feasibility-2026-09-09/`, fora do Git.

- ZIP original: `3860235c920fb0d6f7abfe916cf7ebdf5b1fa2a6e7679d7455bdf2d4fd415129`.
- Bundle original: `e278f2e2068d0ac821d22c9331d79adee492748bbeee5835c9c7bcff5a02f7aa`.
- Insumo: `14153f7cbb348e9eef22a8e1c438757b1ef482951e2576d4a8381d7928e8e142`.
- Protocolo: `f69d6aa1fbca0b64adabe0dd61cfddef409e3f47061c4baaedf9e203f46702e5`.
- Adendo pré-valores: `6ead15aaac9462f089469aaa80ac612ceefba6a06a9e4ed3d7599382ae6cb8ed`.
- Resultado agregado: `67d5eb3ae6f73801e247f59d9f29a1ce3e2eaa2aaf14d961ceb767a47ec93da3`.

Trabalho realizado por um único agente. Não houve aposta, movimentação financeira,
autenticação de casa, contratação de serviço ou publicação de dados privados.
