# PROMPT CODEX — L0: ESTUDO DE VIABILIDADE LIVE + PENDÊNCIAS

Você é o executor do brasileirao-predictor. Contexto: o pré-jogo modelado foi
encerrado (NO_GO em 1X2, OU2.5 e BTTS — ver HANDOFF.md e
docs/RELATORIO_DIAGNOSTICOS_RESIDUAIS_2026-08-24.md). O projeto pivota para
análise LIVE (in-game). Antes de qualquer modelo live, precisamos provar que
existem dados para backtest honesto. Esta sessão é PESQUISA + DOCUMENTAÇÃO +
PEQUENAS CORREÇÕES — nenhum modelo novo, nenhum treino, nenhuma coleta paga.

Leia antes: HANDOFF.md (checkpoints recentes),
docs/experiments/LIVE_BACKTEST_ENGINE_BLOCKED.md,
docs/PROJECT_LOGIC_REGISTER.md, data/trials.json.

## RESTRIÇÕES ABSOLUTAS
1. Nenhum código de modelo live nesta sessão (o gate L0 precisa responder primeiro).
2. Nenhum acesso a 2025 para treino/seleção. 2026 somente diagnóstico.
3. Nenhuma compra de dados ou assinatura — apenas levantamento documentado de
   o que existe, cobertura e custo.
4. Nenhum pick, stake ou capital. CAPITAL_GATE permanece LOCKED.
5. Registrar novos trials em data/trials.json antes de qualquer teste estatístico.
6. Serving inalterado. Listar todos os desvios ao final. Nenhum commit/push.

---

## TAREFA 1 — ESTUDO DE VIABILIDADE LIVE (L0)

Criar `docs/experiments/LIVE_FEASIBILITY_01.md` respondendo, com fontes citadas:

### 1.1 Dados históricos de EVENTOS live (timestamped)
Para cada fornecedor abaixo, pesquisar e documentar: existe feed/API histórico
de eventos do Brasileirão (gol, cartão, substituição, xG) com timestamp de minuto
(idealmente segundo)? Cobertura (quais temporadas)? Custo? Formato?
- Sportradar (historical)
- Stats Perform / Opta
- API-Football (endpoint de events + plano que libera histórico)
- Betfair Historical Data (Exchange, mercados in-play)
- FootyStats / outros agregadores baratos
- Dados abertos: StatsBomb open data (limitado, mas gratuito — documentar cobertura)

### 1.2 Dados históricos de ODDS live
- Betfair Exchange historical in-play odds (o mais provável de existir com
  timestamp de segundo): cobertura Brasileirão, custo, formato;
- Pinnacle in-play: existe histórico acessível?
- Algum agregador (The Odds API etc.) com odds live históricas?
CRÍTICO: sem odds live históricas, backtest live é impossível — este item
pesa mais que todos os outros.

### 1.3 Microestrutura
Documentar o que se sabe sobre: delay de aceitação de apostas live (Betfair
~5s; casas BR?), política de suspensão de mercado pós-evento, margem típica
live vs pré-jogo nos mercados 1X2/OU.

### 1.4 Checklist booleano final (o gate)
- [ ] (a) Existe histórico de EVENTOS timestamped ≥ 2 temporadas de Brasileirão?
- [ ] (b) Existe histórico de ODDS live ≥ 2 temporadas?
- [ ] (c) Custo total (eventos + odds) compatível com um orçamento de projeto
      pessoal (declarar o valor estimado mensal/anual)?
- [ ] (d) Dados de suspensão/latência/delay disponíveis ou simuláveis de forma
      documentada?

Qualquer NÃO → manter status `HOLD_NO_LIVE_VIABILITY_GO` e recomendar o
próximo caminho (Motor A / coletor Gate A1).
Todos SIM → `LIVE_FEASIBILITY: GO` e a próxima sessão projeta o L1
(motor de estado do jogo). A recomendação deve ser explícita no relatório.

---

## TAREFA 2 — PENDÊNCIAS DE ARRUMAÇÃO (baratas, sem gate)

1. **HANDOFF.md**: diz "22 registros" em trials.json, mas o arquivo tem 23.
   Corrigir a contagem e adicionar nota de que a contagem deve ser derivada,
   não hardcoded (o README já foi corrigido para isso — aplicar o mesmo no
   HANDOFF).
2. **Enriquecimento de venue**: os 32 jogos Inter/Bahia têm `city` vazio e não
   existe campo de estádio. Criar tarefa documentada (schema proposto:
   `matches.venue_id`, `matches.neutral`, `matches.actual_stadium`) e registrar
   em docs/COVERAGE.md como lacuna conhecida. NÃO inferir dados.
3. **Elo stale Inter/Bahia**: registrar em data/trials.json como observação
   (não hipótese nova) que o erro concentrado nos dois papéis indica força mal
   estimada por reatividade lenta — candidata a mecanismo futuro SE o live
   morrer e o projeto voltar ao pré-jogo com informação PIT.
4. **Smokes de serving/live**: estão sendo pulados por ausência de
   data/matches.db. Documentar no HANDOFF como pendência ambiental
   permanente neste checkout, com instrução exata de como rodá-los no
   ambiente que tem o banco.

---

## TAREFA 3 — ATUALIZAR O REGISTRO LÓGICO

Atualizar docs/PROJECT_LOGIC_REGISTER.md com a conclusão consolidada:
- pré-jogo modelado: encerrado (lista dos NO-GO com referências);
- diagnósticos residuais: T2-2026 = ruído; Inter/Bahia = força mal estimada;
  prêmio teórico do mercado = 0,011 RPS concentrado em baixa confiança;
- pivot: Motor A (coletor Pinnacle×soft, Gate A1, spec MARKET-05 congelada)
  e investigação live (L0);
- métrica de sucesso NUNCA é acurácia isolada: é CLV > 0 + ROI IC excluindo
  zero + DSR ≥ 0,95. Acurácia 55–60% só faz sentido como característica de
  nicho live (jogos decididos cedo), nunca como gate.

## TAREFA 4 — VALIDAÇÃO FINAL

- Suíte completa de testes, ruff, pyright: reportar contagens;
- git diff --check;
- Listar TODOS os desvios deste prompt explicitamente;
- Nenhum commit/push.

## ENTREGA
`docs/experiments/LIVE_FEASIBILITY_01.md` + atualizações dos registros +
relatório final com: veredito do gate L0 (booleanos), pendências resolvidas,
e a próxima ação única recomendada.
