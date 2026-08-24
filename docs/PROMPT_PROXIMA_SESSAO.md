# Prompt para abrir a próxima sessão

Cole o bloco abaixo como primeira mensagem de um chat novo. Ele foi escrito
para uma sessão **sem nenhum contexto** deste projeto.

---

```
Projeto: brasileirao-predictor. Estou na minha máquina Windows, em
C:\Users\Superleo13\Projetos\brasileirao-predictor, com a venv ativa
(.venv\Scripts\Activate.ps1) e acesso ao data/matches.db real — então você pode
EXECUTAR, não só propor.

ANTES DE QUALQUER COISA, leia:
  - HANDOFF.md → sempre o primeiro checkpoint no topo; não use uma data fixa
  - docs/ROADMAP.md → regras inegociáveis, divisão dos dados, fila priorizada
  - docs/RUNBOOK_P0-P2.md → comandos validados e o memorando do P1

Contexto curto: sistema Python 100% local que prevê Brasileirão Série A (1X2 e
over/under 2,5) com Elo + Dixon-Coles/Poisson, sob governança anti-viés rígida.
Capital bloqueado até prova pré-registrada de edge.

ESTADO EM 2026-08-22: 14 trials — 1 COMPROVADA (h12, o ensemble de xG estava
piorando tudo e foi desligado), 1 pré-registrada (h13, coorte prospectiva), 12
fechadas. A pilha de serving sem ensemble bate a climatologia com IC95
inteiramente abaixo de zero (RPS −0,006650, [−0,010544, −0,002858], n=1318), e o
controle negativo passou nos DOIS motores. Isso é resolução preditiva
demonstrada — NÃO é edge econômico, que segue inexistente.

O bloco abaixo é histórico e não é fila operacional. Reavalie-o contra o
primeiro checkpoint do HANDOFF antes de qualquer ação:

MINHA FILA HISTÓRICA, na ordem:

1. A H9 NUNCA EMITIU. data/research/h9_shadow.jsonl não existe — zero picks
   desde sempre, o que explica a trial estar "inconclusiva". A infraestrutura
   está pronta e funcionando (data/research/prospective.db, armazém bitemporal,
   15 mil observações de the_odds_api, 92% das entidades com 7+ capturas =
   movimento de linha real). Descubra por que o funil nunca aprova um pick:
   leia src/research/h9_shadow.py e scripts/emit_h9_shadow.py e me diga qual
   gate está fechando. Isto é o mais urgente: cada rodada sem emitir é dado
   prospectivo perdido para sempre (Regra 5).

2. Consertar o mecanismo por trás das 42 janelas perdidas (23/07 a 17/08):
   (a) nenhuma tarefa do Agendador roda `cron_update_models`, então o cache de
       Elo esvazia e a emissão para em silêncio;
   (b) o Agendador tem 18 tarefas e install_windows_scheduler.ps1 instala 7 —
       as outras 11 não sobrevivem a uma reinstalação;
   (c) o alarme sai com exit=1, indistinguível de "tarefa quebrada" no
       Agendador. Um alarme que ninguém separa de ruído não é alarme.

3. market_no_vig — o teste de teto, e a única coisa que responde "existe
   dinheiro nisso?". Está destravado: o de-vig já existe (src/math_utils.py com
   Shin, src/data/market_anchor.py proporcional), falta ligar como baseline em
   SUPPORTED_BASELINES do benchmark_predictor. Cobertura 1X2 em 2021-2024:
   99,2%. Ressalvas: filtrar home_score IS NOT NULL (34 linhas órfãs de jogos
   adiados), e NÃO medir teto de OU só onde há odds (buraco de 34-37% em
   2023-24 = subconjunto escolhido pela disponibilidade).
   ATENÇÃO: docs/SIMULACAO_2025_2026.md já tem uma tabela "Mercado (Shin fech.)"
   em que o mercado GANHA do modelo no Brier (0,5808 vs 0,5998 em 2025). É
   indicativo, não veredito — está sobre holdout selado + ano exploratório —,
   mas é o dado mais próximo de um teto que existe no repositório hoje, e a
   expectativa realista para o market_no_vig deveria partir dele.

4. DECISÕES MINHAS, com material pronto — me apresente as opções antes de
   mexer:
   - P1: otimizar fit_dixon_coles_parameters (~85-95x medido, exato). Mas o
     gargalo é do motor dixon_coles (~20 min) e não do serving (~3 s), que é o
     que se serve. Vale trocar a agenda da TRACK A de motor?
   - brier_ou25 não tem baseline, logo é um guardrail incapaz de vetar.
     Corrigir muda a superfície de promoção: é pré-registro, não conserto.

REGRAS QUE NÃO QUERO QUE VOCÊ QUEBRE: holdout de 2025 é INTOCADO (a arquitetura
não está congelada); 2026 é exploratório; uma variável por experimento;
accuracy é DIAGNOSTIC_ONLY, nunca métrica de promoção; corrigir o mecanismo em
vez de mascarar no filtro; toda estratificação carrega n; pré-registro que
mede depois de ver o resultado não é pré-registro.

AVISOS PRÁTICOS:
- --engine dixon_coles leva ~20 min por corrida; --engine serving leva ~3 s.
  O teste de permutação são 4 corridas.
- O job de CI Python 3.13 leva ~4 min; não cancele por impaciência, e prefira
  esperar o CI fechar antes de mergear.
- No PowerShell não use \" para escapar dentro de python -c; use só aspas
  simples por dentro. E não use Set-Content em config.yaml (grava BOM).

PRIMEIRA TAREFA — VALIDE TUDO ANTES DE ACREDITAR NOS DOCUMENTOS.

Não é formalidade. Na sessão de 2026-08-22, TRÊS documentos afirmavam coisas
que não batiam com a realidade: o README dizia "414 testes" (eram 611), o
READINESS declarava pyright verde (deu 75 erros), e o SIMULACAO_2025_2026
justificava uma decisão de produção com dados do holdout selado. Documento é
afirmação, não evidência. Rode e me diga o que bateu e o que não bateu:

  # suíte e barreiras
  python -m pytest -q
  python scripts\ci_check.py --fast
  ruff check . ; ruff format --check .
  python -m pyright        # gate REABERTO: HANDOFF diz 75 erros pré-existentes

  # o registro de trials e o atestado
  python -c "import json;t=json.load(open('data/trials.json'));print(len(t),'trials');[print(' ',x['name'],'->',x['status']) for x in t]"
  python -c "import json;print(json.load(open('data/trials.harness_attestation.json')))"
  python -m pytest tests\test_trials_registry_schema.py -q

  # a base
  python scripts\inventario_dados.py

  # os relatorios que sustentam as afirmacoes do HANDOFF
  python -c "import json;d=json.load(open('reports/benchmark_serving_noxg_2026-08-22.json'));print(d['metrics'][0]);print(d.get('ensemble_xg'))"
  python -c "import json;d=json.load(open('reports/permutation_serving_2026-08-22.json'));print(d['verdict'])"
  python -c "import json;d=json.load(open('reports/research_xg_ensemble_2026-08-22.json'));print(d['primary']);print(d['verdict'])"

O que TEM que bater, senão me avise alto:
  - 611 testes passando, ci_check verde, ruff limpo
  - 14 trials: 1 comprovada (h12), 1 pre-registrada (h13), 12 fechadas
  - attestation: evaluate=_rps_pipeline, metric=rps, expires_at 2026-08-29
    (se estiver vencida, renove com:
     python -c "from scripts.research_01a_refit_cadence import attest_rps_power; attest_rps_power()"
     e NUNCA com scripts/_attest_only.py, que atesta o funil PSR do H8 -- pipeline
     errado, e foi assim que a attestation certa foi sobrescrita em 2026-08-22)
  - serving_noxg: RPS 0.213339, delta -0.006650, IC95 [-0.010544, -0.002858],
    ensemble_xg {enabled: false}
  - permutation_serving: verdict passed=true
  - research_xg_ensemble: ganho 0.004410, IC95 [0.001436, 0.007741], comprovada
  - inventario: espelho matches 2021-2024 somando 1518

Se QUALQUER coisa divergir, pare e me diga antes de seguir para a fila. Um
documento que mente sobre o estado e' pior que documento nenhum.

Depois disso, me diga o que entendeu do estado atual e qual você acha que deve
ser o próximo passo — antes de executar qualquer coisa da fila.
```
