# Dossiê técnico do predictor: onde acerta, onde erra e por quê

Data de consolidação: **2026-08-26**. Projeto: `brasileirao-predictor`.

Este documento foi preparado para revisão independente por outras IAs ou
pesquisadores. Ele consolida somente evidência já registrada. Não abre uma nova
trial, não procura threshold, não treina modelo e não reavalia holdouts.

## 1. Resumo executivo

O predictor está tecnicamente íntegro, reproduzível e protegido contra vários
tipos de vazamento temporal. Seu principal problema não é uma falha de código:
é **resolução informacional insuficiente**.

O motor transforma essencialmente uma diferença de força Elo em gols esperados
para casa e fora e então em probabilidades de placar/mercado. Isso funciona para
capturar a direção geral de força e mando, mas reage lentamente a mudanças de
elenco/forma e não observa escalação, lesões, técnico, estádio, contexto ou
notícias PIT. O mercado observa parte dessa informação.

Consequências observadas:

- o modelo acerta bastante quando a vitória do mandante é clara;
- confunde muitos empates e vitórias visitantes com vitória da casa;
- nunca escolheu empate por `argmax` nos 225 jogos de 2026 analisados;
- isso **não** significa probabilidade de empate zero: `p_draw` médio foi 25,02%,
  contra 29,78% de empates reais;
- a maior desvantagem contra o mercado aparece quando a confiança máxima do
  modelo é menor que 40%;
- acima de 60% de confiança, modelo e mercado ficaram praticamente empatados;
- BTTS é estruturalmente comprimido; OU2.5 varia mais, mas a divergência contra
  o mercado não ordenou retorno no desenvolvimento;
- Internacional e Bahia foram candidatos claros a força desatualizada em 2026,
  com erro alto tanto em casa quanto fora.

Veredito vigente: **nenhum edge econômico pré-jogo foi demonstrado**. O modelo
pode ser um baseline ou componente auxiliar, mas não há autorização científica
para picks, stakes ou capital.

## 2. O que exatamente é o modelo

O serving usa Elo e um modelo de gols com parâmetros `(a, b, alpha, rho)`.
Simplificando a parte central:

```text
Δ = força_casa − força_fora, incluindo a política de mando/Elo
λ_casa = exp(a + b·Δ + correções habilitadas)
λ_fora = exp(a − b·Δ + correções habilitadas)
```

Uma distribuição de gols (Binomial Negativa) e a correção Dixon–Coles para
placares baixos transformam os lambdas em uma grade de placares. A grade gera
1X2, OU2.5, BTTS e outros mercados.

No incumbent atual:

- `goal_half_life_days = null`: pesos uniformes no ajuste de gols;
- o Elo continua sendo o resumo principal da força relativa;
- o ensemble xG foi desligado após a governança anterior;
- H9 frozen usa parâmetros congelados e Elo disponível no instante correto;
- pesquisa histórica usa estado `as-of`, não `current_elo` futuro.

O desenho implica uma restrição importante:

```text
λ_total = λ_casa + λ_fora ≈ 2·exp(a)·cosh(b·Δ)
```

Logo, o total esperado varia pouco quando `Δ` está perto de zero e o modelo não
possui features externas que mudem o ritmo esperado de uma partida específica.

## 3. Qualidade global registrada

### Desenvolvimento 2021–2023

Após burn-in de 200 jogos, existem 940 previsões walk-forward. Uma agregação
auxiliar das linhas do evaluator produziu:

| Métrica | Valor |
|---|---:|
| n | 940 |
| RPS | 0,210630303919 |
| Brier 1X2 | 0,617282407778 |
| log loss | 1,029720411841 |
| accuracy | 47,1277% |

Ressalva: o painel canônico `h9_frozen` não concluiu o relatório por tentar
bootstrap móvel de bloco 21 em `2021-T2`, que tem apenas 7 observações após o
burn-in. Não existe baseline `h9_frozen` anterior das quatro métricas contra o
qual aplicar identidade de `1e-6`. Os números acima são diagnóstico auxiliar,
não uma nova régua promovida.

### Diagnóstico 2026

Base observada até 2026-08-17:

| Métrica | Valor |
|---|---:|
| n | 225 |
| RPS | 0,208918433078 |
| Brier 1X2 | 0,630818694126 |
| log loss | 1,044540692917 |
| accuracy | 47,1111% |

As métricas são praticamente iguais às globais de desenvolvimento em accuracy
e RPS. O problema de T2-2026 é localizado e ainda tem amostra pequena.

### Comparação com o mercado, 2021–2024

O “mercado” abaixo é o agregado sem casa nomeada do SofaScore, tratado apenas
como diagnóstico, nunca como preço executável ou evidência de lucro.

| Temporada | n | RPS modelo | RPS mercado | modelo − mercado |
|---|---:|---:|---:|---:|
| 2021 | 180 | 0,204551 | 0,189191 | +0,015360 |
| 2022 | 380 | 0,210715 | 0,203368 | +0,007347 |
| 2023 | 380 | 0,218833 | 0,210820 | +0,008013 |
| 2024 | 378 | 0,214532 | 0,198260 | +0,016272 |
| Total | 1.318 | 0,213309 | 0,202115 | **+0,011193** |

Em RPS, menor é melhor. Portanto o mercado foi melhor por 0,011193 no total.
Também foi melhor por 0,023398 em Brier e 0,034366 em log loss.

## 4. O que o modelo acerta e erra em 2026

Matriz de confusão, com linhas como resultado real e colunas como classe de
maior probabilidade (`argmax`):

| Real \ previsto | Fora | Empate | Casa | Total real | Recall |
|---|---:|---:|---:|---:|---:|
| Fora | 19 | 0 | 37 | 56 | **33,9%** |
| Empate | 16 | 0 | 51 | 67 | **0,0%** |
| Casa | 15 | 0 | 87 | 102 | **85,3%** |

Visão pela classe escolhida:

| Classe prevista | Quantidade | Acertos | Precisão da classe |
|---|---:|---:|---:|
| Fora | 50 | 19 | 38,0% |
| Empate | 0 | 0 | N/A |
| Casa | 175 | 87 | 49,7% |

Dos 119 erros totais:

- 51 foram empates classificados como vitória da casa (**42,9% dos erros**);
- 37 foram vitórias visitantes classificadas como vitória da casa (**31,1%**);
- 16 foram empates classificados como vitória visitante (**13,4%**);
- 15 foram vitórias da casa classificadas como vitória visitante (**12,6%**).

Assim, **74,0% dos erros foram jogos não vencidos pelo mandante que o modelo
classificou como vitória da casa**.

### Interpretação correta do “nunca prevê empate”

O modelo atribui probabilidade a empate, mas ela nunca foi a maior das três em
2026. Isso pode ocorrer mesmo em um modelo probabilístico razoável: empates são
uma classe individual frequente, porém vitória da casa ou fora pode continuar
sendo ligeiramente mais provável em cada jogo.

Por isso:

- accuracy/argmax mostra uma incapacidade de **selecionar empate como classe**;
- RPS, Brier e log loss avaliam a distribuição inteira e são métricas mais
  informativas para um predictor probabilístico;
- forçar empate por threshold depois de observar os resultados seria tuning
  pós-hoc e não é uma correção válida.

## 5. Empates e calibração

Em 2026:

- `p_draw` médio: **25,0218%**;
- taxa real de empates: **29,7778%**;
- gap marginal: modelo subestima em aproximadamente **4,76 pontos percentuais**.

Reliability em faixas congeladas:

| Faixa de `p_draw` | n | `p_draw` médio | empate real | gap real − previsto |
|---|---:|---:|---:|---:|
| 10–20% | 16 | 18,0958% | 31,2500% | +13,1542 pp |
| 20–30% | 209 | 25,5521% | 29,6651% | +4,1130 pp |

Não houve observações nas outras faixas. A primeira faixa tem apenas 16 jogos;
o gap grande é sugestivo, não conclusão robusta. O achado mais seguro é que a
distribuição de `p_draw` está comprimida: 92,9% dos jogos caíram em 20–30%.

## 6. Lambdas: o modelo erra gols ou conversão em resultado?

### Por resultado real em 2026

| Resultado real | n | λ casa | gols casa | λ fora | gols fora |
|---|---:|---:|---:|---:|---:|
| Vitória fora | 56 | 1,3175 | 0,5179 | 1,1352 | 2,1429 |
| Empate | 67 | 1,4428 | 1,1194 | 1,0435 | 1,1194 |
| Vitória casa | 102 | 1,4994 | 2,2255 | 0,9900 | 0,5882 |

Esta tabela é condicionada ao resultado realizado e não deve ser lida como
calibração causal. Ainda assim, ela mostra o mecanismo dos erros:

- em vitórias visitantes, o modelo esperava mais gols da casa que do visitante;
- em vitórias da casa, a direção média estava correta;
- em empates, os gols reais foram equilibrados, mas os lambdas ainda favoreciam
  a casa.

### T2-2026: drift ou ruído

| Marginal | λ médio | gols médios | λ − real | IC95 pareado |
|---|---:|---:|---:|---:|
| Casa | 1,4532 | 1,1429 | +0,3104 | [−0,0360; +0,6567] |
| Fora | 1,0340 | 1,1143 | −0,0803 | [−0,3839; +0,2233] |

T2 teve `n=35`, 10 acertos e accuracy 28,57%. Sob `Binomial(35, 0,50)`, o
intervalo preditivo de 95% é 12–23 acertos; 10 é incomum. Porém ambos os ICs
dos erros marginais de lambda incluem zero. O veredito registrado permanece:

**`RESULT_NOISE_NOT_PARAMETER_DRIFT`**.

Em linguagem simples: os placares transformaram expectativas de gols
aproximadamente centradas em resultados 1X2 ruins. Com apenas 35 jogos, não há
prova suficiente de quebra dos parâmetros, embora o resultado seja preocupante
e deva continuar sendo monitorado.

## 7. Onde o mercado sabe mais

Desvantagem de RPS por confiança máxima do modelo:

| Confiança máxima | n | RPS modelo − mercado |
|---|---:|---:|
| <40% | 318 | **+0,016625** |
| 40–50% | 594 | +0,012325 |
| 50–60% | 299 | +0,007296 |
| ≥60% | 107 | **−0,000343** |

Leitura:

- onde o modelo tem convicção alta, ele fica praticamente igual ao mercado;
- onde o jogo é ambíguo para o modelo, o mercado ganha mais;
- esse padrão é consistente com informação contextual ausente: escalações,
  lesões, mudanças de técnico/elenco, momento e outras notícias PIT;
- também pode conter diferenças de estimação, mas simples recalibração de saída
  já foi investigada sem produzir edge.

No recorte em que o modelo escolheu mandante (`n=1.088`), o prêmio do mercado
foi 0,009477 RPS. O mercado separou vitória de empate especialmente por sua
própria confiança na casa:

| P(casa) do mercado | n | vitória real casa | empate real |
|---|---:|---:|---:|
| <35% | 136 | 28,47% | 29,93% |
| 35–45% | 257 | 42,02% | 26,85% |
| 45–55% | 302 | 48,68% | 30,13% |
| ≥55% | 393 | 65,14% | 19,59% |

O modelo tende a ficar no lado “casa” sem reproduzir toda essa separação.

## 8. Clubes que expuseram a lentidão da força

Erro global de classificação em 2026: **52,89%**.

| Clube | Jogos | Erros | Erro em casa | Erro fora | Diagnóstico |
|---|---:|---:|---:|---:|---|
| Internacional | 23 | 16 | 75,00% (9/12) | 63,64% (7/11) | força mal estimada |
| Bahia | 23 | 16 | 58,33% (7/12) | 81,82% (9/11) | força mal estimada |

Como o excesso aparece nos dois papéis, “mando heterogêneo” não explica sozinho
o padrão. A hipótese mais compatível é força desatualizada: quebra de elenco,
técnico ou momento que um Elo de baixa reatividade absorve lentamente.

Não há prova causal porque as features necessárias não existem PIT na base. O
campo `city` está vazio nesses registros e não substitui estádio/venue.

Lista dos jogos errados está preservada em
`docs/RELATORIO_DIAGNOSTICOS_RESIDUAIS_2026-08-24.md` e em
`data/research/residual_diagnostics_2026-08-24.json`.

## 9. Mercados derivados

### OU2.5

Em 940 previsões de desenvolvimento:

- média: 39,85%;
- desvio-padrão: 2,69 pp;
- P10–P90: 37,58%–43,45%;
- range: 36,56%–56,54%;
- coverage de odds: 808/940 = 85,96%.

Passou o gate mínimo de resolução, mas a análise dev-only de divergência contra
o mercado não mostrou ROI monotônico em nenhum lado sob de-vig Shin ou power.
A maioria das faixas teve ROI negativo; aparentes ganhos extremos tinham `n=3`
ou `n=5`, milhares de observações abaixo do poder requerido. Veredito:
`ARCHIVE_OU25_CURRENT_RESIDUAL` sem carregar 2024.

### BTTS

Em 940 previsões:

- média: 44,19%;
- desvio-padrão: **1,29 pp**;
- P10–P90: 42,69%–45,64%;
- range: 35,65%–46,53%;
- coverage de odds: 809/940 = 86,06%.

Falhou o gate estrutural de desvio-padrão mínimo de 2 pp. O modelo quase não
separa jogos nesse mercado. Veredito: `NO_GO_LOW_MODEL_RESOLUTION`.

## 10. Hipóteses já testadas e descartadas

Não propor novamente estas ideias sem **nova informação PIT ou mecanismo novo**:

| Ideia | Resultado |
|---|---|
| Divergência 1X2 modelo × mercado | sem monotonicidade; `NO_GO_CURRENT_RESIDUAL` |
| OU2.5 por divergência | sem monotonicidade e sem poder; arquivado |
| BTTS com modelo atual | variância estrutural insuficiente |
| Recalibração simples de saída | não produziu edge |
| Ajuste escalar de mando | não resolveu |
| Ajuste escalar de força/temperatura | não resolveu |
| Alterar `rho` | não resolveu |
| Ensemble xG existente ligado | H12 comprovou que **desligar** melhora RPS; o ensemble ligado foi retirado |
| Ataque/defesa simples com o mesmo placar | não acrescentou informação útil |
| Ressuscitar faixas/thresholds após olhar resultado | proibido por governança |

O aprendizado comum é que reorganizar a mesma informação histórica não fecha o
gap contra um mercado com dados contextuais mais recentes.

## 11. Causas: demonstrado, inferido e desconhecido

### Demonstrado pelos dados/código

1. O modelo usa uma representação de força altamente comprimida, dominada por
   Elo e parâmetros globais de gols.
2. Em 2026, o argmax escolhe casa em 77,8% dos jogos e nunca empate.
3. O mercado agregado tem RPS melhor no painel 2021–2024.
4. A desvantagem se concentra em baixa confiança do modelo.
5. BTTS tem resolução insuficiente e OU2.5 não ordena retorno no dev.
6. Internacional/Bahia têm excesso de erro nos dois mandos.

### Inferência forte, mas não causalmente provada

1. O Elo está lento para mudanças rápidas de força de elenco/técnico.
2. O viés efetivo para mandante nasce da combinação entre mando global e força
   relativa insuficientemente atualizada.
3. A informação que falta nos jogos ambíguos é majoritariamente contextual/PIT.

### Ainda desconhecido

1. Quanto escalação, desfalques, técnico, estádio, viagens e descanso melhoram
   isoladamente, sem leakage.
2. Se há subgrupos prospectivos onde o modelo adiciona sinal ao mercado.
3. Se odds Pinnacle × casas soft produzem edge estrutural executável; o coletor
   A1 ainda está `NOT_STARTED` no estado registrado.
4. Se T2-2026 continuará extremo com amostra maior.

## 12. Limitações que uma revisão externa deve respeitar

- 2024 tem dono como validação de hipóteses futuras; não usar para selecionar.
- 2025 foi aberto por solicitação explícita em 2026-08-26; não usar para tuning
  nem voltar a chamá-lo de validação cega.
- 2026 é diagnóstico read-only de regras congeladas.
- O agregado SofaScore não identifica bookmaker e não é evidência executável.
- Accuracy não mede qualidade probabilística adequadamente e pune empates de
  modo peculiar; sempre analisar junto com RPS/Brier/log loss/calibração.
- Condicionar lambdas ao resultado realizado ajuda a descrever erros, mas cria
  seleção retrospectiva e não prova causalidade.
- Internacional/Bahia são leads diagnósticos, não autorização para criar ajuste
  específico por clube.
- Os documentos `RELATORIO_FINAL.md` e `CONCLUSOES.md` são legado do projeto de
  seleções/Copa. Podem inspirar mecanismos, mas seus números não são evidência
  direta do Brasileirão.

## 13. Perguntas úteis para outras IAs investigarem

Peça crítica metodológica, desenho de experimento e revisão de código — não
novos picks. Perguntas recomendadas:

1. A decomposição da matriz de confusão admite explicação alternativa além de
   força desatualizada + mando global?
2. Como testar reatividade de força sem escolher meia-vida depois de olhar 2024,
   2025 ou 2026?
3. Qual desenho PIT mínimo isolaria escalação, mudança de técnico e desfalques?
4. A compressão de `p_draw` é consequência inevitável da grade de gols ou de
   parâmetros/inputs específicos?
5. Que teste prospectivo distingue “lambdas centrados com ruído de placar” de
   drift gradual com poder realista?
6. Há métricas próprias de probabilidade — calibration-in-the-large, slope,
   decomposition de Brier, PIT/rank histograms — que faltam como guardrails?
7. O benchmark contra agregado sem bookmaker pode conter viés de seleção ou
   timestamp? Como auditar isso sem promovê-lo a preço executável?
8. Quais features podem ser coletadas com `available_at < kickoff_at` e fonte
   reproduzível, sem custo/complexidade desproporcional ao prêmio de 0,011 RPS?
9. Como corrigir o bug do painel `h9_frozen` para estratos menores que o bloco
   de bootstrap sem mudar a métrica histórica?
10. Que observabilidade falta para provar que o A1 opera sete dias sem gaps,
    conflito de identidade ou quebra de hash-chain?

## 14. Pacote mínimo para compartilhar

Arquivos centrais:

```text
docs/DOSSIE_ANALISE_PREDICTOR_2026-08-26.md
docs/RELATORIO_RETESTE_2026-08-24.md
docs/RELATORIO_DIAGNOSTICOS_RESIDUAIS_2026-08-24.md
docs/RELATORIO_SESSAO_0B_2026-08-24.md
docs/PROJECT_LOGIC_REGISTER.md
docs/experiments/MARKET_03_EDGE_ORDERING_PROTOCOL.md
docs/experiments/MARKET_04_0B_RESOLUTION_PROTOCOL.md
docs/experiments/MARKET_05_A1_COLLECTOR_SPEC.md
data/trials.json
data/research/residual_diagnostics_2026-08-24.json
data/research/market04_0b_resolution_2026-08-24.json
brasileirao_predictor/model.py
brasileirao_predictor/serving_evaluator.py
brasileirao_scripts/benchmark_predictor.py
```

Não compartilhar `data/matches.db` sem intenção explícita: ele tem 49,5 MB,
fica fora do Git e é o banco operacional. Nunca compartilhar `.env`, tokens ou
`ODDSPAPI_KEY`.

## 15. Prompt curto para revisão externa

```text
Revise criticamente o dossiê anexado do brasileirao-predictor. Separe fatos,
inferências e hipóteses. Procure erros de desenho experimental, leakage,
condicionamento retrospectivo, métricas inadequadas e explicações alternativas.
Não proponha picks, stakes, thresholds pós-hoc nem reutilize 2024/2025 para
seleção. Não ressuscite hipóteses marcadas NO-GO sem mecanismo ou informação PIT
nova. Entregue: (1) falhas de raciocínio, (2) causas alternativas priorizadas,
(3) testes read-only que não consumam holdout, (4) dados PIT mínimos necessários,
(5) critérios objetivos de falsificação.
```

## 16. Fontes internas desta consolidação

- `docs/RELATORIO_RETESTE_2026-08-24.md`;
- `docs/RELATORIO_DIAGNOSTICOS_RESIDUAIS_2026-08-24.md`;
- `docs/RELATORIO_SESSAO_0B_2026-08-24.md`;
- `data/research/residual_diagnostics_2026-08-24.json`;
- `data/research/market04_0b_resolution_2026-08-24.json`;
- `brasileirao_predictor/model.py` e `brasileirao_predictor/serving_evaluator.py`;
- `data/trials.json`;
- CI completo do commit `20c5d2c`: Python 3.13/3.14, .NET, Redis e Compose
  aprovados; suíte local com 752 testes e cobertura global de 47%.

## 17. Comparação histórica do mesmo padrão de erro

Após a primeira versão deste dossiê, a mesma decomposição da matriz de confusão
de 2026 foi aplicada read-only às previsões walk-forward do engine `serving` em
2021–2024. Essa primeira comparação parou em 2024; 2025 foi aberto depois, por
solicitação explícita, e aparece em subseção própria abaixo.

| Ano | n | Accuracy | Argmax casa | Argmax empate | Recall fora | Recall empate | Recall casa | Erros “não casa → casa” |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 180 | 52,78% | 85,00% | 0,00% | 18,75% | 0,00% | 89,90% | 75,29% dos erros |
| 2022 | 380 | 46,32% | 85,26% | 0,00% | 19,23% | 0,00% | 92,86% | 82,35% dos erros |
| 2023 | 380 | 45,26% | 80,00% | 0,00% | 22,12% | 0,00% | 83,71% | 74,52% dos erros |
| 2024 | 380 | 48,68% | 81,05% | 0,00% | 29,29% | 0,00% | 86,67% | 77,95% dos erros |
| 2025 | 380 | 50,26% | 79,47% | 0,00% | 28,89% | 0,00% | 86,39% | 72,49% dos erros |
| 2026 | 225 | 47,11% | 77,78% | 0,00% | 33,93% | 0,00% | 85,29% | 73,95% dos erros |

Matriz agregada 2021–2024, com linhas reais e colunas previstas na ordem
fora/empate/casa:

| Real \ previsto | Fora | Empate | Casa | Recall |
|---|---:|---:|---:|---:|
| Fora | 78 | 0 | 261 | 23,01% |
| Empate | 78 | 0 | 278 | 0,00% |
| Casa | 75 | 0 | 550 | 88,00% |

No total foram 1.320 previsões, accuracy 47,58%, 82,50% de argmax casa e 692
erros. Desses erros, 539 (77,89%) eram empate ou vitória visitante que o modelo
classificou como vitória da casa.

Portanto o mecanismo observado em 2026 **não é um acidente daquele ano**. É uma
assinatura estável da regra de decisão atual. Há inclusive melhora gradual do
recall de vitória visitante — 18,75% em 2021 para 33,93% em 2026 — e redução da
frequência de argmax casa, mas a assimetria continua grande.

### O que mudou em 2026

| Ano | `p_draw` médio | empate real | previsto − real |
|---|---:|---:|---:|
| 2021 | 30,04% | 27,22% | +2,81 pp |
| 2022 | 27,80% | 28,42% | −0,62 pp |
| 2023 | 26,47% | 25,79% | +0,68 pp |
| 2024 | 26,41% | 26,58% | −0,17 pp |
| 2025 | 26,01% | 26,05% | −0,05 pp |
| 2026 | 25,02% | 29,78% | **−4,76 pp** |

Em 2021–2025, a probabilidade marginal de empate estava próxima da frequência
real, apesar de empate nunca vencer o argmax. Em 2026, além da velha limitação
do argmax, apareceu subestimação marginal maior de empate.

Conclusão refinada:

1. **Estrutural e recorrente:** o modelo escolhe casa demais e nunca escolhe
   empate como classe; a maioria dos erros tem o mesmo sentido em todos os anos.
2. **Não necessariamente defeito probabilístico histórico:** até 2025, a média
   de `p_draw` acompanhava a frequência real, mostrando que argmax e calibração
   são problemas diferentes.
3. **Sinal específico de 2026:** o gap marginal de empate aumentou para −4,76
   pp. Isso merece monitoramento, mas ainda não autoriza recalibração pós-hoc.

### Abertura explícita do holdout 2025

Em 2026-08-26, após a comparação inicial ter preservado 2025, o usuário pediu
explicitamente “simula 2025”. O holdout foi então aberto uma única vez para a
mesma decomposição congelada, sem ajuste de modelo, parâmetro ou threshold.

Resultado 2025 (`n=380`, walk-forward, engine `serving`): RPS `0,205338977462`,
Brier 1X2 `0,602207342857`, log loss `1,006240088511` e accuracy `50,2632%`.
A matriz real × previsto (fora/empate/casa) foi:

| Real \ previsto | Fora | Empate | Casa |
|---|---:|---:|---:|
| Fora | 26 | 0 | 64 |
| Empate | 26 | 0 | 73 |
| Casa | 26 | 0 | 165 |

Consequência de governança: **2025 não é mais amostra cega** e não pode ser
usado futuramente como validação confirmatória ou para alegar desempenho
out-of-sample não observado. O resultado pode ser usado apenas como diagnóstico
já consumido. Nenhuma comparação econômica contra mercado foi executada nesta
abertura.
