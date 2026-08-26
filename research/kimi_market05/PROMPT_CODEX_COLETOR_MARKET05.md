# PROMPT CODEX — Implementar coletor MARKET-05 e iniciar shadow mode (Gate A1)

Contexto: a PoC da fonte PASSOU. Fonte: OddsPapi (`source_id: oddspapi_v4`).
Confirmado em produção: Pinnacle + Betano BR, EstrelaBet, Superbet BR, KTO com
1X2 no mesmo evento (185 casas/evento). Torneio: Brasileirão Série A,
tournamentId 325. Fixture de referência: id1000032566886940.

Leia OBRIGATORIAMENTE antes de codar:
- docs/experiments/MARKET_05_A1_COLLECTOR_SPEC.md (contrato congelado)
- tests/test_collector_contract.py (17 testes que definem "pronto")
- schemas/odds_snapshot_v1.json
- HANDOFF.md (checkpoints)

## RESTRIÇÕES ABSOLUTAS
1. Coletor NÃO alimenta structural_edge.py ainda. Saída: snapshots com
   `homologated: false`. Separação total até Gate A1 PASS.
2. Nenhum ROI, pick, stake, EV operacional ou capital. Shadow only.
3. Chave lida exclusivamente de ODDSPAPI_KEY; nunca persistir, logar ou
   imprimir. Falha fechada se ausente.
4. Nenhum dado pós-kickoff entra no pipeline v1 (assert: captured_at < kickoff_at).
5. SofaScore agregado proibido como fonte aqui.
6. PROIBIDO backfill histórico nesta sessão: o endpoint de odds históricas
   do OddsPapi NÃO deve ser chamado. Qualquer uso futuro de dados históricos
   exige trial registrado ex ante em data/trials.json, com 2025 selado e
   2026 restrito a diagnóstico — as proteções temporais do protocolo aplicam-se
   a TODA e qualquer fonte de dados, incluindo esta.
7. Serving e pipeline de previsão INALTERADOS: o coletor escreve somente em
   data/odds_snapshots/ e data/collector_metrics/. Proibido tocar
   data/matches.db, src/ de previsão, cache ou qualquer job existente.
8. Sem commit/push ao final; listar desvios explicitamente.

## TAREFA 1 — Coletor (src/collector/ + scripts/collect_odds.py)

Implementar contra tests/test_collector_contract.py até os 17 testes passarem:

1. **Ingestão OddsPapi**:
   - `GET /v4/fixtures?sportId=10&tournamentId=325&from=...&to=...` (descoberta de eventos)
   - `GET /v4/odds?fixtureId=...` por evento
   - Casas-alvo: `pinnacle` (referência) + `betano.bet.br`, `estrelabet`,
     `sportingbet.bet.br`, `superbet.bet.br`, `kto`, `pixbet` (soft)
   - Mercados v1: 1X2 (outcomes 101/102/103), OU 2.5, BTTS — conforme
     disponibilidade; OU/BTTS ainda não homologados na PoC → coletar como
     `identity_status` normal mas marcar mercado como `unverified` até auditoria
2. **Identidade canônica**: alias table versionada (data/team_aliases.json,
   mapping_version datada); nomes vindos da fonte SEMPRE passam pela tabela;
   desconhecido → quarentena + sugestão de alias (fuzzy apenas sugere).
   event_id = `br-serie-a|2026|{home}|{away}|{kickoff_date}`.
3. **Armazenamento**: JSONL append-only por dia em data/odds_snapshots/,
   hash-chain (hash_prev), rollover diário com SHA-256 do arquivo registrado.
   Schema exato: schemas/odds_snapshot_v1.json (validar cada linha contra ele).
4. **Deduplicação/conflitos/suspensão/linhas** conforme spec §6.
5. **Cadência**: padrão 15 min; 5 min na última hora pré-kickoff.
   ATENÇÃO AO ORÇAMENTO: free tier = 250 req/mês. Calcular o custo real da
   cadência (fixtures discovery + odds por evento × casas... na prática a API
   cobra por requisição de odds: ~1 req por fixture). Se a cadência completa
   exceder o free tier, configurar MODO ECONÔMICO: coletar apenas
   T-24h/T-6h/T-1h/fechamento por evento (4 snapshots/evento), que cabe no
   free tier para ~60 fixtures/mês, e documentar a decisão. O plano pago só
   entra se o shadow econômico mostrar que a cobertura é insuficiente —
   decisão humana, não automática.
6. **Métricas**: job diário calcula event_coverage, market_coverage,
   continuity, freshness, identity_resolution_rate, conflict_rate conforme
   spec §7, gravando em data/collector_metrics/.

## TAREFA 2 — Shadow mode (o relógio do Gate A1)
- Agendar (documentar como: Windows Task Scheduler / cron — comando exato no
  HANDOFF, não depender de processo manual);
- Shadow começa imediatamente após testes verdes;
- Registrar início do período de homologação em trials.json:
  `market05-a1-shadow` com data de início, critérios de PASS da spec §9;
- Log diário mínimo: snapshots coletados, quarentenados, conflitos, erros de fonte.

## TAREFA 3 — Atualizações de registro
- HANDOFF.md: checkpoint "Gate A1 shadow iniciado em <data>", instruções de
  operação diária e de como verificar métricas;
- trials.json: registrar `market05-a1-shadow` (pre-registrada);
- PROJECT_LOGIC_REGISTER.md: PoC PASS com os números reais (185 casas,
  Pinnacle+4BR, evento Botafogo×Athletico-PR);
- docs/COVERAGE.md: Sportingbet BR sem mercado 101 no snapshot da PoC e
  Pixbet ausente — lacunas conhecidas da fonte;
- Lembrete operacional: rotacionar a chave exposta antes da coleta contínua
  (já orientado; confirmar que a chave em uso é a NOVA).

## TAREFA 4 — Validação
- 17 testes contratuais + suíte completa verdes; ruff; pyright; ci_check;
- Reportar contagens exatas;
- Listar TODOS os desvios.

## TAREFA 5 — Avaliador do Gate A1 (obrigatório, não manual)
Criar `scripts/evaluate_gate_a1.py`: ao fim dos 7 dias, lê
data/collector_metrics/ e emite automaticamente PASS/FAIL contra os 9
critérios da spec §9 (fontes ≥5+ref, 7 dias sem gap >1h, event_coverage ≥90%,
market_coverage ≥95%, continuity ≥95%, identity_resolution ≥99%,
conflict_rate <0,1%, auditoria humana registrada, testes verdes). O veredito
é calculado, nunca redigido à mão. FAIL em qualquer critério → documentar
causa e reiniciar o relógio do zero (spec §9).

ATENÇÃO — consequência do modo econômico: com 4 snapshots/evento, a métrica
`continuity` NÃO é medível. O relatório deve declarar explicitamente que o
shadow econômico é um ENSAIO de pipeline (valida mapping, identidade,
deduplicação e cobertura de eventos), e que a homologação formal do Gate A1
provavelmente exigirá o tier pago. O avaliador deve emitir `REHEARSAL_ONLY`
nesse modo — nenhum PASS pode ser declarado sobre o ensaio.

## TAREFA 6 — Registrar ativo estratégico identificado
Adicionar ao PROJECT_LOGIC_REGISTER.md, seção de ativos não utilizados:
o OddsPapi possui endpoint de odds históricas timestamped (movimentação de
linha, Pinnacle nomeado). Status: IDENTIFICADO, NÃO UTILIZADO nesta sessão
(ver restrição 6). Relevância futura: pode reabrir o Gate L0 live e habilitar
backtests com referência nomeada — qualquer uso exige trial registrado ex ante.

## ENTREGA
Relatório com: testes passando, shadow ativo (sim/não e por quê), modo de
cadência escolhido (completo vs econômico) com a matemática do orçamento de
requisições, data de início do relógio de 7 dias, e pendências.
