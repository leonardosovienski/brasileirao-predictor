# PLANO DE IMPLEMENTAÇÃO — PIVOT PARA LUCRO ESTRUTURAL
## brasileirao-predictor → bet-ops
**Versão 1.0 — 2026-08-24**

---

## 0. Princípio central

O edge não vem mais de prever melhor que o mercado. Vem de **estrutura de mercado**:
a Pinnacle (sem vig) é a melhor aproximação da probabilidade verdadeira; casas recreativas
BR são lentas e caras. Lucrar = comprar odd > preço justo.

Condição de compra: `odd_soft × p_pinnacle_sem_vig > 1 + threshold_segurança`

O modelo próprio vira filtro/secunda opinião, não fonte de edge.
Gates absolutos herdados do protocolo anterior:
- DSR ≥ 0,95 antes de qualquer capital real no Motor A
- Flat stake em todo paper-trading
- CLV registrado em 100% das apostas simuladas
- n por power analysis, nunca arbitrário
- Nenhum pick gerado sem registro prévio em trials/log imutável

---

## MOTOR A — +EV ESTRUTURAL (Pinnacle devig × casas BR)
**Prazo: 3–4 semanas até paper-trading | Custo: baixo | Probabilidade de edge real: ALTA**

### Semana 1 — Acesso a dados
- [ ] Levantar casas BR reguladas com odds acessíveis (API oficial, odds APIs agregadoras,
      ou scrape resiliente). Alvos iniciais: as 5–10 maiores por volume no mercado regulado.
- [ ] Expandir o feed Pinnacle já existente na coorte prospectiva para cobrir:
      1X2, OU 0.5–4.5 (todas as linhas), BTTS, handicaps asiáticos.
- [ ] Definir cadência de coleta: mínimo 1 snapshot/15min em pré-jogo;
      registrar timestamp exato de cada odd (PIT rigoroso — odds movem).
- [ ] Schema: `odds_snapshots(event_id, book, market, line, selection, odd, ts_capture)`
- [ ] Teste de integridade: nenhuma odd sem timestamp; nenhum evento sem mapping
      canônico entre casas (resolver nomes de times/mercados entre fontes — maior
      fonte de bugs desse tipo de sistema).

**Gate A1**: ≥ 5 casas BR + Pinnacle cobrindo ≥ 90% dos jogos da Série A com
timestamps corretos por 7 dias consecutivos. Se falhar → resolver dados antes de prosseguir.

### Semana 2 — Motor de devig e detecção
- [ ] Implementar devig da Pinnacle por dois métodos e comparar:
      - Power method (baseline)
      - Shin method (corrige favorite-longshot bias — preferido para favoritos/zebras)
- [ ] Módulo `src/research/ev_detector.py`:
      - para cada odd BR ativa: `ev = odd_soft × p_shin − 1`
      - alerta se `ev > threshold` (threshold inicial: 3%, declarado ex ante)
      - filtro de staleness: ignorar se a odd Pinnacle tem mais de N minutos
        (a linha pode ter se movido e a casa BR estar correta ao ajustar)
      - filtro anti-palito: checar se o "edge" não é erro de mapping ou odd defasada
- [ ] Reuso: o motor `market_edge_ordering.py` já pareia probabilidade×odd —
      adaptar de modelo×mercado para pinnacle×soft.

**Gate A2**: detector rodando 7 dias em shadow mode gerando alertas; auditoria manual
de 50 alertas aleatórios — se >10% forem artefato (mapping errado, odd defasada,
linha errada), corrigir antes de paper-trading.

### Semanas 3–4 — Paper-trading
- [ ] Registrar TODA aposta que o detector sinalizaria: odd capturada, ts,
      e odd de fechamento Pinnacle do mesmo mercado.
- [ ] Métricas contínuas: CLV por aposta, CLV médio, distribuição, ROI simulado flat stake,
      calibração da p_shin nos eventos apostados.
- [ ] Power analysis inicial: com odds médias ~1.9–2.5, estimar n para DSR ≥ 0,95
      com edge hipotético de 2% e 4%. Esperado: centenas de apostas, não milhares
      (variância de 2 outcomes << 3 outcomes a odd 3.2).

**Gate A3 (LIBERAÇÃO)**: n ≥ power analysis E CLV médio > 0 E ROI com IC > 0 E
DSR ≥ 0,95. Só então capital real, começando com stakes mínimos.

### Operação com capital (pós-gate)
- [ ] Stakes: flat até 200 apostas reais; depois Kelly fracionado (1/4) se calibração confirmada.
- [ ] Gestão de contas: distribuir volume entre casas, evitar padrões óbvios de arb
      (stakes redondos variados, nem sempre o máximo do boost).
- [ ] Monitorar limitação: registrar quando uma casa limitar — é custo operacional esperado.

---

## MOTOR B — ARBS E EXTRAÇÃO DE PROMOS (lucro imediato, baixo risco)
**Prazo: dias | Paralelo ao Motor A desde a semana 1**

- [ ] Com o feed de odds da Semana 1, detector de arb: soma de 1/odd < 1 entre casas
      (incluindo 3 saídas em 1X2 entre 2–3 casas diferentes).
- [ ] Planilha/sistema de promos ativas: bônus de boas-vindas, odds boosts, freebets
      das casas reguladas BR. Calcular EV de extração de cada promo
      (matched betting contra Pinnacle/Betfair Exchange quando houver).
- [ ] Execução manual assistida no início; stakes pequenos até validar o fluxo
      operacional (saque, KYC, limitação).
- [ ] Risco conhecido e aceito: limitação de contas. Mitigação: priorizar promos
      (lucro one-shot) e arbs pequenos esparsos.

**Sem gate estatístico** — arb/promo é travamento matemático, não hipótese.
Gate apenas operacional: fluxo de depósito/aposta/saque validado em cada casa.

---

## MOTOR C — MODELO EM MERCADO SOFT (médio prazo)
**Prazo: 1–3 meses | Só inicia quando Motor A estiver em paper-trading**

O modelo sai do mercado mais eficiente (1X2 Série A) e vai onde ninguém modela direito.

### C1 — Escolha do alvo (1 semana de pesquisa, zero modelo)
Candidatos em ordem de prioridade:
1. **Corners e cartões — Série A** (precificação fraca das casas, dados existentes)
2. **Props de jogador** (ineficiência máxima, mas dados PIT de escalação necessários)
3. **Série B / Copas estaduais** (menos líquido, menos modelado)
Critério de escolha: disponibilidade de odds históricas para backtest honesto
(sem histórico = sem backtest = não começa, regra do protocolo).

### C2 — Modelo novo com a correção raiz
- Quebrar a amarra escalar `exp(a ± b·ΔElo/400)`:
  ataque/defesa por equipe com shrinkage hierárquico + mecanismo novo declarado ex ante
  (não repetir TRACK A02/H12 — registro obrigatório do mecanismo antes do primeiro treino).
- Informação PIT realmente nova (escalação, desfalques) com teste anti-vazamento.
- Validação: dev → validação única → holdout selado. Protocolo idêntico ao atual.

### C3 — Live (condicional)
- Só avança se o estudo de viabilidade (Fase 2 do roadmap anterior) responder:
  (a) existe histórico live timestamped? (b) cobertura ≥ 2 temporadas?
  (c) custo compatível? (d) dados de suspensão/latência?
- Se HOLD → arquivar sem culpa.

---

## ORÇAMENTO E INFRA

| Item | Custo estimado |
|---|---|
| Odds API agregadora (Pinnacle + BR books) | US$ 50–300/mês conforme plano |
| Feed live (só Motor C3, se GO) | a levantar no estudo de viabilidade |
| Servidor/cron para coleta 24/7 | mínimo (reuso da infra atual) |
| Bankroll inicial pós-gate | definir após Gate A3; sugestão: começar com 20–30% do capital total |

## RISCOS MAPEADOS

| Risco | Mitigação |
|---|---|
| Limitação de contas BR | Distribuir volume, promos primeiro, múltiplas casas |
| Odd defasada no detector (falso EV) | Filtro de staleness + auditoria manual (Gate A2) |
| Mapping errado entre casas | Testes de integridade + auditoria (Gate A2) |
| Edge estrutural menor que o esperado | Paper-trading com DSR antes de qualquer real |
| Pinnacle restringir acesso API | Fallback: Betfair Exchange odds como proxy de verdade |
| Regulamentação BR mudar | Monitorar; capital diversificado entre casas |

## DEFINIÇÃO DE SUCESSO

- **30 dias**: Motor A em paper-trading + Motor B gerando primeiros lucros operacionais
- **90 dias**: Gate A3 respondido (GO ou NO-GO com dados); Motor C com alvo escolhido
- **180 dias**: se GO → capital real crescendo com CLV positivo documentado;
  se NO-GO → decisão informada: dobrar em Motor C (mercados soft) ou encerrar
  com capital intacto.

**O capital só sai da gaiola por uma porta: DSR ≥ 0,95 em coorte prospectiva.**
