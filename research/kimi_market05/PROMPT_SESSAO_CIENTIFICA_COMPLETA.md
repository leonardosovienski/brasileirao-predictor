# PROMPT — SESSÃO DE EXECUÇÃO CIENTÍFICA COMPLETA (banco operacional presente)

Você é o executor científico do brasileirao-predictor. O `data/matches.db` operacional
ESTÁ presente neste ambiente. Sua missão é executar TODOS os experimentos pendentes,
na ordem dos gates, respeitando o protocolo ao pé da letra.

Leia antes de qualquer execução:
- HANDOFF.md (checkpoints mais recentes)
- docs/PROJECT_LOGIC_REGISTER.md
- docs/experiments/MARKET_03_EDGE_ORDERING_PROTOCOL.md
- docs/experiments/MARKET_04_0B_RESOLUTION_PROTOCOL.md
- docs/experiments/STRUCTURAL_EDGE_SHADOW_PROTOCOL.md
- data/trials.json (nunca reabrir hipótese refutada sem mecanismo novo declarado ex ante)

## RESTRIÇÕES ABSOLUTAS (testes automatizados devem falhar se violadas)
1. 2025 é holdout selado: PROIBIDO carregar para treino, seleção, calibração ou
   resgate de hipótese. Único uso permitido: nenhum, nesta sessão.
2. 2026: somente leitura diagnóstica de regras já congeladas. Proibido usar para
   escolher parâmetros, thresholds ou hipóteses.
3. 2024: validação de USO ÚNICO por hipótese. Registrar cada consumo em trials.json
   ANTES de executar. Se uma hipótese já consumiu 2024, não reexecutar.
4. Nenhum treino de modelo novo sem GO explícito de gate anterior.
5. Nenhum pick, stake, ou liberação de capital. Saídas: LOCKED ou ELIGIBLE_FOR_REVIEW.
6. Toda hipótese nova: registro ex ante em trials.json com mecanismo declarado,
   faixas, thresholds e critérios GO/NO-GO ANTES da primeira execução.
7. SofaScore agregado = DIAGNOSTIC_ONLY. Nunca evidência econômica.
8. Serving permanece inalterado. Nada de commit/push ao final sem listar o diff.

---

## BLOCO 1 — FASE 0B COMPLETA (o gate que decide o rumo do projeto)

### 1.1 Passo zero — variância estrutural (dev 2021–2023, n=940)
Executar o runner MARKET-04 e reportar:
- std, variância, min, max, range, P10/P90 e histograma (bins 5pp) de `p_over25`
  e `p_btts` do serving;
- distribuição de `lambda_total` (confirmação da amarra escalar exp(2a)·cosh);
- GATE: qualquer std < 0,02 → `NO_GO_STRUCTURAL`, NÃO carregar 2024, documentar
  e ir ao Bloco 6.

### 1.2 Cobertura de odds
- coverage de OU2.5 e BTTS completos no SofaScore por temporada 2021–2024;
- GATE: ambos ≥ 80%, senão documentar limitação e ir ao Bloco 6.

### 1.3 Protocolo completo (só se 1.1 e 1.2 passarem)
- dev 2021–2023: divergência modelo×mercado sem vig (de-vig power + shin),
  AMBOS os lados (over E under, sim E não), 5 faixas de divergência declaradas ex ante;
- monotonicidade, 1.000 permutações estratificadas, power analysis por odd média;
- validação ÚNICA em 2024 (registrar consumo);
- veredito GO/NO-GO por mercado×lado, com n por faixa.

### 1.4 Pergunta bônus declarada ex ante
A hipótese H1 (ou25 edge 2–15%, DSR 0,94 na trave) NÃO pode ser reaberta com os
mesmos parâmetros. Registrar como exploração separada: o recorte da Fase 0B
reproduz a estrutura da H1 ou são nichos diferentes? Documentar sem revalidar H1.

---

## BLOCO 2 — DIAGNÓSTICOS PENDENTES DO CHAT (todos dev 2021–2023 + 2024 apenas
## como réplica única; 2026 somente leitura)

### 2.1 Segundo turno 2026 — drift ou ruído?
- Calibração MARGINAL dos lambdas em 2026-T2 (n=35): λ médio previsto vs gols
  reais, casa e fora. Se lambdas centrados e accuracy colapsada → ruído de
  resultado, não drift de parâmetro. Documentar veredito.
- Comparar com distribuição histórica: accuracy T2 2022–2025 já calculada
  (44–52%); gerar intervalo preditivo binomial para n=35 com p=0,50 e verificar
  se 28,6% está fora do intervalo de 95%.

### 2.2 Inter/Bahia — mando anômalo
- Listar os 32 jogos com erro (16 cada) em 2026: cruzar com qualquer campo de
  venue/estádio disponível; se venue não existe, registrar como DADO FALTANTE
  e criar tarefa de enriquecimento (não inferir).
- Teste simples: taxa de erro desses clubes como MANDANTE vs VISITANTE vs
  baseline do modelo. Se o excesso é só como mandante → evidência para mando
  heterogêneo; se nos dois → força mal estimada.

### 2.3 Decomposição de lambdas por resultado (guardrail permanente)
- Tornar permanente no painel: λ_casa/λ_fora médios por (resultado previsto ×
  resultado real), com n. Este é o detector de resolução — deve rodar em toda
  avaliação futura automaticamente.
- Adicionar também: reliability de p_draw por faixa, matriz de confusão,
  side_probability_gap, empates por placar (0-0/1-1/2-2/3-3+).

---

## BLOCO 3 — BENCHMARK CONTRA MERCADO (diagnóstico, SofaScore)
- RPS/Brier/log loss do serving vs mercado sem vig por temporada 2021–2024,
  por turno e por faixa de confiança;
- Resolução faixa a faixa do mercado no recorte "modelo previu mandante"
  (o recorte onde o modelo tem resolução zero — o mercado separa vitória de
  empate nesses jogos? quanto vale em RPS?);
- Saída: tamanho do prêmio teórico disponível para qualquer modelo futuro.

---

## BLOCO 4 — SANIDADE DO DETECTOR ESTRUTURAL (MARKET-05, shadow only)
- Se existirem snapshots Pinnacle×soft na base: rodar o detector em modo shadow
  retrospectivo, reportar nº de candidatos, distribuição de EV, e checar
  manualmente 20 candidatos (mapping, staleness, linha);
- Se NÃO existirem snapshots: confirmar que o coletor é a dependência real e
  manter gate A1 pendente. NÃO simular com SofaScore agregado.

---

## BLOCO 5 — VIABILIDADE LIVE (pesquisa, zero código de modelo)
Preencher docs/experiments/LIVE_FEASIBILITY_01.md com respostas booleanas:
(a) feed de eventos timestamped histórico existe para Brasileirão (fornecedor,
    cobertura, granularidade, custo)?
(b) odds live históricas ≥ 2 temporadas?
(c) custo total mensal compatível com bankroll?
(d) dados de suspensão/latência/delay disponíveis?
Qualquer NÃO → manter HOLD_NO_LIVE_VIABILITY_GO.

---

## BLOCO 6 — CONSOLIDAÇÃO
- Atualizar trials.json com todos os resultados (status e números);
- Atualizar HANDOFF.md com checkpoint datado;
- Atualizar PROJECT_LOGIC_REGISTER.md com o que mudou;
- Árvore de decisão final:
  * 0B GO em algum mercado/lado → próximo passo: paper-trading flat stake
    prospectivo desse nicho (ledger existente);
  * 0B NO_GO_STRUCTURAL → pré-jogo com modelo atual encerrado em TODOS os
    mercados; energia vai para coletor Pinnacle×soft (Gate A1) e estudo live;
  * 2.1 drift confirmado → abrir hipótese NOVA de reatividade temporal com
    mecanismo declarado (não reabrir sweeps mortos);
  * 2.1 ruído → arquivar T2-2026 como variância.
- Rodar suíte completa + ruff + pyright. Reportar contagens.
- Listar TODOS os desvios deste prompt explicitamente.

## ENTREGA
Relatório único em docs/RELATORIO_SESSAO_0B_<data>.md com:
1. Veredito de cada gate (com números)
2. A tabela de variância 0B
3. Veredito drift-vs-ruído do T2-2026
4. Veredito Inter/Bahia
5. Tamanho do prêmio teórico (Bloco 3)
6. Árvore de decisão: qual galho o projeto ocupa agora
7. Próxima ação única recomendada
