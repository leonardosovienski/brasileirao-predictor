# Handoff — OU2.5, auditoria 2024–2026 e rodada de 29–31/08/2026

Data de consolidação: 2026-08-28, horário de Brasília.

Este documento é o ponto de entrada canônico para continuar a investigação em
outra conversa. Ele separa deliberadamente três coisas que não podem ser
misturadas: validação do ledger retrospectivo, prova de executabilidade e teste
prospectivo com banca virtual.

## Veredito curto

O recorte retrospectivo mais interessante encontrado foi:

- mercado: Under 2.5 gols;
- EV do modelo mínimo: 15%;
- odd decimal: 1,80 a 2,40;
- stake contrafactual: 1 unidade por aposta.

A liquidação, a aritmética e a identidade dos 742 registros de 2024–2026 foram
revalidadas. O resultado retrospectivo é real **como ledger contrafactual**. Ele
não é ainda um ROI executável porque as odds históricas são agregadas e
classificadas como `POSTGAME_APPROXIMATION`, sem bookmaker e sem horário de
captura pré-jogo. Também não foi possível reproduzir, a partir dos dados brutos,
o estado point-in-time do modelo para cada linha.

Veredito formal:

`LEDGER_SETTLEMENT_AND_ARITHMETIC_REVALIDATED; PREDICTION_GENERATION_AND_ECONOMIC_EXECUTABILITY_NOT_REVALIDATED`

## O que foi validado em 2024–2026

- 742 linhas válidas e 742 `event_id` únicos;
- 2024: 149 registros precificados;
- 2025: 374 registros precificados;
- 2026: 219 registros precificados;
- nenhuma duplicação e nenhuma falha registrada;
- confronto por `event_id` com o estado atual da API do SofaScore;
- kickoff, rodada, placar, Under/Over, vitória, lucro, probabilidade no domínio
  válido e fórmula do EV recalculados;
- a resposta bruta da API consultada na auditoria não foi congelada. Portanto,
  a redação correta é “reconfirmado contra o estado atual da API”, e não
  “snapshot histórico imutável”.

Cobertura da fonte por temporada:

| Temporada | Jogos encerrados | Versões adiadas | Registros precificados |
|---|---:|---:|---:|
| 2024 | 380 | 8 | 149 |
| 2025 | 380 | 13 | 374 |
| 2026 até o corte | 235 | 9 | 219 |

## Resultado do recorte congelado

| Temporada/período | Apostas | Lucro | ROI | IC bootstrap 95% do ROI |
|---|---:|---:|---:|---:|
| 2024 completo | 75 | +10,65u | 14,20% | −10,47% a 38,90% |
| 2024 primeiro turno | 2 | +2,80u | 140,00% | inconclusivo, amostra mínima |
| 2024 segundo turno | 73 | +7,85u | 10,75% | −14,97% a 35,21% |
| 2025 completo | 159 | +37,60u | 23,65% | 5,91% a 41,21% |
| 2025 primeiro turno | 86 | +28,60u | 33,26% | 9,80% a 57,12% |
| 2025 segundo turno | 73 | +9,00u | 12,33% | −14,25% a 38,73% |
| 2026 completo | 73 | +5,625u | 7,71% | −17,26% a 32,19% |
| 2026 primeiro turno | 63 | +0,625u | 0,99% | −25,91% a 28,29% |
| 2026 segundo turno | 10 | +5,00u | 50,00% | inconclusivo, amostra pequena |

O corte dos turnos usa `roundInfo.round` do SofaScore: primeiro turno = rodadas
1–19; segundo turno = rodadas 20–38. Não se deve dividir o ledger pela posição
190, pois a ausência de preços em parte dos jogos desloca essa fronteira.

Conclusão estatística: 2025 é a única temporada cujo ROI completo e primeiro
turno apresentam limite inferior positivo nesse replay. 2024 e 2026 permanecem
compatíveis tanto com lucro quanto com prejuízo. O ROI de 140% de 2024/T1 vem de
somente duas apostas e não representa precisão.

## O que continua não validado

- que cada `model_probability` era exatamente a probabilidade disponível antes
  do respectivo kickoff;
- que cada ajuste usou somente partidas anteriores;
- que Elo, calibração e parâmetros correspondem ao estado histórico exato;
- bookmaker, origem e horário das odds históricas agregadas;
- possibilidade real de executar os preços retrospectivos;
- CLV contra o fechamento da mesma casa;
- ausência de seleção retrospectiva entre as 80 configurações investigadas;
- equivalência de decisões entre preço agregado pós-jogo e preços PIT nomeados.

O teste prospectivo deve exigir dois resultados separados: qualidade do sinal
(CLV médio e intervalo de confiança) e resultado econômico (ROI prospectivo e
intervalo de confiança), além de concentração por bookmaker, clube e rodada.

## Bancos e caminhos locais

### Banco atual do workspace operacional

`C:\Users\Superleo13\Documents\Codex\2026-08-28\a\brasileirao-predictor\data\matches.db`

- tamanho observado na consolidação: 147.456 bytes;
- SHA-256 observado: `0f5331ab14e2b19c59a2ff124e682680d3f51dce6271d6feda64f1ad55fe4aa3`;
- estado lógico: `matches=0` e `sofascore_matches=0`;
- não usar como fonte de ratings ou histórico.

Nota de proveniência: no início da auditoria esse arquivo tinha 106.496 bytes e
hash `1a717463...`. Durante uma tentativa de verificar o carregador, duas linhas
foram inseridas e imediatamente removidas; as contagens voltaram a zero, mas a
alocação física do SQLite mudou. Isso explica o tamanho e hash atuais. Nenhuma
linha histórica permaneceu no banco.

### Banco operacional de odds

`C:\Users\Superleo13\Documents\Codex\2026-08-28\a\brasileirao-predictor\data\odds_operational.db`

- tamanho observado: 40.960 bytes;
- SHA-256 observado: `08b440b92f5b34d4ca5d8f8e7d006209f4aee9b09532399e3cb714571b8434e6`;
- na última leitura havia 17 fatos;
- todos pertenciam a Atlético-MG × Vitória;
- havia 1X2 nomeado para Betano, Estrelabet, KTO, Pinnacle e Superbet;
- OU2.5 tinha somente o par Over/Under da Pinnacle.

Snapshots append-only:

`C:\Users\Superleo13\Documents\Codex\2026-08-28\a\brasileirao-predictor\data\odds_snapshots\2026-08-28.jsonl`

### Banco preservado usado no replay e na previsão preliminar

`C:\Users\Superleo13\Documents\Codex\2026-08-27\analise-o-reposit-rio-brasileirao-predictor\outputs\matches-db-operacional-8a3a2415\matches.db`

- tamanho: 49.508.352 bytes;
- SHA-256: `8a3a2415aab9b8525708ee18ee7b3fb360b40031904095f5c71b35871e5946cd`;
- acesso realizado em modo somente leitura;
- cache do modelo: 2.125 partidas;
- `config_hash`: `ce8783f131b544b6`;
- `computed_at`: `2026-08-24T05:39:16Z`;
- é o banco que corresponde ao estado documentado no replay anterior;
- a previsão de 28/08 é preliminar porque esse estado não incorpora
  integralmente os resultados posteriores ao corte.

### Clone criado durante a auditoria

`C:\Users\Superleo13\Documents\Codex\2026-08-28\oi-4\brasileirao-predictor`

Esse clone não contém os bancos operacionais/históricos não versionados. A
ausência de `data/matches.db` nele nunca deve ser interpretada como ausência de
dados em todos os workspaces do projeto.

## Teste da rodada de 29–31/08/2026

Estado criado: `PAPER_CAPITAL_TEST`.

- banca virtual: 100u;
- stake virtual fixa: 1u;
- exposição máxima da rodada: 10u;
- uma posição no máximo por jogo;
- dinheiro real: desativado;
- `capital_enabled=false`;
- não existe automação ou monitoração ativa; ela foi removida a pedido do
  usuário;
- acompanhamento futuro deve ser manual na nova conversa.

Os 10 jogos congelados são Atlético-MG × Vitória, São Paulo × Bragantino,
Vasco × Cruzeiro, Athletico-PR × Fluminense, Flamengo × Botafogo, Corinthians ×
Santos, Mirassol × Palmeiras, Grêmio × Chapecoense, Bahia × Internacional e
Remo × Coritiba.

Previsões preliminares produzidas em 28/08:

| Jogo | P(Under 2.5) |
|---|---:|
| Atlético-MG × Vitória | 53,87% |
| São Paulo × Bragantino | 56,11% |
| Vasco × Cruzeiro | 55,58% |
| Athletico-PR × Fluminense | 55,91% |
| Flamengo × Botafogo | 51,46% |
| Corinthians × Santos | 54,06% |
| Mirassol × Palmeiras | 55,26% |
| Grêmio × Chapecoense | 50,62% |
| Bahia × Internacional | 54,50% |
| Remo × Coritiba | 55,81% |

Somente Atlético-MG × Vitória tinha odd OU2.5 nomeada: Pinnacle Under 2.5 a
1,781, capturada em `2026-08-28T21:34:24.216024Z`. O EV foi −4,05% e a odd
também ficou abaixo da banda congelada. Decisão preliminar: `NO_BET`. Os outros
nove jogos estavam sem cotação Under 2.5 nomeada. Resultado da execução de hoje:
zero candidatos e exposição virtual de 0u.

## Artefatos versionados

- contrato do candidato: `contracts/ou25-under-high-ev-prospective-2026.json`;
- contrato da rodada: `contracts/ou25-paper-capital-round-2026-08-29.json`;
- validação histórica: `reports/ou25_paper_capital_2026_08_29/historical_validation_2024_2026.json`;
- auditoria jogo a jogo: `reports/ou25_paper_capital_2026_08_29/historical_game_audit_2024_2026.jsonl`;
- recorte por turno: `reports/ou25_paper_capital_2026_08_29/historical_turn_split_2024_2026.json`;
- ledger inicial da rodada: `reports/ou25_paper_capital_2026_08_29/initial_round_ledger.jsonl`;
- previsões preliminares: `reports/ou25_paper_capital_2026_08_29/preliminary_predictions_2026_08_28.json`.

## Procedimento para a nova conversa

1. Ler este handoff e os dois contratos antes de qualquer decisão.
2. Não alterar parâmetros após observar odds ou resultados.
3. Ler o banco de odds e os snapshots somente em modo leitura.
4. Para cada jogo, exigir probabilidade criada antes do kickoff, bookmaker
   nomeado, Under 2.5 entre 1,80 e 2,40 e EV mínimo de 15%.
5. Se qualquer requisito faltar, registrar `NO_BET` com motivo.
6. Se houver candidato, registrar apenas `PAPER_BET`; não executar aposta real.
7. Preservar o fechamento da mesma casa para calcular CLV.
8. Após os jogos, liquidar o ledger e reportar separadamente ROI, CLV, saldo,
   drawdown e concentração.

## Encerramento das execuções automáticas

Após a consolidação inicial, todas as tarefas do Agendador do Windows cujo nome
começa por `brasileirao-` foram interrompidas e desativadas por solicitação
explícita do usuário. Verificação final em 2026-08-28:

- tarefas do projeto encontradas: 25;
- tarefas em estado `Disabled`: 25;
- tarefas em outro estado: 0;
- processos relacionados ao projeto em execução: 0.

Foram incluídas nessa paralisação as famílias A1 (`collect`, `discover` e
`metrics`), H8, H9 (`backup`, `closing`, `emit`, `missed-window`, `settle` e
variantes), captura de lineup, snapshots de fechamento, pesquisa de mercado,
readiness prospectivo e atualização de modelos. Cinco tarefas H9 exigiram
elevação administrativa para serem desativadas; a verificação posterior
confirmou que todas ficaram desativadas.

Essa é uma alteração operacional do Agendador do Windows e, portanto, não é
representada pelo Git. Este registro documenta o estado observado. Reativação
futura deve ser explícita, seletiva e acompanhada de nova conferência das
credenciais, caminhos e contratos antes da primeira execução.
