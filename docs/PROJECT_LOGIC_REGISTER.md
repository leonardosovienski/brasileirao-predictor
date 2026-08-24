# Registro da lógica, hipóteses, testes, tentativas e ideias

Versão: `project-logic-register/1`
Data de consolidação: 2026-08-23
Fontes: `data/trials.json`, `HANDOFF.md`, `docs/ROADMAP.md`, protocolos experimentais e discussão operacional da rodada de 22/08/2026.

Este documento é memória do raciocínio do projeto. Ele **não é pré-registro** e não promove nenhuma ideia. Em caso de divergência de estado, prevalecem o topo do `HANDOFF.md`, o ledger `data/trials.json` e o protocolo específico versionado.

## 1. Tese central do projeto

O objetivo não é acertar placares por intuição nem maximizar accuracy escolhendo apenas jogos fáceis. É produzir probabilidades calibradas para o Brasileirão Série A, medir resolução fora da amostra e, somente em trilha separada, descobrir se existe vantagem econômica prospectiva contra preços executáveis.

A arquitetura atual combina Elo com modelo de gols NB/Dixon–Coles. O serving supera climatologia em 2021–2024, mas perde do mercado 1X2 sem vig. Logo:

- existe sinal esportivo acima da frequência-base;
- esse sinal ainda não supera a informação agregada pelo mercado;
- não há edge econômico comprovado;
- capital permanece bloqueado.

## 2. Regras lógicas que sobreviveram às auditorias

1. **Probabilidade antes de palpite.** A saída primária é a distribuição; o argmax é apenas resumo.
2. **Accuracy é diagnóstica.** RPS é primária no 1X2; Brier, log loss, calibração, resolution e sharpness são guardrails.
3. **Coverage e `n` sempre aparecem.** Selecionar jogos para elevar accuracy pode fabricar melhora.
4. **Um relógio por informação.** Somente dados disponíveis em `predicted_at` entram; kickoff simultâneo não pode vazar resultado.
5. **Pesquisa e operação usam cortes diferentes.** Desenvolvimento: 2021–2023; validação: 2024; 2025 holdout selado; 2026 exploratório. Já no serving de agosto de 2026, todos os resultados anteriores disponíveis de 2025/2026 precisam entrar no ajuste cronológico.
6. **Uma variável por tentativa.** Mudança de modelo, fonte, janela, threshold ou decisão cria tentativa nova.
7. **Problema do motor se corrige no motor.** Não mascarar empate baixo, favorito exagerado ou lambda comprimido com filtro oportunista.
8. **Mercado e modelo esportivo são trilhas distintas.** Boa previsão não prova edge; CLV não prova lucro; ROI sem poder não prova nada.
9. **Pré-registro precisa anteceder o dado.** Resultado observado não pode ganhar rótulo confirmatório retroativo.
10. **Serving robusto e pesquisa honesta têm necessidades diferentes.** Serving pode degradar com segurança; painel precisa contar falhas e preservar paridade train/serve.
11. **Append-only para previsões e settlements.** Nenhuma previsão oficial é reescrita depois do resultado.
12. **Sem capital por inferência.** GO técnico não habilita aposta; exige autorização e gate econômico próprio.

## 3. Trials formais do ledger

O ledger contém 14 tentativas. Os nomes e estados abaixo refletem `data/trials.json` em 23/08/2026.

| Trial | Pergunta | Tentativa/resultado | Estado |
| --- | --- | --- | --- |
| H1 `h1-ou25-edge-2-15-walkforward` | Edge de 2–15% em OU2.5 gera retorno/CLV? | n=455, ROI +7,9%, mas IC95 do P&L cruza zero e DSR=0,94; depois a “abertura” mostrou-se não capturável | `refutada` |
| H2 `h2-periodo-1t-conf60` | Picks de 1º tempo com probabilidade ≥60% mantêm acerto compatível? | n=1493, acerto 79,0% vs confiança média 79,8%; sem odds, não testa dinheiro | `informativa` |
| H3 legado `h3-ou25-sombra-2026` | O sinal OU2.5 sobrevive em captura prospectiva? | fonte agregada do SofaScore foi indevidamente tratada como book; população ficou legacy incomplete | `substituida` |
| H4 `H4_DIXON_COLES_CALIBRATED` | Dixon–Coles calibrado supera Elo puro? | n=737; delta RPS 0,00235 com IC95 cruzando zero | `refutada` |
| H5 legado `h5-ensemble-xg-sombra-2026` | Ensemble xG sustenta OU2.5 prospectivamente? | mesma falha de proveniência da H3 legada | `substituida` |
| H3 Pinnacle | Baseline OU2.5 cria edge contra quote real do Pinnacle? | exige 100 `MATURED_ELIGIBLE`; cobertura conhecida limitada | `inconclusiva` |
| H5 Pinnacle | Ensemble xG supera baseline na mesma população/odds? | coorte paralela, ainda sem amostra suficiente; depois H12 mostrou dano preditivo do ensemble | `inconclusiva` |
| H1 exploratória 2023–2026 | Incluir 2023 reforça o funil OU2.5? | n=567, números favoráveis, mas 2023 foi incluído após observar o baseline e odds eram agregadas | `exploratoria` |
| H7 | Picks prospectivos batem fechamento Pinnacle em CLV? | gate `IC95_lower(CLV)>0`, n≥50; indicador antecedente, não prova lucro | `inconclusiva` |
| H8 | Funil treinado em 2023–2025 funciona no 2026 já observado? | n=76, ROI positivo, IC amplo; visto antes do registro e preço pós-jogo aproximado | `exploratoria` |
| H9 | Replicação prospectiva estrita do H8 com quote executável H−1,5 | modelo/fonte/horizonte congelados; milestones 100/200/300/500 | `inconclusiva` |
| H11 | Refit a cada rodada (~10 jogos) supera refit a cada 100 jogos? | n=1318, ganho RPS 0,001764; IC95 cruza zero | `refutada` |
| H12 | Desligar ensemble xG melhora o serving? | n=1318, ganho RPS 0,004410, IC95 [0,001436; 0,007741]; ensemble desligado | `comprovada` |
| H13 | Serving sem ensemble supera climatologia prospectivamente? | coorte futura, avaliação única somente em n≥900 | `pre-registrada` |

### Lições das trials

- Retorno aparente pode desaparecer quando a cotação não era executável.
- Mais dados após olhar o resultado podem ser úteis para exploração, mas não restauram cegamento.
- CLV tem variância menor que P&L, porém continua sendo proxy, não lucro.
- Dixon–Coles não demonstrou ganho sobre Elo na formulação H4, embora faça parte do serving combinado.
- Recalibrar mais frequentemente não demonstrou ganho robusto.
- O ensemble xG não era diversificação útil: piorava probabilidades e deve permanecer desligado.
- O efeito histórico contra climatologia é real na amostra observada, mas sua confirmação honesta agora depende de futuro prospectivo.

## 4. Experimentos executados fora das 14 trials

### TRACK A02 — força dinâmica por clube

Hipótese: estados separados de ataque/defesa de curto e longo prazo capturam mudança de força melhor que o serving atual.

Tentativa: motor `dynamic_strength`, uma formulação com estados em log-rate, mantendo componentes congelados. A primeira implementação revelou problema no tratamento de ridge e foi corrigida no mecanismo antes da leitura final.

Resultado: NO-GO na amostra de desenvolvimento; piorou RPS e accuracy também caiu. 2024 e 2026 não foram consumidos para resgatar a formulação; 2025 permaneceu intacto. Isso refuta a parametrização, não toda ideia de força dinâmica.

### MARKET-02 — residual multinomial 1X2

Hipótese: o modelo esportivo contém informação residual que melhora a abertura de mercado Shin sem vig.

Tentativa: regressão multinomial usando o mercado como offset e o residual do serving como sinal.

Resultado: NO-GO em 2024; o residual piorou a abertura. Não servir essa especificação. O fato de a abertura pura parecer melhor em 2026 é diagnóstico, não validação retrospectiva.

### PoC/H10 — fadiga e descanso

Hipótese: diferença de dias de descanso altera gols/probabilidades.

Tentativa inicial: PoC barata com datas históricas. Ganho de Brier de aproximadamente 0,04%, melhorando menos da metade dos jogos; sinal praticamente nulo. Interpretação: no calendário regular brasileiro a variável tem pouca dispersão precisamente onde seria necessária.

Tentativa formal posterior: infraestrutura `h10_fadiga_walkforward.py`, com relógio e fingerprint corrigidos. Fadiga permanece uma direção fraca/parcialmente resolvida, não feature promovida.

## 5. Tentativas técnicas que mudaram a interpretação científica

### Guarda de bloco de kickoff

Problema: ordenar apenas por data permitia que jogos simultâneos de uma rodada treinassem uns nos resultados dos outros. Refit frequente ganharia artificialmente.

Correção: kickoff real, ordenação temporal e truncamento estrito `training kickoff < target kickoff` em todos os braços. Lição: corrigir leakage antes de comparar modelos; não filtrar o relatório para escondê-lo.

### Paridade painel × serving

Problema: medir outro motor ou usar cache ajustado com todo o futuro produz números sem relação com produção.

Correção: `ServingStackEvaluator` chama as mesmas funções de Elo, modelo de gols e blend, reajustando em cada corte walk-forward. Lição: paridade funcional sem reutilizar cache futuro.

### Controles positivo e negativo

Hipótese sobre o instrumento: o painel precisa detectar sinal sintético e rejeitar ruído real permutado.

Tentativas: attestation de poder e permutation test. Ambos são barreiras para distinguir modelo bom de pipeline com leakage.

### Bootstrap e calibração

Problemas: bootstrap iid estreitava IC em jogos temporalmente correlacionados; slope não ponderado dava a bins pequenos o mesmo peso de bins grandes.

Correções: bootstrap de bloco móvel e slope ponderado por `n`. Lição: não promover ruído por incerteza subestimada.

### Identidade e proveniência de mercado

Problemas: “abertura-fantasma”, agregador rotulado como bookmaker, fechamento de outra casa, jogos adiados/superseded e captura pós-kickoff.

Correções: bookmaker nomeado, snapshots append-only, closing da mesma casa anterior ao kickoff, identidade por `event_id` e relógio PIT. Lição: preço sem proveniência não mede edge.

## 6. Lógica do empate levantada na rodada

### Observação

Nos jogos Internacional × Atlético-MG e Cruzeiro × Flamengo, as probabilidades 1X2 ficaram próximas e 1–1 foi o placar individual modal. A apresentação por argmax escolheu um lado por margem pequena, ocultando a incerteza.

### Hipótese intuitiva discutida

Se os lados estão equilibrados e o placar modal é empate, talvez o palpite categórico deva ser empate.

### Teste exploratório realizado

Em reconstrução 2021–2024, o padrão “argmax lateral + placar modal empatado” ocorreu em n=528/1320 (coverage 40%). O argmax lateral acertou 39,58%; escolher sempre empate acertaria 29,73%. Com margem lateral ≤3 pontos percentuais, n=106: argmax 32,08% e empate 30,19%. Troca automática não ganhou.

Uma busca conjunta com Elo gap, margem lateral, `p_draw`, probabilidade da moda e `lambda_total` não encontrou regra estável. Uma regra intuitiva “tipo Inter–Galo” perdeu em 2021–2023 e ganhou em 2024, sinal de instabilidade/seleção.

### Interpretação atual

- O usuário identificou corretamente um problema de **comunicação e decisão**: `36–28–36` não é escolha robusta.
- Placar modal empatado e probabilidade agregada de empate são objetos diferentes.
- Não há evidência para converter automaticamente argmax lateral em empate.
- A saída correta hoje é mostrar distribuição, placar modal, distância entre líderes e `SEM_ESCOLHA_ROBUSTA` quando não existir política congelada.
- A compressão de `p_draw`, probabilidade do 1–1 e `lambda_total` sugere investigar geração dos lambdas/rho e resolution do empate, não aplicar boost manual.

O inventário completo está em `docs/DRAW_VARIABLE_CATALOG.md`.

## 7. Ideias de modelo ainda abertas

Estas são direções, não trials:

1. **TRACK A01B:** xG com janela única versus componentes curto/longo; controle barato de recência.
2. **TRACK A02 reformulada:** novos estados dinâmicos, somente após explicar por que a primeira formulação comprimiu/piorou o sinal.
3. **A02B:** testar se Elo ainda agrega depois de forças de ataque/defesa bem modeladas.
4. **A03:** incerteza explícita das forças e shrinkage proporcional à precisão/amostra.
5. **A04:** ambiente de gols dinâmico `mu_t` por época/regime.
6. **A05:** priors de recém-promovidos, retornantes e clubes com pouco histórico na Série A.
7. **A06:** vantagem de mando dinâmica e depois hierárquica por equipe/estádio.
8. **A07:** comparar NB/Dixon–Coles, Bivariate Poisson e Conditional Poisson usando os mesmos lambdas.
9. **A08+:** contexto PIT, uma variável por trial: descanso, viagem, escalação, ausências, treinador, clima e outras.
10. **Calibração específica do empate:** reliability, intercept/slope, Brier binário draw/not-draw e decomposição 0–0/1–1/2–2.
11. **Força de escalação:** construir primeiro valor de jogador PIT e qualidade agregada; só depois testar diferença provável→confirmada.
12. **Mudança de titulares:** quantidade e qualidade das trocas, separando anúncio provável de escalação oficial.
13. **Regime de baixa pontuação:** testar se `lambda_total`, `lambda_gap` e `rho` precisam variar por temporada/regime.
14. **Incerteza da seleção:** política explícita para comunicar jogos equilibrados sem fabricar aumento de accuracy por abstention.

## 8. Ideias de mercado ainda abertas

1. **MARKET-01:** consenso entre casas, fazendo de-vig individual antes da agregação; escolher método por robustez probabilística, nunca ROI.
2. **MARKET-02 reformulada:** somente com hipótese nova que explique o fracasso do residual simples.
3. **MARKET-03:** adicionar uma feature contextual PIT por trial ao residual de mercado.
4. **MARKET-04:** coorte prospectiva em sombra para qualquer especificação que sobreviva ao desenvolvimento.
5. Movimento abertura→snapshot atual, velocidade da mudança e dispersão entre casas.
6. Comparar modelo com mercado de fechamento sem vig na mesma cobertura, preservando closing apenas para avaliação quando ainda não existia na decisão.
7. Separar 1X2, OU2.5 e outros mercados; sucesso em um não transfere automaticamente para outro.

Gate econômico permanece: ROI IC95 inferior >0, CLV IC95 inferior >0, PSR≥0,80 e DSR≥0,95, em coorte prospectiva apropriada. Mesmo assim, ativação de capital exige decisão explícita separada.

## 9. Ideias operacionais de previsão

- Antes de prever, passar pelo `prediction-readiness/1`.
- Usar todo histórico disponível até o instante real, incluindo 2025/2026 anteriores, sem usar o resultado do alvo.
- Congelar modelo, fingerprint, input, probabilidades, placares e limitações.
- Distinguir `OFFICIAL_PRE_MATCH`, `OFFICIAL_LIVE` e `RETROSPECTIVE_ONLY`.
- Escalação só altera números quando houver transformação validada; até lá é contexto.
- Live exige minuto, placar e horário. xG, chutes, posse, cartões e escanteios não entram sem pesos validados.
- Cada previsão oficial recebe ID e linha nova; settlement fica em ledger separado.
- Não chamar simulação após o kickoff de previsão pré-jogo.

## 10. Caminhos já rejeitados ou proibidos

- religar o ensemble xG atual;
- usar 2025 para escolher arquitetura antes do congelamento formal;
- validar arquitetura em 2026 observado;
- aumentar accuracy filtrando jogos e ocultando coverage;
- transformar placar modal empatado em regra automática de empate;
- ajustar threshold depois de olhar os resultados e manter o mesmo nome de trial;
- usar odds pós-jogo/apito como se fossem executáveis pré-jogo;
- usar fechamento futuro como feature da previsão anterior;
- converter lineup ou estatística live em peso improvisado;
- misturar trials preditiva e econômica;
- interpretar CLV como lucro ou resultado pequeno como edge;
- habilitar capital por resultado retrospectivo.

## 11. Ordem lógica recomendada, sem iniciar trabalho automaticamente

1. Preservar protocolo de previsão e prontidão.
2. Auditar resolution/calibração do motor, especialmente empate e compressão dos lambdas.
3. Escolher **uma** hipótese esportiva com efeito plausível maior que o ruído detectável.
4. Desenvolvimento em 2021–2023 e validação em 2024; manter 2025 selado para escolha.
5. Usar 2026 somente para diagnóstico e serving cronológico.
6. Só levar ao prospectivo o que superar métricas probabilísticas e controles.
7. Manter pesquisa de mercado paralela e independente.
8. Não promover serving ou capital sem evidência e autorização.

## 12. Como adicionar uma nova ideia

Registrar neste documento como `IDEIA`, contendo:

- mecanismo causal esperado;
- variável única manipulada;
- dados necessários e disponibilidade PIT;
- métrica primária e guardrails;
- amostras de desenvolvimento/validação;
- efeito mínimo detectável e `n` esperado;
- riscos de leakage, seleção e dupla contagem;
- condição que faria abandonar a ideia.

Somente depois, antes de observar a amostra decisória, criar protocolo/trial separado. Atualizar o estado para `TESTADA`, `REFUTADA`, `INCONCLUSIVA` ou `COMPROVADA` sem apagar a formulação anterior.

## 13. Complemento da auditoria integral do repositório

Esta seção foi acrescentada após cruzar todos os arquivos em `docs/`, `scripts/`, `src/research/`, `reports/`, `contracts/` e o histórico Git. Ela fecha direções que não apareciam na primeira consolidação.

### 13.1 Proveniência: legado de seleções versus evidência do Brasileirão

`CAUSA_RAIZ.md`, `CONCLUSOES.md`, `RELATORIO_FINAL.md`, `RELATORIO_VIABILIDADE.md`, `VIES_ZEBRA.md`, `MAHER_RESULTADO.md` e parte do `V2_BLUEPRINT.md` nasceram no `wc-predictor-v2`, sobre seleções e Copa 2026. Eles explicam a origem intelectual do projeto atual, mas não constituem validação automática na Série A.

Classificação correta:

- mecanismo matemático geral pode virar hipótese no Brasileirão;
- número obtido em seleções permanece evidência daquela arena;
- diferença de densidade, mando, calendário, promoção/rebaixamento e eficiência de mercado impede transferência direta;
- uma conclusão só é atual para o Brasileirão quando repetida pelo painel e dados deste projeto.

### 13.2 Viés favorito–empate–zebra e transformação Elo→lambda

Hipóteses/tentativas herdadas:

| Questão | Intervenção | Resultado legado | Uso atual |
| --- | --- | --- | --- |
| filtro de edge cria viés? | substituir modelo por Shin exato e por Shin+ruído simétrico | filtro não criou nem amplificou o viés | mecanismo inocentado; repetir apenas se o funil mudar |
| Elo comprimido causa zebras? | multiplicar sensibilidade `b` | mais sensibilidade moveu massa de azarão para favorito | causal para parte do fenômeno, mas não autoriza alterar `b` |
| aumentar `b` melhora previsão? | sweep `b×{1,1.3,1.6,2}` | aumentou sharpness, mas piorou Brier e descalibrou empate | caminho rejeitado como correção manual |
| `rho` infla empates? | curva de `rho` até zero | efeito pequeno, cerca de 0,8pp no legado | `rho` não explica sozinho excesso de picks de empate |
| simetria `cosh` achata o modelo? | lambdas com coeficientes livres `b1/b2` | mudança de Brier/probMax desprezível | forma funcional inocentada naquela arena |
| lambda total tem pouca resolução? | decomposição analítica e bins de Elo | `2·exp(a)·cosh(b·ΔElo/400)` quase constante perto de equilíbrio | mecanismo relevante; motivou ataque/defesa e ambiente de gols |

Também foi demonstrado no legado que “muitas apostas em empate” não significa necessariamente `p_draw` inflado: o empate do modelo estava calibrado, mas divergia de um mercado que lhe atribuía menos massa. A hipótese de **draw-shading do mercado** ficou bloqueada por amostra pequena e ausência de odds históricas suficientes. No Brasileirão atual, o serving perde do mercado sem vig; portanto não herdar a conclusão de que o mercado erra no empate.

### 13.3 Calibração específica e decomposição do erro

Tentativas localizadas:

- calibração do empate por faixas, em vez de comparar somente médias;
- calibração 1X2 e OU contra mercado;
- sharpness/probabilidade máxima e entropia modelo versus mercado;
- decomposição por favorito, empate e azarão;
- quebra por equipe de gols feitos/sofridos versus lambdas;
- separação de 0–0, 1–1 e demais empates;
- análise de primeiro versus segundo turno real;
- comparação contra climatologia e mercado no mesmo conjunto pareado.

Lição: média global pode esconder descalibração condicional. Toda retomada precisa usar RPS/Brier/log loss e reliability com `n`, nunca somente frequência média ou accuracy.

### 13.4 Maher, força única e estimador batch

Sequência completa da tentativa herdada:

1. Maher com ataque/defesa por equipe aparentou grande melhora sobre Elo.
2. A primeira interpretação atribuiu o ganho à separação ataque/defesa.
3. Um controle de força única usando a mesma máquina batch superou o Maher.
4. A conclusão foi retratada: o ganho vinha do **estimador batch**, não de informação ataque/defesa.
5. O lead restante ficou multi-confundido: batch vs online, janela, regularização, verossimilhança e cadência mudavam juntos.

No Brasileirão, C1 força única e C2 ataque/defesa em gols apontaram melhora pequena e não significativa em simulação 2025+2026 já observada. TRACK A02 tentou estados dinâmicos de ataque/defesa e deu NO-GO na primeira formulação. Ideia ainda legítima: experimento fatorial que isole estimador, janela, cadência e parametrização — sem reaproveitar 2025 como escolha.

### 13.5 Candidatos C1–C4 e por que o resultado antigo foi revertido

`SIMULACAO_2025_2026.md` comparou:

- C1: força única batch em gols;
- C2: ataque/defesa batch em gols;
- C3: ataque/defesa com alvo misto 85% xG + 15% gols;
- C4: ensemble 50/50 do baseline com C3.

C4 pareceu significativo na simulação observada e chegou ao serving atrás de flag. Posteriormente H12 realizou contraste pareado canônico em 2021–2024 e comprovou que o ensemble piorava RPS. Estado atual: a conclusão mais nova prevalece; ensemble desligado. Lição: resultado atraente em 2025/2026 observado não substitui avaliação canônica nem justifica promoção.

### 13.6 Janelas, recência e abertura de temporada

Tentativas encontradas:

- sweep de `form_half_life_years` de 0,5 a 6 anos e sem decay: ratings mudaram, mas métricas quase não; hipótese refutada naquela formulação;
- sweep de `calibration_window_years`: 0,5 ano pareceu muito melhor em n=160, mas foi escolhido como melhor entre nove valores na mesma amostra;
- bootstrap isolado do vencedor não corrigia adequadamente a seleção múltipla;
- viés por times parecia persistente em n=18/40/80, mas vários sinais inverteram em n=160;
- Botafogo/Cruzeiro permaneceram leads locais naquela leitura, não regras de equipe.

`calibration_window_years=0,5` é candidato exploratório contaminado por seleção, não parâmetro aprovado nem trial formal localizada no ledger. A01B (curto/longo prazo) é a reformulação metodologicamente mais limpa dessa intuição.

### 13.7 Estatísticas de jogo e combinações

Existe infraestrutura para testar individualmente e em pares estatísticas históricas como:

- xG;
- chutes no alvo;
- chutes dentro da área;
- grandes chances;
- demais campos de `match_statistics`.

A primeira tabela de features foi invalidada porque o MLE recebeu colunas no formato errado e porque Elo atual vazava para jogos passados. O código foi corrigido para Elo forward-only e banco read-only. Não foi localizado relatório canônico versionado, posterior à correção, que autorize promover qualquer feature individual ou combinação. Logo:

- resultados anteriores ao fix são inválidos;
- os scripts existentes são infraestrutura/arqueologia, não evidência atual;
- testar muitas features/pares exige controle explícito de multiplicidade;
- estatística pós-jogo só pode alimentar partidas futuras, nunca o próprio alvo.

### 13.8 VORP, valor de jogador e escalações

Direção v3 encontrada:

- regressão ridge esparsa do diferencial de xG em presenças de jogadores;
- replacement level por posição e penalidade para estreantes;
- Elo+VORP versus Elo em teste de sobrevivência com DM/HLN, Brier, CLV e PSR;
- worker de escalações atualizando estado e kernel de baixa latência.

Auditoria histórica encontrou banco insuficiente, lookahead e caminho híbrido quebrado; nenhum artefato VORP legítimo existia naquele momento. Parte da engenharia foi modernizada depois e hoje há agregados de jogadores, mas o agregado final da temporada não é PIT dentro da própria temporada. Não há resultado canônico demonstrando valor incremental de VORP/lineup no Brasileirão.

Estado: hipótese de alto interesse, bloqueada até existir valor de jogador realmente PIT, cobertura documentada, teste sintético do estimador e avaliação batch honesta. Hot path/latência só importa depois que o sinal for provado.

### 13.9 Mercados alternativos examinados

O backtest histórico percorreu, além de OU2.5:

- 1X2;
- dupla chance;
- BTTS;
- OU1.5, OU3.5 e linhas 0.5/4.5/5.5;
- primeiro tempo informativo;
- posteriormente, infraestrutura para handicap asiático, draw-no-bet, cartões, escanteios e finalizações.

1X2 e dupla chance foram desfavoráveis; BTTS/OU3.5 tiveram ROI bruto positivo, mas CLV negativo e nenhuma trial confirmatória. H2 de primeiro tempo foi informativamente calibrada, sem odds para gate econômico. Não foi localizada evidência confirmatória para handicap, cartões, escanteios ou finalizações. Mercado distinto exige trial distinta; nenhuma conclusão de OU2.5 se transfere.

### 13.10 Promovidos, mudanças de elenco e priors

A simulação observou que recém-promovidos entravam perto da média e eram superestimados, sugerindo prior negativo/shrinkage. O forward também levantou drift localizado associado a elenco/técnico e começo de temporada, mas muitos sinais por clube reverteram com mais jogos.

Ideias separadas:

- prior de promovido baseado em Série B e tempo fora da elite;
- maior incerteza inicial, não apenas desconto determinístico;
- atualização por força de elenco/escalação;
- mudança de treinador como evento PIT;
- adaptação mais rápida no começo da temporada.

Nenhuma está promovida. Prior fixo escolhido olhando 2025 destruiria o holdout; deve ser desenvolvido em temporadas anteriores/competições auxiliares.

### 13.11 Engenharia, custo e precisão numérica como hipóteses operacionais

Outras direções encontradas:

- vetorizar Dixon–Coles ou fornecer jacobiano para reduzir o custo do walk-forward;
- kernel Numba/Redis e worker C# para baixa latência;
- teste de paridade entre implementações Python/JIT/C#;
- fallback e idempotência de serving;
- cobertura de providers, integridade de wheels, backup/restore e scheduler;
- fonte alternativa API-Football/Sportmonks e backfill PIT isolado.

Essas melhorias podem tornar o sistema mais rápido/confiável, mas não acrescentam resolução por si mesmas. Mudança numérica exige goldens e recongelamento das réguas. Backfill sem `available_at`, bookmaker e timestamp não sustenta inferência histórica.

### 13.12 Tentativas de fonte de dados

O `PAST_ATTEMPT_LEDGER` registra:

- backfill API-Football histórico sem odds/bookmaker/timestamps PIT: falhou como base de edge;
- Sportmonks: não verificado por falta de token/auditoria;
- store PIT isolado: contrato funcionou;
- The Odds API: parcialmente funcionou para fonte prospectiva nomeada;
- estabilidade de bookmaker: construída como pré-requisito operacional;
- dados de escalação API-Football: opcionais e não autorizados a alterar H9.

Alguns estados textuais desse ledger ficaram antigos depois das migrações H3/H5/H9. Usá-lo como histórico de tentativa, não como fonte do estado operacional atual.

### 13.13 Ideias de arena e generalização

A investigação legada propôs procurar arenas onde haja mais observações por equipe ou mercado menos eficiente:

- clubes em vez de seleções;
- ligas inferiores/mercados menos líquidos;
- dados de Série B para promovidos;
- mercados de eventos (cartões, escanteios, finalizações);
- odds históricas de múltiplas casas.

O brasileirao-predictor já realizou a migração para clubes, mas o resultado contra fechamento 1X2 continua negativo. “Mercado menos eficiente” é hipótese, nunca permissão para assumir edge ou buscar subsets até algum ROI ficar positivo.

## 14. Índice epistemológico final

Após a auditoria, as ideias do projeto se distribuem em nove sentidos:

1. **força das equipes:** Elo, batch ridge, ataque/defesa, dinâmica, promovidos;
2. **geração de gols:** lambda total, dispersão NB, Dixon–Coles, ambiente de gols;
3. **informação externa:** xG passado, estatísticas, elenco, VORP, escalação, treinador;
4. **tempo:** recência, janela, cadência, descanso, começo de temporada;
5. **decisão:** argmax, empate modal, incerteza e escolha robusta;
6. **mercado:** de-vig, consenso, residual, movimento, CLV, executabilidade;
7. **outros mercados:** OU, BTTS, DC, períodos e eventos;
8. **ciência:** PIT, holdout, multiplicidade, bootstrap, controles e métricas;
9. **operação:** coleta, identidade, append-only, serving, latência e capital gate.

Não foi encontrada uma décima família material fora dessas categorias. Novas ideias devem ser encaixadas nelas ou justificar explicitamente por que representam mecanismo novo.

## 15. Correção de conexão do peso temporal (2026-08-23)

Auditoria da previsão retrospectiva de 23/08 mostrou que `half_life_days=360`,
selecionado na H4, era consumido pelo avaliador Dixon–Coles de pesquisa, mas
não pelo `fit_goal_model` NB/DC que serve produção. A janela de quatro anos
cortava o histórico, porém dava peso 1 a todos os jogos restantes.

Correção implementada:

- `fit_goal_model` aceita pesos positivos por observação;
- serving walk-forward e cron calculam `exp(-ln(2) * idade_dias / 360)`;
- jogo atual vale 1, com 360 dias vale 0,5, com 720 dias vale 0,25;
- o valor entra no hash do cache;
- peso unitário preserva o resultado legado;
- ensemble xG continua desligado e capital continua bloqueado.

Esta alteração invalida a comparabilidade direta de benchmarks congelados da
pilha anterior. O efeito foi posteriormente avaliado no sweep da seção 17:
pesos uniformes venceram a grade em desenvolvimento e 360 dias piorou
pontualmente as três perdas em 2024, com ICs cruzando zero. Logo, a conexão é
correção de engenharia, mas 360 dias é NO-GO como melhoria preditiva.

## 16. Auditoria de parâmetros configurados versus efeito real (2026-08-23)

O critério desta auditoria não foi apenas "a chave aparece no código": ela
precisa chegar a uma operação que altere o resultado ou controlar
explicitamente um caminho desligado.

Resultado para o `config.yaml`:

- conectados no serving: `elo.initial_rating`, `home_advantage`,
  `window_years`, `form_half_life_years`, `k_factors`,
  `model.calibration_window_years`, `goal_half_life_days` e `max_goals`;
- conectados, mas deliberadamente inativos: todos os campos de `ensemble_xg`
  porque `enabled=false`; seus valores só alteram o braço quando ligado;
- conectados apenas ao braço de pesquisa: todos os campos de
  `dynamic_strength`; o serving normal não os consome por desenho;
- conectados à avaliação/decisão, não ao modelo: campos de `backtest`;
- conectados apenas a ingestão/fontes: `source`, `player_stats`, `odds_shop` e
  `sofascore`;
- `league` e `tournament_name` são identidade/roteamento, não hiperparâmetros.

Ressalva funcional descoberta no sweep: `elo.initial_rating` é lido, mas uma
translação comum de 1400 a 1600 cancela nas diferenças Elo e produziu saída
idêntica em todos os 940 jogos de desenvolvimento. Ele não implementa um
prior relativo para promovidos; esse mecanismo foi testado separadamente e
também deu NO-GO.

Falhas adicionais encontradas e corrigidas:

1. cache com hash divergente era apenas avisado e ainda assim servido;
2. `kernel_daemon` carregava cache sem validar hash ou quantidade de jogos;
3. `src.backtest` e `scripts/backtest_walkforward.py`, embora descritos como
   caminhos de paridade, reajustavam o NB/DC com pesos uniformes.

Agora o peso exponencial tem uma implementação única em
`model.exponential_recency_weights`, compartilhada por cron, serving e pelos
dois backtests canônicos. Cache incompatível é recalculado em memória na CLI;
o daemon falha fechado e exige refresh persistido.

Scripts exploratórios/históricos que chamam `fit_goal_model` diretamente
continuam podendo usar pesos uniformes. Eles não são serving nem evidência da
pilha atual e não devem ser rotulados como paridade sem migração explícita.
Alterá-los em massa invalidaria a semântica de experimentos registrados.

## 17. Sweep disciplinado das hipóteses testáveis (2026-08-24)

Análise exploratória solicitada pelo operador, não pré-registro. Grades foram
escolhidas antes da leitura de cada resultado; seleção em 2021–2023 e uma
leitura de 2024 apenas para o vencedor. 2025 não foi consumido e 2026 não foi
usado para escolher especificação. Primária: RPS; Brier e log loss como
guardrails; `n=940` no desenvolvimento e `n=380` na validação, coverage 100%,
salvo mercado de abertura (`n=922`, coverage 98,1%).

| Hipótese isolada | Resultado em desenvolvimento | Leitura/validação | Estado |
| --- | --- | --- | --- |
| meia-vida do NB/DC 90/180/360/720/1460 dias vs uniforme | uniforme venceu; decaimento piorou monotonicamente | 360 também piorou pontualmente em 2024, IC cruzando zero | NO-GO |
| janela de calibração 0,5/1/2/3/4 anos | 3 e 4 empataram | 3 anos piorou em 2024 | NO-GO |
| meia-vida Elo 0,5/1/2/4/8/sem decay | 1 ano venceu por margem pequena | piorou RPS/Brier/log loss em 2024 | NO-GO |
| mando 0/50/75/100/125/150 Elo | 100 venceu as três métricas | incumbent preservado | NO-GO para mudança |
| `K` Elo 10/20/30/40/50/60 | 30 venceu as três métricas | incumbent preservado | NO-GO para mudança |
| escala de `rho` 0/0,5/1/1,5/2 | `rho=0` melhorou muito pouco | mesma direção em 2024, mas todos os ICs cruzaram zero | inconclusiva, efeito minúsculo |
| deslocamento global do ambiente de gols | `a+0,10` venceu RPS | piorou todas as métricas em 2024 | NO-GO |
| ambiente de gols PIT por média móvel 50/100/200/380 jogos | todas as janelas perderam | sem candidato | NO-GO |
| escala de sensibilidade Elo→lambda `b` | incumbent venceu RPS/log loss; `1,25×` só melhorou Brier | guardrail falhou | NO-GO |
| dispersão NB vs piso Poisson | diferenças na sexta casa decimal | não repetiu em 2024 | equivalente/NO-GO |
| ataque/defesa por clube baseado apenas em gols, blend 25/50/75% | 25% melhorou todas as métricas | piorou todas em 2024; accuracy subiu apenas 0,26pp | NO-GO |
| temperature scaling 0,8/0,9/1/1,1/1,2 | 0,9 melhorou todas as perdas | piorou todas em 2024 e subestimou empate | NO-GO |
| multiplicador direto de `p_draw` 0,85–1,15 | 0,95 melhorou RPS quase zero, mas piorou log loss | guardrail falhou; boost de empate foi pior | NO-GO |
| blend modelo + fechamento sem vig | mercado puro venceu | fechamento é baseline de avaliação, não feature PIT | modelo sem residual útil |
| blend modelo + abertura sem vig | abertura pura venceu; qualquer peso do modelo piorou | proveniência histórica limita inferência | exploratória |
| `initial_rating` 1400–1600 | saída idêntica: translação comum cancela no Elo | não implementa prior relativo de promovido | mecanismo inócuo |
| prior relativo de promovido −100/−50/0/+50 Elo | zero venceu | sem candidato | NO-GO |

Conclusão desta rodada: nenhuma nova especificação passou
desenvolvimento + validação. Não procurar mais combinações dos mesmos
controles após observar 2024; isso seria tuning no conjunto de validação. O
próximo progresso legítimo depende de informação nova PIT (por exemplo,
força de escalação) ou de uma arquitetura causal nova com protocolo próprio,
não de mais filtros/thresholds sobre as mesmas probabilidades.

## 18. Reconstrução diagnóstica dos jogos de 22–23/08/2026

Esta tabela foi produzida depois dos jogos e serve apenas para preservar o que
foi discutido. Não é previsão prospectiva, pré-registro nem evidência para
selecionar modelo. As probabilidades são casa/empate/fora; o acerto categórico
usa apenas o argmax, com accuracy `DIAGNOSTIC_ONLY`. Escalações não receberam
peso quantitativo porque ainda não existe transformação validada de jogador
para força e lambdas.

| Jogo | Probabilidades | Placar modal | Resultado | Argmax |
| --- | ---: | ---: | ---: | --- |
| Fluminense 2–1 Remo | 59,2% / 23,7% / 17,1% | 1–0 | casa | acerto |
| Internacional 0–0 Atlético-MG | 37,5% / 28,0% / 34,5% | 1–1 | empate | erro |
| Cruzeiro 2–1 Flamengo | 35,4% / 28,2% / 36,4% | 1–1 | casa | erro |
| Bragantino 1–0 Grêmio | 51,1% / 26,2% / 22,7% | 1–1 | casa | acerto |
| Vitória 0–2 Bahia | 41,8% / 27,9% / 30,3% | 1–1 | fora | erro |
| Palmeiras 4–1 Vasco | 75,5% / 16,5% / 8,1% | 2–0 | casa | acerto |
| Santos 1–1 Mirassol | 46,0% / 27,2% / 26,9% | 1–1 | empate | erro |
| Chapecoense 1–0 São Paulo | 29,3% / 27,6% / 43,2% | 1–1 | casa | erro |
| Coritiba 2–1 Corinthians | 39,0% / 28,0% / 32,9% | 1–1 | casa | acerto |

Agregado: `n=9`, coverage 100%, 4/9 acertos, accuracy diagnóstica 44,4%,
RPS 0,1929, Brier 0,5538 e log loss 0,9392. A regra informal de escolher
empate quando o placar modal era empate também acertou 4/9 nesta amostra; ela
não demonstrou ganho. O caso Internacional–Atlético-MG motivou investigar
empates, mas um placar modal empatado não implica que a soma da classe empate
seja maior que casa ou fora. Essa distinção está agora exposta nos
`draw_diagnostics` e catalogada em `docs/DRAW_VARIABLE_CATALOG.md`.
