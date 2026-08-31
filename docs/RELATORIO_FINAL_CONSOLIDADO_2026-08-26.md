# Relatório final consolidado — brasileirao-predictor

> **SUPERSEDIDO PARA MÉTRICAS — 2026-08-26:** uma auditoria posterior encontrou
> diferenças entre a likelihood e a grade servida, decay terminal ausente no
> Elo e climatologia com informação da própria coorte. O código foi corrigido;
> os números e o ledger abaixo preservam o estado histórico do commit-base e
> não devem ser reutilizados como estado corrente. Ver
> `docs/AUDITORIA_MATEMATICA_E_CORRECOES_2026-08-26.md`.

Data: **2026-08-26**  
Commit-base analisado: `915b5c6`  
Escopo: ciência preditiva, erros, mercados, dados, governança e integridade.

## 1. Veredito em uma página

O projeto está **saudável como software e como processo científico**, mas o
modelo atual **não demonstrou vantagem econômica pré-jogo**.

O predictor aprende a direção geral da força e reconhece bem vitórias claras de
mandantes. Seu erro dominante é estável entre temporadas: atribui o maior valor
1X2 à casa em aproximadamente 78%–85% dos jogos, nunca atribui o argmax ao
empate e perde muitas vitórias visitantes/empates como vitória da casa.

Isso não equivale a “probabilidade de empate zero”. De 2021 a 2025, a média de
`p_draw` acompanhou razoavelmente a frequência real; o problema era a ordenação
entre três classes. Em 2026 surgiu também subestimação marginal de empate de
4,76 pontos percentuais.

O mercado agregado foi melhor em RPS, Brier e log loss no painel 2021–2024. A
maior diferença aparece nos jogos em que o modelo tem confiança máxima abaixo
de 40%; acima de 60%, modelo e mercado ficaram praticamente iguais. A leitura
mais consistente é que a arquitetura captura força estável, mas carece de
informação PIT para jogos ambíguos e mudanças rápidas de regime.

Estado econômico:

- pré-jogo 1X2: **NO-GO**;
- OU2.5: **arquivado na formulação atual**;
- BTTS: **NO-GO estrutural**;
- live: **HOLD sem viabilidade comprovada**;
- coletor Pinnacle × soft: **único caminho principal ainda vivo**, mas Gate A1
  ainda `NOT_STARTED`;
- capital: **LOCKED**.

## 2. Dados efetivamente disponíveis

O SQLite operacional local é `data/matches.db`, fora do Git.

Inventário confirmado:

- tamanho: 49.508.352 bytes;
- SHA-256 observado: `8A3A2415AAB9B8525708EE18EE7B3FB360B40031904095F5C71B35871E5946CD`;
- `PRAGMA integrity_check`: `ok`;
- `matches`: 2.281 linhas;
- jogos encerrados: 2.125;
- `sofascore_matches`: 2.321;
- `match_statistics`: 439.764;
- `odds_lines`: 17.820;
- `odds_snapshots`: 25.142;
- `sofascore_player_ratings`: 65.733;
- `player_comp_stats`: 5.210.

Jogos encerrados originalmente validados por temporada:

| Ano | Jogos |
|---|---:|
| 2021 | 380 |
| 2022 | 380 |
| 2023 | 380 |
| 2024 | 380 |
| 2025 | 380 |
| 2026 | 225 |

Os 940 casos de desenvolvimento não são a quantidade bruta do banco: são 1.140
jogos de 2021–2023 menos burn-in walk-forward de 200 partidas.

## 3. Arquitetura avaliada

O núcleo transforma diferença Elo em intensidades de gols:

```text
Δ = força_casa − força_fora, com a política de mando
λ_casa = exp(a + b·Δ + correções habilitadas)
λ_fora = exp(a − b·Δ + correções habilitadas)
```

Depois aplica distribuição de gols e correção Dixon–Coles para gerar uma grade
de placares e probabilidades 1X2/OU/BTTS.

Configuração relevante:

- `goal_half_life_days = null` no incumbent: ajuste de gols com pesos uniformes;
- Elo é a representação principal de força relativa;
- ensemble xG está desligado: H12 comprovou que desligá-lo melhorou RPS;
- H9 frozen combina parâmetros congelados com Elo `as-of`;
- pesquisa é read-only e não usa `current_elo` futuro;
- o modelo não observa de forma PIT escalação, lesões, técnico, estádio, viagem,
  notícias ou quebras de elenco.

Limitação algébrica relevante:

```text
λ_total ≈ 2·exp(a)·cosh(b·Δ)
```

Isso comprime totais esperados e mercados derivados quando a única informação
específica do jogo é essencialmente `ΔElo`.

## 4. Qualidade preditiva global

### Desenvolvimento 2021–2023

| Métrica | Valor |
|---|---:|
| n após burn-in | 940 |
| RPS | 0,210630303919 |
| Brier 1X2 | 0,617282407778 |
| log loss | 1,029720411841 |
| accuracy | 47,1277% |

Esses valores são agregação diagnóstica. O relatório canônico `h9_frozen`
falhou ao aplicar bootstrap móvel de bloco 21 ao estrato `2021-T2` com `n=7`.
Não havia referência anterior completa para atestar identidade a `1e-6`.

### 2025, aberto por solicitação explícita

| Métrica | Valor |
|---|---:|
| n | 380 |
| RPS | 0,205338977462 |
| Brier 1X2 | 0,602207342857 |
| log loss | 1,006240088511 |
| accuracy | 50,2632% |

2025 deixou de ser holdout cego em 2026-08-26. O processamento foi walk-forward
com regra congelada, sem tuning, mas o ano não pode mais sustentar alegação
confirmatória futura.

### 2026 disponível

| Métrica | Valor |
|---|---:|
| n | 225 |
| RPS | 0,208918433078 |
| Brier 1X2 | 0,630818694126 |
| log loss | 1,044540692917 |
| accuracy | 47,1111% |

O nível geral de accuracy/RPS não colapsou versus o desenvolvimento. O ponto
anormal é o trecho T2 ainda pequeno.

## 5. Assinatura histórica dos erros

| Ano | n | Accuracy | Argmax casa | Argmax empate | Recall fora | Recall empate | Recall casa | “Não casa → casa” entre erros |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 180 | 52,78% | 85,00% | 0,00% | 18,75% | 0,00% | 89,90% | 75,29% |
| 2022 | 380 | 46,32% | 85,26% | 0,00% | 19,23% | 0,00% | 92,86% | 82,35% |
| 2023 | 380 | 45,26% | 80,00% | 0,00% | 22,12% | 0,00% | 83,71% | 74,52% |
| 2024 | 380 | 48,68% | 81,05% | 0,00% | 29,29% | 0,00% | 86,67% | 77,95% |
| 2025 | 380 | 50,26% | 79,47% | 0,00% | 28,89% | 0,00% | 86,39% | 72,49% |
| 2026 | 225 | 47,11% | 77,78% | 0,00% | 33,93% | 0,00% | 85,29% | 73,95% |

Conclusões:

1. O padrão de 2026 não é acidente: aparece em todos os anos.
2. Há melhora gradual no recall de visitante e queda no argmax casa, mas a
   assimetria continua grande.
3. O modelo reconhece vitórias de mandante muito melhor que vitórias fora.
4. Empate nunca vence o argmax, embora receba probabilidade material.
5. Trocar automaticamente previsões laterais por empate já foi investigado e
   não ganhou: em 2021–2024, nos 528 casos “argmax lateral + placar modal
   empatado”, o lado acertou 39,58% e escolher sempre empate acertaria 29,73%.

### Matriz 2026

| Real \ previsto | Fora | Empate | Casa |
|---|---:|---:|---:|
| Fora | 19 | 0 | 37 |
| Empate | 16 | 0 | 51 |
| Casa | 15 | 0 | 87 |

Dos 119 erros: 51 foram empate→casa, 37 fora→casa, 16 empate→fora e 15
casa→fora. Portanto 88/119, ou 73,95%, foram resultados não vencidos pelo
mandante chamados de vitória da casa.

### Matriz 2025

| Real \ previsto | Fora | Empate | Casa |
|---|---:|---:|---:|
| Fora | 26 | 0 | 64 |
| Empate | 26 | 0 | 73 |
| Casa | 26 | 0 | 165 |

Em 2025, 137/189 erros (72,49%) tiveram o mesmo sentido.

## 6. Empate: argmax não é calibração

| Ano | `p_draw` médio | Empate real | Previsto − real |
|---|---:|---:|---:|
| 2021 | 30,04% | 27,22% | +2,81 pp |
| 2022 | 27,80% | 28,42% | −0,62 pp |
| 2023 | 26,47% | 25,79% | +0,68 pp |
| 2024 | 26,41% | 26,58% | −0,17 pp |
| 2025 | 26,01% | 26,05% | −0,05 pp |
| 2026 | 25,02% | 29,78% | **−4,76 pp** |

Até 2025, calibração marginal e argmax contam histórias diferentes: a média de
empate estava próxima do observado, mas nunca era a maior classe individual.
Em 2026, a distribuição continuou comprimida e também ficou baixa em média.

Reliability 2026:

| Faixa | n | `p_draw` médio | Empate real |
|---|---:|---:|---:|
| 10–20% | 16 | 18,10% | 31,25% |
| 20–30% | 209 | 25,55% | 29,67% |

A faixa de 16 jogos é pequena. Nenhum threshold deve ser criado com base nela.

## 7. T2-2026: anormalidade sem drift confirmado

- T1: `n=190`, accuracy 50,53%, RPS 0,209379, Brier 0,614523,
  log loss 1,022213;
- T2: `n=35`, accuracy 28,57% (10/35), RPS 0,206417, Brier 0,719284,
  log loss 1,165747;
- intervalo preditivo binomial 95% sob `p=0,50`: 12–23 acertos;
- 10 acertos fica fora do intervalo.

| Lado | λ médio | Gol real médio | λ − real | IC95 |
|---|---:|---:|---:|---:|
| Casa | 1,4532 | 1,1429 | +0,3104 | [−0,0360; +0,6567] |
| Fora | 1,0340 | 1,1143 | −0,0803 | [−0,3839; +0,2233] |

Como ambos os ICs incluem zero, o veredito permanece
`RESULT_NOISE_NOT_PARAMETER_DRIFT`. Isso não prova ausência de drift; significa
que a amostra atual não separa drift marginal de ruído de conversão de placar.

## 8. Clubes com maior lead causal já documentado

| Clube | Jogos | Erros | Erro em casa | Erro fora |
|---|---:|---:|---:|---:|
| Internacional | 23 | 16 | 75,00% | 63,64% |
| Bahia | 23 | 16 | 58,33% | 81,82% |

O excesso nos dois papéis é incompatível com explicação puramente de mando. É
consistente com força desatualizada, mas não prova qual evento causou a quebra.
Elenco, técnico e momento não estão disponíveis como features PIT. `city` está
vazio e não pode ser usado para inferir estádio.

## 9. Modelo contra mercado

Agregado SofaScore, sem bookmaker nomeado, somente diagnóstico:

| Temporada | n | RPS modelo | RPS mercado | Modelo − mercado |
|---|---:|---:|---:|---:|
| 2021 | 180 | 0,204551 | 0,189191 | +0,015360 |
| 2022 | 380 | 0,210715 | 0,203368 | +0,007347 |
| 2023 | 380 | 0,218833 | 0,210820 | +0,008013 |
| 2024 | 378 | 0,214532 | 0,198260 | +0,016272 |
| Total | 1.318 | 0,213309 | 0,202115 | **+0,011193** |

Por confiança máxima:

| Confiança | n | RPS modelo − mercado |
|---|---:|---:|
| <40% | 318 | +0,016625 |
| 40–50% | 594 | +0,012325 |
| 50–60% | 299 | +0,007296 |
| ≥60% | 107 | −0,000343 |

O mercado adiciona mais informação onde o modelo está indeciso. O prêmio total
de 0,011193 RPS é pequeno para justificar sozinho uma reconstrução cara de
features; é alvo máximo observado, não promessa de capturabilidade.

## 10. Mercados derivados

### OU2.5

- desenvolvimento: `n=940` previsões e 808 com odds completas;
- média 39,85%, desvio-padrão 2,69 pp;
- passou resolução mínima;
- divergência contra mercado não teve ROI monotônico sob Shin nem power;
- células positivas extremas tinham `n=3` ou `n=5` e nenhum poder;
- MDE aproximada em 380 jogos a odd 1,90: 13,67% ROI;
- veredito: `ARCHIVE_OU25_CURRENT_RESIDUAL`.

### BTTS

- `n=940`, 809 com odds completas;
- média 44,19%, desvio-padrão 1,29 pp;
- threshold de resolução: 2 pp;
- veredito: `NO_GO_LOW_MODEL_RESOLUTION`.

## 11. Ledger científico

`data/trials.json` contém agora 29 nomes únicos, todos com status. As grafias
`substituida`/`substituída` são a mesma categoria:

| Status | Quantidade |
|---|---:|
| Refutada | 6 |
| Informativa | 3 |
| Substituída | 3 |
| Inconclusiva | 6 |
| Exploratória | 2 |
| Comprovada | 1 |
| Pré-registrada | 8 |

A única trial com status histórico `comprovada` é H12: desligar o ensemble xG
melhorou a qualidade no painel reutilizado. A decisão operacional permanece,
mas a confirmação não foi cega e isso não prova edge econômico. H13 foi
substituída; H14 e H15 estão pré-registradas, porém a persistência prospectiva
dos braços ainda está `NOT_STARTED`.

Famílias fechadas na formulação atual: divergência 1X2, OU2.5 residual, BTTS,
recalibrações simples, mando/força/temperatura escalares, `rho`, ataque-defesa
simples e ensemble xG ligado.

## 12. Coletor A1 e caminho econômico

A PoC OddsPapi encontrou no mesmo evento Pinnacle e quatro softs BR com 1X2:
Betano BR, EstrelaBet, Superbet BR e KTO. Sportingbet apareceu sem mercado 101;
Pixbet não apareceu.

Estado operacional real:

| Item | Estado |
|---|---|
| Dias de shadow | 0 |
| Snapshots diários | 0 |
| Requests registrados | 0/245 |
| Quarentenas | 0 |
| Hash-chains | N/A, nenhum arquivo |
| Gate | `NOT_STARTED` |
| `homologated` | false |
| Capital | bloqueado |

O modo econômico foi orçado em 245 requests/mês, mas é `REHEARSAL_ONLY` e não
consegue provar a continuidade do gate formal. O próximo avanço econômico exige
sete dias reais, cinco ou mais softs + referência, coverage, identidade,
conflitos, hash-chain e auditoria humana de 50 eventos.

A chave OddsPapi anteriormente colada em chat deve ser considerada exposta. Ela
não deve ser persistida nem reutilizada; apenas uma chave rotacionada deve ser
configurada em `ODDSPAPI_KEY`.

## 13. Qualidade de software e operação

Bateria final do commit anterior:

- 752 testes Python aprovados;
- Python 3.13 e 3.14 aprovados no GitHub CI;
- Ruff e `ruff format --check`: verdes;
- Pyright: 0 erros e 0 warnings;
- pacote wheel/sdist e instalação isolada: aprovados;
- .NET 10: build/test aprovados, cobertura mínima de linhas e branches ≥80%;
- Compose: build, health, Redis, perda/reconexão e shutdown gracioso aprovados;
- `ci_check.py`: 5/5, incluindo anti-lookahead e smokes pré-jogo/live;
- probabilidades dos três smokes somaram 100%;
- worktree permaneceu limpo após a bateria.

Cobertura deve ser nomeada corretamente:

- cobertura global por statements na execução local/CI: **47%**, piso 45%;
- relatório branch-aware consolidado: **37,65% global**;
- runtime homologado branch-aware: **81,25%**;
- Worker .NET: **85,15% linhas / 80,92% branches**.

A cobertura baixa em pesquisa/legado não invalida o runtime homologado, mas é
dívida real e não deve ser apresentada como “81% do projeto inteiro”.

## 14. Incidentes, desvios e informações stale

1. O primeiro push falhou no CI porque três arquivos não estavam formatados. O
   commit `1544dbe` corrigiu e o CI seguinte ficou verde.
2. O teste .NET local falhou sem Redis/Docker Desktop; o mesmo commit passou no
   CI com Redis provisionado. Foi falha ambiental, não funcional.
3. O painel `h9_frozen` tinha bug de relatório para estratos menores que o bloco
   de bootstrap. A política agora retorna IC nulo nesses estratos e o artefato
   canônico corrigido foi concluído em
   `reports/benchmark_h9_frozen_corrected_2021_2024_2026-08-26.json`. O resultado
   desse painel é somente diagnóstico retrospectivo: os parâmetros congelados
   de H9 descendem do H8 já observado e não foram escolhidos cegamente antes de
   2021–2024; portanto, a vantagem histórica não confirma H9 nem autoriza capital.
4. A afirmação antiga “shadow A1 ativo” não corresponde ao disco: não há
   manifesto, snapshots, métricas ou tarefas instaladas.
5. Checkpoints antigos do `HANDOFF.md` preservam história e podem dizer que 2025
   está selado. O checkpoint superior de 2026-08-26 supersede essa condição.
6. Relatórios antigos da Copa/seleções não são evidência do Brasileirão.

## 15. Cadeia causal mais defensável

```text
força resumida principalmente por Elo + mando global
        ↓
baixa reatividade a mudança de elenco/técnico e pouca informação específica
        ↓
λ_casa frequentemente permanece acima de λ_fora em jogos ambíguos
        ↓
argmax casa em 78%–85% e empate nunca argmax
        ↓
boa captura de vitórias claras da casa, baixa captura de visitante/empate
        ↓
mercado vence sobretudo quando a confiança do modelo é baixa
```

Demonstrado: as frequências, matrizes, compressão e vantagem do mercado.

Inferido: que a causa dominante da informação ausente seja elenco/técnico/
escalação. É plausível e compatível com Inter/Bahia, mas ainda não isolada.

Não demonstrado: que adicionar qualquer feature específica produzirá edge ou
que exista um threshold rentável escondido.

## 16. O que ainda falta saber

1. Ranking completo de erro por clube e estabilidade entre temporadas, com
   correção por dificuldade do calendário.
2. Calibration slope/intercept 1X2 por temporada e ICs, além da média de empate.
3. Distribuição da margem entre primeira e segunda classe para quantificar quão
   frágeis são os argmax laterais.
4. Decomposição de Brier em calibração, resolução e incerteza por classe.
5. Features PIT auditáveis de escalação, lesões, técnico, venue, descanso e
   viagem; atualmente não existem com clocks/proveniência suficientes.
6. Odds nomeadas e sincronizadas de Pinnacle + softs, sem agregado anônimo.
7. Evidência prospectiva futura para H14/H15; 2025 não serve mais e a coleta
   dos braços ainda precisa ser ativada antes de qualquer observação elegível.
8. Amostra maior de T2-2026 para reavaliar ruído versus drift.

Esses itens são lacunas, não autorização automática para experimentos. Cada
hipótese nova precisa de protocolo, mecanismo e amostra futura legítima.

## 17. Recomendações finais

1. Não tentar “consertar” o argmax com threshold de empate pós-hoc.
2. Preservar o modelo atual como baseline congelado, não como motor econômico.
3. Preservar o fix do relatório `h9_frozen`: estrato menor que `block_length`
   recebe IC nulo em vez de derrubar o artefato inteiro.
4. Rotacionar a chave OddsPapi e iniciar o A1 somente com segredo ambiental.
5. Priorizar o coletor Pinnacle × soft, porque testa um mecanismo econômico que
   não depende de o modelo vencer o mercado em probabilidade pura.
6. Se houver nova pesquisa de modelo, exigir informação PIT nova e um futuro
   realmente cego; não usar 2024/2025 para seleção.
7. Tratar 2026 como monitoramento diagnóstico, não como laboratório de tuning.

## 18. Pacote para revisão por outras IAs

Compartilhar:

```text
docs/RELATORIO_FINAL_CONSOLIDADO_2026-08-26.md
docs/DOSSIE_ANALISE_PREDICTOR_2026-08-26.md
docs/RELATORIO_RETESTE_2026-08-24.md
docs/RELATORIO_DIAGNOSTICOS_RESIDUAIS_2026-08-24.md
docs/RELATORIO_SESSAO_0B_2026-08-24.md
docs/PROJECT_LOGIC_REGISTER.md
docs/DATA_MAP.md
docs/COVERAGE.md
data/trials.json
brasileirao_predictor/model.py
brasileirao_predictor/serving_evaluator.py
brasileirao_scripts/benchmark_predictor.py
```

Não compartilhar `.env`, chave OddsPapi ou banco operacional sem decisão
explícita.

Prompt recomendado:

```text
Audite o relatório anexado como revisor científico adversarial. Separe fatos,
inferências e hipóteses; procure leakage, múltiplas tentativas, condicionamento
retrospectivo, métricas inadequadas e explicações alternativas. 2025 já foi
consumido e não é holdout. Não proponha picks, stakes ou thresholds pós-hoc.
Não ressuscite hipótese refutada sem mecanismo ou informação PIT nova. Entregue
críticas priorizadas, testes falsificáveis read-only, dados PIT necessários e
um desenho prospectivo que preserve uma amostra realmente futura.
```

## 19. Conclusão

O predictor não está quebrado: ele faz de forma consistente o que sua
informação permite. O problema é que essa informação produz uma distribuição
pouco resolvida para separar casa, empate e visitante em jogos ambíguos. O
mercado possui vantagem justamente nessa região.

O resultado científico útil não é “apostar ao contrário” nem “forçar empate”. É
o mapa preciso da fronteira:

- software: verde;
- probabilidades: úteis como baseline, com assimetria conhecida;
- edge pré-jogo: não demonstrado;
- dados contextuais PIT: ausentes;
- 2025: consumido;
- A1: ainda não iniciado;
- próximo mecanismo testável: Pinnacle × soft em shadow auditável.
