# HANDOFF.md — brasileirao-predictor

> ## CHECKPOINT — SESSÃO CLAUDE (2026-08-22, MADRUGADA) — FONTE DA VERDADE ATUAL
>
> **O projeto tem seu primeiro resultado significativo.** A pilha de serving,
> com o ensemble de xG DESLIGADO, bate a climatologia com IC95 inteiramente
> abaixo de zero em RPS, Brier 1X2 e log-loss — e o controle negativo passou
> **no mesmo motor**. O checkpoint anterior (logo abaixo) continua válido como
> histórico da parte de engenharia.

---

## A — O que foi demonstrado

### 1. Resolução preditiva vs. climatologia (2021-2024, n=1318, motor `serving`, ensemble OFF)

| | valor | climatologia | delta | IC95 |
| --- | --- | --- | --- | --- |
| **RPS** | 0,213339 | 0,219989 | **−0,006650** | **[−0,010544, −0,002858]** |
| Brier 1X2 | 0,622593 | 0,637127 | −0,014534 | [−0,022395, −0,006838] |
| log-loss | 1,036857 | 1,056539 | −0,019682 | [−0,031037, −0,008418] |

Os três IC inteiramente abaixo de zero. RPS 3,02% melhor que a taxa-base.
Relatório: `reports/benchmark_serving_noxg_2026-08-22.json`.

**Dois critérios do §8 NÃO passam** e não devem ser esquecidos:
`calibration_slope` do OU2.5 em **1,5517** (alvo 0,9-1,1) e `resolution` em
0,001405, **menor** que a do v4 (0,001761). A cabeça de over/under continua
sem discriminar — antes era superconfiante e errada (slope 0,31; 0,18 com
ensemble), agora é conservadora e quase constante (`sharpness` 0,000764). Só
trocou de patologia.

### 2. Controle negativo, motor `serving` — **PASSOU**

| | skill | bate climatologia |
| --- | --- | --- |
| referência (dados reais) | **+0,030227** | SIM |
| perm1 (embaralhado) | −0,020940 | não |
| perm2 | −0,018273 | não |
| perm3 | −0,013748 | não |

Amplitude de +0,030 para −0,018. O sinal está no vínculo time↔desfecho: com os
resultados embaralhados o modelo PERDE da climatologia. É o contraste que o
controle no motor `dixon_coles` não exibia (lá a referência também não batia a
climatologia). Relatório: `reports/permutation_serving_2026-08-22.json`.

**O controle do motor `dixon_coles` é uma corrida SEPARADA** — ~1h40, valida a
régua histórica (v4 e 01A), não esta. Não confundir os dois arquivos.

### 3. RESEARCH-XG — `h12-ensemble-xg-ligado-vs-desligado` → **COMPROVADA**

**A primeira trial comprovada do projeto. Treze registradas, uma comprovada.**

Pareado jogo a jogo, uma variável (`ensemble_xg.enabled`), n=1318:

| | ganho | IC95 |
| --- | --- | --- |
| **RPS** | **+0,004410** | **[+0,001436, +0,007741]** |
| Brier 1X2 | +0,021648 | [+0,008562, +0,036863] |
| Brier OU2.5 | +0,030696 | [+0,019290, +0,043565] |
| log-loss | +0,027244 | [+0,010618, +0,046425] |

Os quatro IC acima de zero: o ensemble piorava **todas** as métricas, não
trocava umas pelas outras. `xg_fit_failures_control=0` — o braço ligado era
integralmente com ensemble, então o contraste é o real.
Diagnóstico (Regra 12, não entra no veredito): accuracy 43,3% → 47,9%.

**PROVENIÊNCIA — não é pré-registro cego.** O efeito foi observado antes, em
duas corridas não pareadas do painel. A trial acrescenta o IC95 na MESMA
amostra. Vale menos que um GO cego, e está escrito no relatório e nas notas.

### 4. Por que o ensemble estava ligado — o achado de governança

`config.yaml` justificava a flag com um walk-forward em **"2025+2026"**.
**2025 é holdout selado (Regra 7); 2026 é exploratório (Regra 1).** A flag foi
ligada em 2026-07-17 sob o pré-registro da H5 — o pré-registro foi cumprido, o
que faltou foi a **origem dos dados**. Medido no período legítimo, o efeito se
inverte.

Uma flag ligada com evidência do holdout, servindo em produção por um mês, e
que na amostra limpa piora tudo. É o mecanismo que as Regras 1 e 7 existem para
impedir, falhando na única vez em que foi testado de verdade.

## B — Bugs corrigidos (PRs #31-#36, todas mergeadas)

- **#33** — `--engine serving` morria de `KeyError: 'rho'` com qualquer banco,
  DEPOIS do walk-forward inteiro. O comando do P2 do Roadmap **nunca tinha
  rodado**. Corrigido usando `p_over` da própria grade servida (reconstruir uma
  DC por fora era a distribuição errada: o serving é NB+DC misturado com xG).
- **#35** — o relatório não registrava o estado do ensemble; `xg_fit_failures`
  vinha `0` tanto para "funcionou" quanto para "nunca tentou". Dois relatórios
  de `--engine serving` eram indistinguíveis pelo conteúdo — e duas corridas
  saíram idênticas por isso.
- **#36** — `scripts/research_xg_ensemble.py`, o teste pareado.
- **#31/#32/#34** — `docs/RUNBOOK_P0-P2.md`, validação dos comandos, checkpoint.

## C — Custo: o gargalo do P1 é de UM motor

| motor | ajuste por refit | parâmetros | 1318 previsões |
| --- | --- | --- | --- |
| `dixon_coles` | `fit_dixon_coles_parameters` | ~42-52, sem gradiente | **~20 min** |
| `serving` | `model.fit_goal_model` | 4-5 | **~3 s** |

O gargalo é do motor **que não é o que se serve**. A agenda da TRACK A poderia
rodar sobre `--engine serving` em segundos — mas trocar de motor troca a régua,
e todas as medições congeladas são do `dixon_coles`. **Reavaliar o P1 com isso
em conta antes de mexer na numérica** (`src/dixon_coles.py` segue intocado; a
análise e a medição estão em `docs/RUNBOOK_P0-P2.md` e
`scripts/p1_cost_probe.py`).

## D — Achados NÃO corrigidos (decisão do operador)

1. **`brier_ou25` não tem baseline** (`_metric_record(..., baseline_value=None)`)
   → é um guardrail estruturalmente **incapaz de vetar** pela regra de promoção.
   Corrigir muda a superfície de promoção: é pré-registro.
2. **A cabeça de OU 2.5 não discrimina** — `resolution` ~0,0014 em todas as
   configurações medidas. É o problema aberto mais concreto do modelo.
3. **`scripts/_attest_only.py` é armadilha** — sobrescreve a attestation da
   régua RPS com a do funil PSR do H8. Aconteceu nesta sessão. Renovar a régua
   RPS se faz com
   `python -c "from scripts.research_01a_refit_cadence import attest_rps_power; attest_rps_power()"`.
4. **`pyright`** reportou 75 erros pré-existentes em `src/` num ambiente Linux
   com dependências recém-instaladas, contra o "pyright limpo" registrado antes.
   Conferir na máquina do operador.

## E — O que o projeto continua NÃO tendo

- **Edge econômico: nenhum.** `market_no_vig` — o teste de teto — nunca existiu.
  Bater a climatologia não é bater o mercado. **Capital bloqueado (Regra 4).**
- **Nenhuma coorte prospectiva** (MARKET-04).
- **O resultado de §A.1 não é trial pré-registrada** — emergiu de uma medição.
  Justifica um pré-registro, não o substitui.
- **Holdout de 2025 intocado**, como deve ser. A decisão final de arquitetura
  ainda precisa passar por ele.
- TRACK A: 01B, 02, 02B, 03, 04, 05, 06, 07, 08+ não começaram.

## F — Estado técnico

- Suíte: **589 testes**. `ci_check.py` verde. CI verde (3.13, 3.14, .NET, Compose).
- `ruff check` e `ruff format` limpos.
- `config.yaml`: `ensemble_xg.enabled: false`, com a justificativa registrada
  no próprio arquivo.

---

> ## CHECKPOINT — SESSÃO CLAUDE (2026-08-22) — FONTE DA VERDADE ATUAL
>
> Sessão rodada num **container remoto, SEM acesso a `data/matches.db`**. Nenhum
> experimento real foi executado; o que se fez foi validar os comandos, achar e
> corrigir um bug que os bloqueava, e instruir a decisão do P1.
>
> O checkpoint de 2026-08-21 (abaixo) segue válido como histórico. Onde
> divergirem, vale este — em especial o §6 item 4 daquele checkpoint, que manda
> rodar o motor de serving com um comando que **não funcionava**.

---

## A — O que mudou (PRs #31, #32, #33, todas mergeadas)

### #33 — `--engine serving` nunca rodou (o achado central)

O comando do P2 do Roadmap morria com `KeyError: 'rho'`, **com qualquer banco**.
`_run_walkforward` lia `pred.metadata["rho"]` sem condição, para reconstruir uma
`DixonColesMatrix` e dela tirar o P(over 2.5). A `ServingStackEvaluator` nunca
expôs `rho` — a pilha servida é `Ensemble(NB+DC, AtkDef-xG)`, não uma DC pura.

E morria **depois do walk-forward inteiro**, ao montar as linhas: a mesma forma
de falha do `KeyError: actual_ou25` da PR #27.

Reconstruir a DC por fora também era a distribuição **errada**. `xg_model.blend`
mistura *grades* (não probabilidades) justamente para que 1X2, OU e BTTS saiam
da mesma distribuição — e o painel jogava essa grade fora. Correção: o serving
entrega `p_over` da própria grade servida; `_p_over_from` usa esse campo quando
existe, reconstrói a matriz quando o motor expõe `rho` (o `dixon_coles`, onde a
DC *é* a distribuição certa), e **falha alto** quando não há nenhum dos dois.

O teste que faltava tinha a mesma assinatura de sempre: os existentes cobriam
`_make_evaluator("serving", ...)` — que só **constrói** o objeto — e o evaluator
isolado. Nenhum rodava `_run_walkforward` com `engine="serving"`. Adicionado um
que roda o produtor de ponta a ponta, e **verificado que ele falha sem a
correção**.

### #31 e #32 — `docs/RUNBOOK_P0-P2.md`

Comandos exatos do P0/P2 com o critério de leitura de cada saída, e o memorando
de decisão do P1. **`src/dixon_coles.py` não foi alterado.**

## B — Validação dos comandos (banco SINTÉTICO, apagado depois)

Foi construído um `matches.db` sintético de 1.520 jogos com o DDL real, só para
exercitar o pipeline. **Os números não têm valor científico nenhum.** O que se
validou é que os comandos rodam:

| comando | estado |
| --- | --- |
| P0.1 (snippet de verificação de `trials.json`) | ✅ |
| P0.2 baseline v4 | ✅ ponta a ponta, `n=1320` |
| P0.3 permutação | ✅ **PASSOU**, exit 0, ~68 min (4 walk-forwards) |
| P2 serving | ✅ **só depois da #33** |

No controle negativo, o skill colapsou e ficou **negativo** nas três permutações
(−0,028, −0,019, −0,033), com IC95 inteiro do lado ruim — o comportamento
correto. O `skill_score` da corrida de referência bateu exatamente com o
`rps_skill_score_vs_climatology` do relatório do baseline.

## C — Achados que NÃO foram corrigidos (decisão do operador)

1. **`brier_ou25` não tem baseline.** `_metric_record(..., baseline_value=None,
   ...)` — a climatologia do painel não define baseline de OU 2.5, então
   `delta` e `delta_ci95` vêm `null` **por construção**. Consequência: o Roadmap
   §4 lista Brier OU2.5 como guardrail, mas a regra de promoção exige IC inteiro
   do lado ruim para vetar. **Sem baseline não há IC — esse guardrail é hoje
   estruturalmente incapaz de vetar.** Corrigir muda a superfície de promoção do
   painel: é pré-registro, não conserto de bug.
2. **ECE, `calibration_slope`, `resolution` e `sharpness` não estão em
   `metrics`** — vivem em `guardrails_ou25`, calculados só para o mercado de OU
   2.5, não para o 1X2. O alvo de slope 0,9-1,1 do Roadmap §8 se lê ali.
3. **Fallback silencioso do model tag.** `_half_life_for` cai calado no
   `DEFAULT_HALF_LIFE = 120` se não achar `params.half_life_days`. Um typo em
   `--model` não dá erro: dá um experimento com half-life errado.
   `H4_DIXON_COLES_CALIBRATED` está certo (360d).
4. **`pyright` reporta 75 erros pré-existentes em `src/`** (ex.:
   `src/predict.py:136`, comparação `int | str`), enquanto o §8 do checkpoint
   anterior diz "pyright limpo". Não vem das mudanças desta sessão. Pode ser
   versão de pyright diferente — **conferir na máquina do operador**.

## D — P1: medido, não implementado

`scripts/p1_cost_probe.py` mede, sem tocar no banco, que o normalizador da grade
DC tem **forma fechada exata** (τ ≡ 1 fora das 4 células magras):

```
Σ P(h|λ)·P(a|μ)·τ(h,a) = F(M|λ)·F(M|μ) + Σ_{4 magras} P·P·(τ−1)
```

Objetivo concorda a ~1e-15; fit completo ~85-95x mais rápido. O resíduo nos
parâmetros ajustados (1e-06 a 1e-05, e varia com a **build do scipy**) é ruído
de parada do L-BFGS-B, três a quatro ordens de grandeza abaixo da largura do
IC95 do 01A (0,0064 em RPS). As três opções e seus riscos estão em
`docs/RUNBOOK_P0-P2.md`. **Nada foi implementado — a decisão é do operador.**

## E — O que falta, em ordem

1. **P0.1 — o único bloqueio real.** `data/trials.json` (com a `h11`),
   `data/trials.harness_attestation.json` **renovada** e o relatório do 01A só
   existem na máquina do operador. A attestation do repo segue expirada
   (`2026-08-16`). Conferir `expires_at`, `core_version` e `metric` antes de
   commitar.
2. **P0.2 → P0.3 → P2**, nessa ordem. Agora rodam de verdade.
3. **Ler o bloco `diagnostic` do relatório do 01A** —
   `blocked_observations_treatment` segue sem ter sido lido desde 2026-08-21.
4. **Decidir o P1** e o baseline do `brier_ou25`.
5. **Conferir o tamanho real do banco.** O operador mencionou "um milhão de
   dados", o que não bate com os 2.123 jogos registrados. Provavelmente é
   `odds_snapshots` (append-only, e não lida por nenhum destes comandos). Se
   `matches` cresceu de verdade, o P1 deixa de ser otimização e vira
   pré-requisito.

## F — Estado técnico

- Suíte: **570 testes** (eram 566), `ci_check.py` verde.
- `ruff check` e `ruff format` limpos. CI verde (3.13, 3.14, .NET 10, Compose).
- `main` em `a3e37a5` no fim desta sessão.

---

> ## CHECKPOINT — SESSÃO CLAUDE (2026-08-21) — FONTE DA VERDADE ATUAL
>
> O checkpoint de 2026-08-20 (logo abaixo) continua válido como histórico,
> mas várias conclusões dele foram **superadas** por esta sessão. Onde os dois
> divergirem, vale este.
>
> **Fila de trabalho e prioridades: `docs/ROADMAP.md`** — consolidado no repo
> nesta sessão (antes o Roadmap v1.0-final vivia só como arquivo solto na
> máquina do operador, invisível para uma sessão nova).

---

## 1. O que o projeto é, e por quê

Sistema Python **100% local** que prevê Campeonato Brasileiro Série A — 1X2 e
over/under 2,5 gols — com Elo + Dixon-Coles/Poisson, sob governança anti-viés
rígida. Nenhuma nuvem, nenhum serviço externo além da coleta de dados.

A premissa que organiza tudo: **capital fica bloqueado até existir prova
estatística pré-registrada de edge.** O projeto não foi construído para
"acertar jogos" — foi construído para responder, com rigor, se existe sinal
explorável e se ele sobrevive a um teste honesto. A governança (registro de
trials, Deflated Sharpe, attestation de poder, holdout selado) existe para
poder dizer **não** com credibilidade.

Meta realista, já corrigida com o operador: 70% de acerto 1X2 **não é
atingível** — os melhores modelos do mundo ficam em 52-56%. A régua é RPS com
IC95, não accuracy (que é `DIAGNOSTIC_ONLY`, Regra 12 do Roadmap).

## 2. Onde está tudo na máquina do operador

Repo clonado em `C:\Users\Superleo13\Projetos\brasileirao-predictor`
(Windows, venv gerenciada por `uv`, ativa com `.venv\Scripts\Activate.ps1`).

**Fora do versionamento** (grandes/sensíveis, `.gitignore` com exceções em
`/data/*`):

| Caminho | O que é |
| --- | --- |
| `data/matches.db` | SQLite com os jogos reais. Tabelas `sofascore_matches` (bruto) e `matches` (espelho do modelo). 2.123 jogos, 2021-2026 |
| `data/h9_shadow/` | Ledger da coorte prospectiva de apostas simuladas |
| `data/sofascore_cache/` | Cache da coleta |

**Versionados por exceção** (são artefatos de governança):
`data/trials.json`, `data/trials.harness_attestation.json`,
`data/teams_brasileirao.json`.

Autenticação Git resolvida: `credential.helper` = `wincred`, PAT
`PREDICTORLOCAL`. O bug do Git Credential Manager (.NET) não volta.

Operação: 7 tarefas no Agendador do Windows (`brasileirao-market-research`,
`-prospective-readiness`, `-h9-emit`, `-h9-closing`, `-h9-settle`,
`-h9-backup`, `-h9-missed-window`), todas `Ready`.

## 3. O que esta sessão fez — PRs #25 a #29, todas mergeadas

### #25 — Guarda de bloco de kickoff (o achado central)

A ABC `PrequentialEvaluator` do core fatia por **índice**: `train_step` recebe
`observations[:i]`, estritamente-anterior na *ordem da lista*, não no
*relógio*. Somava-se a isso que `benchmark_predictor` lia `matches.date` (data
**sem hora**) e ordenava por ela — a ordem dentro de uma rodada ficava ao sabor
do SQLite — e rodada de futebol tem **jogos simultâneos**. Resultado: o
enésimo jogo de um bloco treinava com resultados que ainda não tinham apitado.

O agravante: o viés **cresce com a frequência de refit**, que é exatamente a
variável do RESEARCH-01A. Uma implementação ingênua teria medido vazamento em
vez de cadência e produzido um **falso GO**.

Correção: fit **preguiçoso**. `train_step` só enfileira o histórico; o ajuste
sai no `predict_step`, que conhece o kickoff do alvo e trunca em
`kickoff < alvo`. O `kickoff_at` real (que já existia em `sofascore_matches` e
estava sendo descartado) passou a ser lido e usado para ordenar.

### #26 — Auditoria: 7 correções

1. **`src/elo_baseline.py` tinha o mesmo bug, na forma máxima** — reajusta a
   cada passo (`retrain_every` default 1), então *toda* previsão de bloco
   simultâneo vazava. Como é o H₀, o vazamento **inflava o baseline** e faria
   o Dixon-Coles parecer pior. Mesma correção.
2. **`data/trials.json` não era validado por teste**, apesar de o core
   instruir explicitamente. É o denominador do DSR.
3. **`delta_ci95` era sempre `null`** no bloco `metrics`, inclusive na métrica
   primária — o IC já estava calculado e só era usado no `skill_scores`.
4. **Bootstrap era `iid`** enquanto o resto do projeto usa bloco móvel. iid
   estreita o IC e **superestima significância**.
5. **`calibration_slope` era OLS não-ponderado** sobre 10 médias de bin.
6. **`--baseline` era argumento morto**; a docstring prometia um
   `NotImplementedError` inexistente.
7. **`sync_matches_from_sofascore` não filtrava por competição** — risco
   latente para quando a Série B entrar (RESEARCH-05).

### #27 — Bug meu, e a lição que importa

`_paired_losses` lia `actual_ou25`; o painel produz `actual_over`. O
`KeyError` só estourava **no fim**, depois dos dois braços — derrubou uma
execução de 45 min do operador.

O teste não pegou porque **fabricava as linhas à mão**, escrevendo o campo
inexistente nos dicts que ele próprio montava. Validava a invenção, não o
contrato. Trocado por testes que rodam o **produtor de verdade**, mais um
smoke de ponta a ponta de `main()`. Os fixtures passaram a usar o DDL real de
`src/db.py` em vez de `CREATE TABLE` escrito à mão.

### #28 — Painel alinhado com o serving

O painel media Dixon-Coles + Poisson puro; `src/predict.py` serve
`Ensemble(NB+DC, AtkDef-xG)` — Binomial Negativa com ensemble de xG. Modelos
diferentes em distribuição **e** em features.

`src/serving_evaluator.py` (`ServingStackEvaluator`) reconstrói a pilha de
produção dentro do walk-forward. **Não dava para reusar o cache do cron**:
`cron_update_models` ajusta com todos os jogos da janela do banco — honesto em
produção (o cron roda "agora"), vazamento massivo num backtest. A pilha é
reajustada a cada refit sobre histórico truncado, com os cortes de
`elo.window_years` e `calibration_window_years` **relativos ao último jogo do
histórico**, não à data de hoje.

`benchmark_predictor` ganhou `--engine {dixon_coles,serving}`. **`dixon_coles`
segue como default** para não invalidar medições já feitas.

### #29 — Controle negativo (teste de permutação)

`attest_pipeline_power` já provava o controle **positivo** (a régua detecta
sinal sintético). Faltava o oposto, sobre dados **reais**.
`scripts/permutation_test.py` embaralha os `result` entre partidas — cada
`result` viaja inteiro, então as marginais (e a climatologia) ficam idênticas e
só o vínculo time↔desfecho é destruído. O skill contra climatologia tem que
colapsar para zero; se não colapsar, é **vazamento**, e o script sai com
código 2.

Os quatro vazamentos desta sessão teriam aparecido nele. Nenhum quebrava teste
unitário.

## 4. Resultados medidos

### RESEARCH-01A — `h11-refit-cadence-rodada-vs-100jogos` → **REFUTADA**

Executado em 2026-08-21, período 2021-01-01 a 2024-12-31 (holdout de 2025
intocado).

| | |
| --- | --- |
| n | 1.318 |
| RPS CONTROL (`retrain_every=100`) | 0,216870 |
| RPS TREATMENT (`retrain_every=10`) | 0,215106 |
| Ganho pareado | +0,001764 |
| IC95 (bloco móvel) | **[−0,001650, +0,004750]** |

IC cruza zero. O ponto estimado favorece o tratamento, mas por 0,8% relativo —
e custa **12x mais CPU** (4h30 contra 22 min). Descarte correto pelo Roadmap.

Validação silenciosa: o RPS do CONTROL bate **exatamente** com o baseline v4
gerado independentemente (0,21687). Pareamento e carregamento consistentes.

### Baseline

- `reports/benchmark_baseline_v3_2026-08-20.json` — **no repo, mas INVÁLIDO
  como régua**: foi medido até 2026, atravessando o holdout selado de 2025.
- `benchmark_baseline_v4_2026-08-21.json` — n=1318, RPS 0,21687, período
  2021-2024. **Só na máquina do operador, e gerado ANTES da #26**: o RPS e os
  deltas estão certos, mas os IC95 e o `calibration_slope` saíram pelo método
  antigo. **Precisa ser regerado antes de virar régua.**
- Cobertura de kickoff: **1518/1518 com horário real, zero fallback**. A
  guarda de bloco cobrou só 2 observações no CONTROL — ela quase não morde na
  cadência de 100 jogos.

### Placar da governança

**Doze trials registradas, ZERO comprovadas.** (Onze no repo + a `h11`, ainda
não commitada.) Nenhum edge preditivo ou econômico demonstrado. Capital
bloqueado, corretamente.

## 5. O que o projeto NÃO faz ainda

- **Não demonstrou edge algum.** Nem preditivo, nem econômico.
- **Não tem baseline de mercado** (`market_no_vig`). É o teste de teto: se o
  modelo não bate o fechamento sem vig, não há edge econômico. Depende da
  cobertura de odds históricas na base, não verificável a partir do repo.
- **Não tem `elo_baseline` nem `current_v3` plugados** como skill score —
  pedir um deles falha alto (correto).
- **TRACK A mal começou**: 01A é o primeiro de 01B, 02, 02B, 03, 04, 05, 06,
  07, 08+.
- **TRACK B parada**, apesar de `src/research/market_residual.py` já
  implementar o resíduo com logit do mercado como offset (essencialmente o
  MARKET-02) e `residual_gate.py` já ter o gate econômico com PSR. Falta
  MARKET-01 (consenso com de-vig individual) e MARKET-04 (coorte prospectiva).
  **Pode andar em paralelo à TRACK A.**

## 6. O que fazer — em ordem

### Imediato (operador, na máquina local)

1. **Commitar o que só existe local** — a `h11` com veredito, a attestation
   renovada e o relatório do 01A:
   ```powershell
   git add data/trials.json data/trials.harness_attestation.json reports/
   git commit -m "RESEARCH-01A: h11 refutada (IC95 cruza zero, n=1318)"
   git push origin main
   ```
   **A attestation no repo ainda é a velha** (`expires_at` 2026-08-16,
   `core_version` 2.2.0, `metric` psr). A renovada nunca subiu.

2. **Regerar o baseline v4** com o código atual (bootstrap de bloco, slope
   ponderado), parando antes do holdout:
   ```powershell
   python scripts/benchmark_predictor.py --model H4_DIXON_COLES_CALIBRATED `
       --period 2021-01-01,2024-12-31 `
       --output reports/benchmark_baseline_v4_2026-08-21.json
   ```

3. **Rodar o teste de permutação** — valida que nada mais está vazando:
   ```powershell
   python scripts/permutation_test.py --period 2021-01-01,2024-12-31
   ```

4. **Primeira medição do motor de serving** — responde uma pergunta que o
   projeto nunca respondeu com rigor: o ensemble de xG que está **ligado em
   produção** (`ensemble_xg.enabled: true`) melhora ou piora o RPS?
   ```powershell
   python scripts/benchmark_predictor.py --model H4_DIXON_COLES_CALIBRATED `
       --engine serving --period 2021-01-01,2024-12-31 `
       --output reports/benchmark_serving_v1_2026-08-21.json
   ```
   Olhar `block_guard.xg_fit_failures`: se vier alto, o ensemble degrada para
   o baseline com frequência e o que se mede não é o que se pensa medir.

### Decisão pendente do operador

**Custo do walk-forward.** `fit_dixon_coles_parameters` (`src/dixon_coles.py`)
avalia o objetivo num laço Python que constrói uma `DixonColesMatrix` inteira
**por jogo e por avaliação**, e o `minimize` roda **sem gradiente analítico** —
o scipy faz diferenças finitas sobre ~52 parâmetros, ~53 avaliações por passo
do gradiente. É a causa das 4h30. Vetorizar em numpy ou fornecer o jacobiano
daria ganho de ordens de grandeza.

**Mas mexe na numérica e pode mover resultados já congelados.** Com 4h30 por
experimento, a agenda inteira do Roadmap é inviável — então essa decisão
provavelmente é o gargalo real do projeto. Exige autorização explícita e
re-congelamento das réguas depois.

### Pendências menores registradas

- **Linha órfã de jogo adiado**: PK de `matches` é
  `(date, home_team, away_team)`; adiamento muda a data, a linha nova entra e a
  antiga fica. Exige migração de schema (`event_id` em `matches`) sobre a base
  viva.
- **Encoding de nomes com acento** no `by_team` do relatório
  (`AtlÃ©tico Mineiro`, `GrÃªmio`) — cosmético, na ingestão do Sofascore.
- **Diagnóstico do 01A não lido**: o operador não colou o bloco `diagnostic` do
  relatório. Vale conferir `blocked_observations_treatment` — a previsão era
  ~10x o do CONTROL (que foi 2); se vier perto de 2, o diagnóstico do mecanismo
  de vazamento estava errado.

## 7. Regras que não se negociam (do Roadmap v1.0-final)

1. 2026 é exploratório — nenhuma arquitetura se valida nele.
2. **2025 é holdout selado.** Usar para escolher hiperparâmetro o destrói. Os
   scripts recusam por padrão; `--unseal-holdout` existe e não deve ser usado.
3. Corrigir o mecanismo, nunca mascarar no filtro.
4. Capital bloqueado até gate pré-registrado.
5. Uma alteração por experimento.
6. Accuracy é `DIAGNOSTIC_ONLY`, nunca métrica de promoção.
7. Toda estratificação carrega `n`.
8. Trial preditiva ≠ trial econômica — gates separados.

## 8. Estado técnico

- Suíte: **566 testes**, `scripts/ci_check.py` 5/5 verdes.
- CI: Python 3.13 + 3.14 + .NET 10 + Compose. O job 3.13 leva ~4 min
  normalmente (o 3.14 leva ~1,5 min) — **isso é normal, não é travamento**.
- `ruff check`, `ruff format` e `pyright` limpos.
- `main` em `903311d` no fim desta sessão.

---

> ## CHECKPOINT — SESSÃO CLAUDE (2026-08-20) — fonte da verdade atual
>
> **Checklist GOV-P0/OPS-P0 do Roadmap (§12) fechado nesta sessão**, rodando
> pela primeira vez numa máquina Windows real do operador (clone novo em
> `C:\Users\Superleo13\Projetos\brasileirao-predictor` — o caminho antigo
> `C:\Claude-projetos\...` citado nos checkpoints anteriores não existia
> nessa máquina; o projeto nunca tinha sido clonado aqui).
>
> **Fechado:**
> 1. `data/trials.harness_attestation.json` renovado —
>    `python scripts/_attest_only.py` (script descartável criado só pra
>    isso, isolando a etapa 1 de `governanca.py` sem tocar em `trials.json`)
>    rodou contra a base real e imprimiu `controle positivo OK`
>    (`passed_at=2026-08-20T00:42:38Z`). Script apagado depois de usado.
> 2. OPS-P0 instalado de fato — `scripts/install_windows_scheduler.ps1`
>    rodou e as 7 tasks (`brasileirao-market-research`,
>    `-prospective-readiness`, `-h9-emit`, `-h9-closing`, `-h9-settle`,
>    `-h9-backup`, `-h9-missed-window`) estão `Ready` no Agendador de
>    Tarefas.
> 3. Dados 2021-2023 mapeados em `config.yaml` (`season_id` 36166/40557/
>    48982, descobertos via `python -m src.ingest_sofascore --seasons 325`)
>    — item do checklist que exigia 2021-2023 como treino/burn-in (§3 do
>    Roadmap). Coleta real dessas temporadas fica por conta do operador
>    rodando `python -m src.ingest_sofascore` de novo (idempotente).
>
> **Ainda pendente antes de "checklist 100%"**: `reports/benchmark_baseline_v3_<date>.json`
> não foi congelado — `scripts/benchmark_predictor.py` foi rodado (ver
> validação de turno 1/2 de 2026 abaixo) mas o resultado não foi salvo como
> baseline formal ainda. Também achado e corrigido nesta sessão um bug real
> no próprio `benchmark_predictor.py`: `--period` cortava o histórico
> ANTES do walk-forward, matando o burn-in ao pedir um recorte recente
> (`histórico insuficiente (225)` mesmo com 985 jogos no banco) — corrigido
> para rodar o walk-forward sobre o histórico completo e só filtrar as
> linhas de PREVISÃO pro período pedido.
>
> **Primeira leitura real (2026, 225 jogos, half_life=360d do trial H4
> já registrado)**: turno 1 e turno 2 estatisticamente equivalentes (RPS
> 0,214 vs 0,210, sem degradação); skill score vs climatologia levemente
> positivo (RPS +2,4%, Brier +0,5%) mas IC95 cruza zero em ambos — **sem
> significância ainda** com essa amostra. `calibration_slope` do OU2.5 em
> -0,20 (ideal ≈1) é um sinal de atenção, mas com poucos jogos por balde de
> calibração pode ser ruído. Achado paralelo: nomes de time com acento
> saem corrompidos no `by_team` do relatório (`AtlÃ©tico Mineiro`,
> `GrÃªmio`, `SÃ£o Paulo`, `VitÃ³ria`) — bug de encoding na ingestão do
> Sofascore, cosmético, não investigado ainda.
>
> Meta de "70% de acerto 1X2" pedida pelo operador foi corrigida em
> conversa: não é atingível pra futebol (Regra da Seção 10 do Roadmap já
> proíbe esse alvo) — teto realista de mercados profissionais é ~52-56%,
> hoje o modelo está em 48,9%. Direção acordada: perseguir o teto real via
> Track A (RESEARCH-01A em diante), não um número arbitrário.

> ## CHECKPOINT — SESSÃO CLAUDE (2026-08-19) — fonte da verdade anterior
>
> Implementação do checklist GOV-P0/OPS-P0 do "Roadmap Técnico Consolidado
> v1.0-final" (§12), na parte executável neste ambiente (sandbox sem
> `data/matches.db` populado e sem Task Scheduler real — nada aqui roda no
> Windows do operador).
>
> **Feito nesta sessão:**
> 1. `scripts/run_h4_sweep.py` corrigido — passa `pipeline_fingerprint` ao
>    registrar trial nova (mesma lacuna já corrigida em
>    `h10_fadiga_walkforward.py`, documentada como pendência na sessão
>    anterior; agora fechada).
> 2. `scripts/benchmark_predictor.py` criado — painel canônico de
>    medição walk-forward (RPS primário, Brier 1X2/OU2.5, log-loss, ECE,
>    calibration slope, resolution, sharpness, skill score vs climatology
>    com IC95 bootstrap, estratificação com `n` por season/month/team/
>    probability-bucket/lambda-bucket/half-of-season). `src/evaluator.py`
>    ganhou `lam`/`mu` em `metadata` (aditivo) pra viabilizar o cálculo de
>    over/under e lambda_total sem duplicar o fit. Testado com base sintética
>    (sem matches.db real disponível aqui); `elo_baseline`/`current_v3`/
>    `market_no_vig` como baseline de skill score NÃO estão implementados —
>    falham alto (`choices` do CLI), não fingem resultado.
> 3. `docs/READINESS.md` — seção nova "Governança de pesquisa" documentando
>    o painel e os dois itens de GOV-P0 ainda bloqueados (ver abaixo).
> 4. `scripts/report_h9_missed_windows.py` criado (OPS-P0, item que faltava
>    por completo: "alerta para jogos que deveriam ter entrado na janela mas
>    não entraram"). Somente-leitura; compara `sofascore_matches` contra
>    `h9_emission_attempts.jsonl` e classifica em `MISSED` (janela já fechou,
>    dado perdido) vs `AT_RISK` (janela aberta há >20min sem tentativa).
> 5. `scripts/install_windows_scheduler.ps1` — passou a registrar as cinco
>    tasks H9 que faltavam (`brasileirao-h9-emit`/`-closing` a cada 15min,
>    `-settle` a cada 30min, `-backup` diário 05:00, `-missed-window` diário
>    07:00), além das duas já existentes (market-research, prospective-
>    readiness). Suíte completa (489 verdes) e `ci_check.py` (5/5, os dois
>    smokes de banco pulados por falta de `matches.db` neste sandbox) sem
>    regressão.
>
> **Bloqueado — exige ação do operador na máquina Windows, fora do alcance
> deste sandbox:**
> - **GOV-P0 item 1**: renovar `data/trials.harness_attestation.json`
>   (`core_version` 2.2.0, expirado 2026-08-16) — `python scripts/governanca.py`
>   precisa de `matches.db` com burn-in real, inexistente aqui.
> - **GOV-P0 item 5**: congelar `reports/benchmark_baseline_v3_<date>.json`
>   — rodar `scripts/benchmark_predictor.py` contra a base real, mesma
>   dependência acima.
> - **OPS-P0 (instalação)**: `scripts/install_windows_scheduler.ps1` está
>   pronto mas `Register-ScheduledTask` só existe no Windows do operador;
>   ninguém rodou o instalador ainda — as cinco tasks H9 não estão
>   agendadas de fato até isso acontecer.
>
> Nenhuma trial de RESEARCH-01..08 ou MARKET-01..04 foi aberta — por regra
> do Roadmap (§12), pesquisa só começa com o checklist 100% ✓, e os três
> itens acima seguem pendentes.

> ## CHECKPOINT — SESSÃO CLAUDE (2026-08-17) — fonte da verdade anterior
>
> Migração para `predictor-core==2.3.0` e `predictor-ops==3.1.0` (commits
> `a6d2c19` + fix `3336565`, ambos em `main`). `pyproject.toml`, `uv.lock`,
> `Dockerfile.cli`/`Dockerfile.kernel` e `constraints/shared-wheels.sha256`
> apontam para as wheels publicadas em
> `core-predictor@v2.3.0`/`predictor-ops@v3.1.0`, hashes conferidos byte a
> byte contra os assets do GitHub Release. CI verde no commit exato
> (`32036979309`). H8/H9 e capital fechado (nenhuma trial `comprovada`)
> preservados — nada nesta migração tocou `data/trials.json`,
> `contracts/h8-*` ou `contracts/h9-*`.
>
> Pendência aberta desta sessão: `data/trials.harness_attestation.json`
> ainda está em `core_version: "2.2.0"`, expirado em `2026-08-16`. Renová-lo
> exige rodar `scripts/governanca.py` (etapa 1: `attest_pipeline_power`)
> contra um `data/matches.db` com burn-in real — não disponível no ambiente
> onde esta auditoria rodou (banco local vazio). Antes de registrar qualquer
> trial nova, rode a etapa 1 isoladamente (sem a etapa 2 de pré-registro, que
> só deve rodar quando uma configuração nova de fato precisar ser
> pré-registrada) num ambiente com o banco de partidas populado.

> ## CHECKPOINT — SESSÃO CLAUDE (2026-08-15)
>
> Sessão de trabalho com Claude Code cobrindo governança do gate de sombra,
> o pipeline H9 completo (emissão → fechamento → liquidação → auditoria de
> executabilidade) e a formalização de fadiga/descanso como hipótese (H10).
> Seis PRs mergeados em `main`, nesta ordem: **#10** (veredito GO/NO-GO real
> em `evaluate_shadow_cohort.py`, antes hardcoded em INCONCLUSIVE), **#11**
> (guard em `sombra.py`: `BRASILEIRAO_BOOKMAKER` tem que bater com o
> `params.bookmaker` congelado na trial, senão bloqueia a captura), **#12**
> (`status` estruturado em todas as trials de `data/trials.json` + aviso de
> gate em `bet_log.py add` quando nenhuma trial do mercado tem
> `status="comprovada"`; **e** correção do `.env.example` — a chave certa é
> `ODDS_API_KEY`, não `THE_ODDS_API_KEY` como o template dizia antes),
> **#13** (`scripts/emit_h9_shadow.py` — o job de emissão H9 que faltava —
> `+ scripts/record_h9_closing_snapshots.py` + `scripts/settle_h9_shadow.py`),
> **#14** (`scripts/report_h9_execution_quality.py` — disponibilidade real
> da odd no instante da decisão + slippage contra o melhor preço do
> mercado, não só o book aprovado), **#15** (fix de metodologia: as taxas do
> relatório de #14 eram calculadas por linha bruta, não por jogo — um jogo
> que emitia na 3ª tentativa contava como maioria de falhas; **e**
> `scripts/h10_fadiga_walkforward.py`, hipótese formal de descanso,
> walk-forward + bootstrap de bloco móvel + atestado de poder + registro em
> `trials.json`, substituindo `scripts/poc_fadiga.py` que ficou vestigial —
> aquele script lê `matches` com faixas de data (2010-2023 treino,
> "Copa 2026 intocada") que só faziam sentido no `matches` internacional
> pré-adaptação; `poc_fadiga.py` **não foi apagado**, só superado).
>
> **Dois trilhos prospectivos hoje, não um.** O trilho antigo H3/H5
> (`scripts/sombra.py`, bookmaker fixo) está com as quatro tarefas do
> Agendador de Tarefas **desabilitadas** — dormente, não descontinuado. O
> trilho ativo é H8/H9 (`predictor-ops`, bookmaker dinâmico via
> `bookmaker_stability.jsonl`): jobs `brasileirao-market-research` (coleta
> a cada 6h) e `brasileirao-prospective-readiness` (readiness diário) ativos
> e saudáveis em 2026-08-14; `h9_can_emit=true` desde então. Bookmaker
> recomendado no momento: **William Hill** (dinâmico — pode mudar; H9 aceita
> "named-and-stability-approved", diferente de H3/H5 que congelaram
> `pinnacle` em 2026-07-26 e não aceitam outra casa sem trial nova).
> `scripts/emit_h9_shadow.py` e `scripts/record_h9_closing_snapshots.py`
> ainda **não estão agendados** no Agendador de Tarefas — só existem no
> `main`; agendar é ação do operador, cadência sugerida 15min pros dois.
>
> **`BRASILEIRAO_BOOKMAKER` só importa pro trilho H3/H5** (dormente). Se
> reativar aquele trilho, o valor tem que ser `pinnacle` — a nota mais
> antiga deste arquivo (checkpoint de 2026-07-25 abaixo) ainda recomenda
> `betsson`; **está desatualizada**, mantida intocada por ser registro
> histórico. A trial `h3/h5/h7-*-pinnacle-2026` foi registrada em
> 2026-07-26, um dia DEPOIS daquele checkpoint, com `pinnacle` congelado.
>
> **Distância até capital, sem mudança desde 2026-07-25**: nenhuma trial em
> `data/trials.json` tem `status="comprovada"` (confirmável via
> `src.bet_log.capital_gate_status`). H1 segue refutada. H3/H5 seguem
> travadas no gate de 100 `MATURED_ELIGIBLE` (dormentes agora). H8 é
> exploratória (registrada depois de observar o resultado — não vale como
> prova). H9 é a única frente viva rumo a um veredito prospectivo de
> verdade, e ainda não tem amostra alguma liquidada.
>
> **Bugs e dívidas encontrados e corrigidos nesta sessão** (fora os já
> citados acima): `scripts/run_h4_sweep.py` tem uma lacuna idêntica à que
> corrigi em `h10_fadiga_walkforward.py` — não passa `pipeline_fingerprint`
> ao registrar trial nova, e o `predictor-core` vendorizado atual (2.2.0)
> exige esse campo; se alguém rodar aquele script hoje pra registrar uma
> trial nova, quebra. **Não corrigido** (fora do escopo desta sessão).
>
> **Diagnóstico do operador (2026-08-14), ainda de pé em grande parte**:
> pesquisa econômica e coleta prospectiva avançadas; prova de
> executabilidade dos preços parcial (as PRs #13/#14/#15 avançaram isso,
> mas liquidez/spread/redundância de fornecedor de odds e closing de
> referência alternativo à mesma casa continuam pendentes — os que exigem
> conta/decisão de negócio nova, não só código); qualidade de
> escalação/fadiga como hipótese formal parcialmente resolvida (H10
> cobre fadiga; qualidade de escalação MEDIDA, não só arquivada, segue
> pendente — precisa de valor de jogador/escalação provado antes, que o
> próprio diagnóstico já apontava como pré-requisito não cumprido);
> execução real e risco de portfólio permanecem intencionalmente ausentes
> (não construir antes de qualquer gate abrir capital de verdade).

> ## CHECKPOINT OPERACIONAL (2026-07-25)
>
> Checkpoint somente-leitura: nenhum dado criado, nenhum backfill, nenhum trial
> novo, nenhum threshold tocado, nenhuma integração externa.
>
> **Git/vendor.** `main` em `fb97521`, worktree limpo; worktree de checkpoint
> `claude/brasileirao-predictor-checkpoint-9b7d61` no mesmo HEAD. Vendor
> `predictor_core 1.3.3-ga-20260723` (`CORE_MANIFEST.json` aggregate
> `0cfd8ecbd3e45538`, sync `2026-07-23T06:27:14Z`); heartbeats declaram
> `core_provenance.status = VENDOR_VERSION_DECLARED`. Tools `1.3.4` (`ab3bd46`).
> `data/trials.json` = `5863CAD3…03998B` — confere no repo principal e no worktree.
>
> **Jobs (Task Scheduler, 3/3 `Ready` e habilitados, último resultado `0`).**
> `brasileirao-archival-collection`: `SUCCEEDED` exit 0, fim `2026-07-25T06:30:03Z`
> (1,56 s), próxima 26/07 03:30 local. `brasileirao-sombra-manha`: `SUCCEEDED`
> exit 0, fim `2026-07-24T14:16:05Z` (422 s), próxima 25/07 10:00 local.
> `brasileirao-sombra-noite`: `SUCCEEDED` exit 0, fim `2026-07-25T02:07:16Z`
> (434 s), próxima 25/07 23:00 local. Locks adquiridos sem reclaim nos três.
>
> **Runtime externo.** O archival grava heartbeat/log/events fora do repositório,
> em `%LOCALAPPDATA%\predictor-tools\runtime\brasileirao-predictor\brasileirao-archival-collection\`;
> as sombras gravam em `data/runtime/operations/` (ignorado pelo git). As cópias
> em `logs/operations/*archival-collection*` estão congeladas em 23/07 com
> `FAILED`: são artefato morto do caminho anterior, não falha viva. O
> `predictor-gate-monitor` vigia apenas as duas sombras — o job archival ainda
> não está na lista de tasks monitoradas.
>
> **Archival COLLECTION_ONLY** (`collection-brasileirao-20260723-core-9d352654`,
> `collection-only/1`): 202 eventos no arquivo, 190 `SNAPSHOT_RECORDED`, **12
> `COMPLETE`/terminais**, todos os demais estados em 0. `events_seen=197` e
> `transitions_written=0` nas três últimas execuções — idempotência confirmada,
> sem regressão de lifecycle. `collection_only_archive.py` só faz `SELECT` em
> `sofascore_matches` e escreve exclusivamente em
> `data/collection_only/brasileirao_events.jsonl`: **nada dessa coleta entra em
> `matches.db`, trials, gates, H3 ou H5**.
>
> **Gate estrito: `MATURED_ELIGIBLE = 0/100` nas DUAS linhas.**
> `scripts/evaluate_shadow_cohort.py` (a autoridade do gate, `min_sample=100`,
> `capital_enabled: false`) classifica **os 8 picks da H3 e os 3 da H5 como
> `LEGACY_INCOMPLETE`** — nenhum tem `pick_id`, `bookmaker`, `predicted_at`,
> `kickoff_at`, `odds_captured_at` nem `provenance_hash` do contrato
> `PICK_REQUIRED`. `PROSPECTIVE_ELIGIBLE = 0`, `closing_coverage = 0.0`,
> `dataset_hash = e3b0c442…` (conjunto vazio) e veredito `INCONCLUSIVE` em ambas.
> A coorte prospectiva ainda **não começou a contar**; os 11 registros nunca
> contarão. O relatório `shadow-report/v2` do monitor conta registro bruto
> (4 maturados na H3) e por isso NÃO deve ser lido como progresso de gate.
>
> **H3** (`h3-ou25-sombra-2026`): 8 picks legados, 4 liquidados, 4 abertos.
> Diagnóstico operacional apenas: ROI bruto +60% (PnL +2,4 u), CLV médio −5,50%
> com IC95 bootstrap (seed 13) [−6,37%; −4,94%], **4/4 CLV negativos**, ROI IC95
> [−47,5%; +125%]. CLV negativo em 100% da amostra é coerente com a
> abertura-fantasma da H1.
>
> **H5** (`h5-ensemble-xg-sombra-2026`): 3 picks legados, 2 liquidados, 1 aberto
> (Grêmio × Fluminense, 26/07, under @1,95). Linha separada da H3, mesmo gate
> congelado de 100 `MATURED_ELIGIBLE`.
>
> **Estabilidade de bookmaker: `BOOKMAKER_RECOMMENDATION_READY`.** Com 7 smokes
> (o 7º na execução das 10:00 de 25/07), o ledger sanitizado recomenda
> **`betsson`**: presença 100%, cobertura O/U 2.5 de 98,35%, lag máximo 71 s
> (limite 900 s), 238 cotações válidas. Alternativas aprovadas: `nordicbet`,
> `onexbet`, `unibet_nl`, `unibet_se`, `gtbets`, `pmu_fr`, `williamhill`,
> `coolbet`. `pinnacle`, `betanysports`, `betonlineag`, `codere_it` e
> `tipico_de` ficam em `BOOKMAKER_INSUFFICIENT_COVERAGE`; `matchbook` é
> `BOOKMAKER_REJECTED` por ser exchange. O pré-requisito de estabilidade da
> escolha da casa única está, portanto, **cumprido** — falta apenas congelar
> `BRASILEIRAO_BOOKMAKER`, decisão do operador.
>
> **Mudou desde o último checkpoint.** (1) Lifecycle archival corrigido
> (`4388cb9`): a transição inválida `EVENT_STARTED -> VALIDATED` sumiu e o job
> saiu de `FAILED` (23/07) para `SUCCEEDED` (24/07 e 25/07); funil
> `EVENT_STARTED 3 → 0`, `COMPLETE 7 → 12`, `SNAPSHOT_RECORDED 192 → 190`.
> (2) Heartbeats saíram do worktree (`e90c33e`, `fb97521`), com artefatos de
> runtime destrackeados. (3) Uma liquidação nova em cada linha, do mesmo jogo
> (Botafogo × Vitória, 23/07, 0-0, under @2,10, +1,10 u, CLV −6,76%): H3 3 → 4,
> H5 1 → 2. (4) 6º smoke de estabilidade de bookmaker (15 casas, 392 cotações,
> `picks_persisted: 0`).
>
> **Bloqueio único: `BRASILEIRAO_BOOKMAKER` ausente** — bloqueio de decisão de
> configuração, não bug nem infra. `scripts/sombra.py --capture` falha fechado e
> `[capture]` fecha com `0 pick(s) novos` em toda execução desde 21/07. Com o
> ledger em `BOOKMAKER_RECOMMENDATION_READY`, o bloqueio deixou de ser "falta
> evidência" e passou a ser "falta congelar a casa": enquanto não for congelada,
> o contador segue em 0/100 e nenhum pick elegível nasce.
>
> **Distância até capital.** Nenhum caminho de execução financeira existe:
> `data/bets.jsonl` e `data/bankroll.jsonl` estão vazios (0 byte), stake é
> `sombra-0u`, custos são `not_applicable_shadow_no_execution` e o avaliador
> devolve `capital_enabled: false` fixo. Ordem obrigatória: congelar bookmaker →
> 100 `MATURED_ELIGIBLE` a partir do zero → critério pré-registrado (CLV médio
> IC95 bootstrap cluster por jogo > 0 **E** ROI IC_lower > −2%) → só então
> discutir capital. Ao ritmo histórico (~0,7 pick/dia da coorte legada), 100
> liquidados cai perto de dezembro/2026, depois do fim da janela pré-registrada
> (30/09/2026) — a janela provavelmente expira antes do N, e estendê-la é
> tentativa N+1.
>
> **Próximo evento objetivo:** `brasileirao-sombra-noite` em 25/07 23:00 local
> (a execução das 10:00 já ocorreu e produziu o 7º smoke). **H1 segue
> `HYPOTHESIS_REFUTED`** (abertura-fantasma, bloco de 2026-07-17), H3 e H5
> seguem separadas e com gate congelado em 100 `MATURED_ELIGIBLE`.

> ## BACKFILL PIT ISOLADO (2026-07-21)
>
> `src/data/pit_backfill.py` implementa raw imutável com manifesto/hash, curated
> SQLite separado, resolução versionada de entidades, clocks PIT, closing line
> formal, walk-forward e quality gate com bootstrap agrupado. Testes hostis
> cobrem adulteração, ambiguidade, cotação pós-kickoff e lookahead. Nenhum
> registro é escrito em `matches.db`; o gate permanece sem capital automático.
> Ver `docs/BACKFILL_POINT_IN_TIME.md`, `docs/CLOSING_LINE.md`,
> `docs/PAST_ATTEMPT_LEDGER.md` e `docs/HISTORICAL_SOURCE_REGISTER.md`.

> A coorte H3/H5 iniciada em 2026-07-22 exige contrato estrito e bookmaker
> auditável. Os 8 registros anteriores são `LEGACY_INCOMPLETE`; não contam.
> `scripts/sombra.py` bloqueia a persistência prospectiva quando o bookmaker não
> for fornecido, e o settle exige closing pré-kickoff.

> ## FECHAMENTO DAS RESSALVAS TÉCNICAS (2026-07-20)
>
> O ledger H3/H5 passou a registrar prospectivamente `predicted_at`,
> `kickoff_at` UTC, turno da captura, fonte, odd capturada, abertura separada,
> fechamento bruto e par de fechamento. Custos da sombra são explicitamente
> `not_applicable_shadow_no_execution`, 0u: não há execução financeira. O
> relatório `shadow-report/v2` mede cobertura desses campos e mantém registros
> anteriores como legados, sem backfill retrospectivo.
>
> O `startTimestamp` do Sofascore agora é persistido em `kickoff_at`; os três
> scripts de pesquisa antes apontados pelo CI usam Elo `ratings_asof`, eliminando
> o lookahead conhecido. Backup/restore local implementado em
> `src.backup_restore`: snapshot online SQLite, manifesto SHA-256, verificação de
> adulteração, `integrity_check` e restore somente em raiz nova. Roundtrip real
> verificado em `C:\Claude-projetos\Claude\backups\brasileirao-20260720T1430Z`
> e raiz restaurada homônima, com **1.165 partidas** e integridade `ok`.
> As tarefas manhã/noite agora têm `RestartCount=3`, intervalo `PT15M`,
> `StartWhenAvailable=True` e mantêm `IgnoreNew`, fechando a perda de janela por
> falha transitória sem permitir execuções concorrentes.
>
> Validação: **325 passed, 1 warning sintético conhecido; CI 5/5 sem dívida
> temporal**. Nenhuma regra de seleção, threshold, hiperparâmetro, stake ou
> settlement econômico mudou. Única pendência inevitável: passagem do tempo
> até 100 picks H3 liquidados; hoje são 2/100.

> ## AUDITORIA FINAL LOCAL (2026-07-20)
>
> Revisão independente do estado atual, sem mudança científica ou econômica.
> Suíte completa: **320 passed, 1 warning conhecido**; `scripts/ci_check.py`:
> **5/5**; suíte suportada de `tools/`: **139 passed, 1 skipped**; manifest do
> core e auditoria byte a byte: **44/44 idênticos**. O SQLite operacional
> passou `integrity_check` e `quick_check`, com 1.165 partidas, 8.297 linhas
> de odds e 80.375 snapshots; não foram encontrados eventos/partidas
> duplicados, placares negativos, HT > FT ou odds não finitas/não positivas.
> Nove linhas de mercado são parciais, condição já coberta por descarte claro
> do mercado incompleto (`test_mercado_parcial_pula_o_mercado_nao_o_jogo`).
>
> B3b/B4 seguem protegidos pelos testes de confronto repetido por data e
> idempotência por `bet_id`. A H3 tem **7 picks, 2 maturados e 5 abertos**:
> ROI bruto +17,5%, CLV médio −5,025%, Brier/RPS 0,269568 e log loss 0,732336.
> Esses números são apenas diagnóstico operacional: o gate de 100 liquidados
> permanece fechado e o resultado econômico é **INCONCLUSIVO**. Nenhum bug
> novo inequívoco foi reproduzido; nenhum código, parâmetro ou artefato
> operacional foi alterado. Veredito: **PASS LOCAL COM AMOSTRA AINDA
> INSUFICIENTE**.

> ## 🔵 AUDITORIA HOSTIL DE ROBUSTEZ — RODADA 2 (2026-07-18/19)
>
> Rodada dedicada a este domínio (branch `claude/brasileirao-predictor-audit-11f575`).
> B3b/B4 (settlement com `match_date` + idempotência por `bet_id`, `e54a55d`)
> **reconfirmados no código e nos testes que os protegem**
> (`test_settle_confronto_repetido_exige_match_date_para_desambiguar`,
> `test_settle_idempotente_sobrevive_a_reordenacao_do_arquivo`). Vendor
> byte-idêntico (44/44), `sync_core --check` OK, CI 5/5.
>
> **5 correções de robustez reais** (commit `ba0bd7d`, nenhuma científica):
> (1) `shin_probabilities` rejeita odds 0/negativa/NaN/Inf/None com ValueError
> claro; (2) `_market_probs` ignora linhas-placeholder do Sofascore
> (1X2=1.0/1.0/1.0 — 4 reais na base viravam p=⅓ fabricado); (3) `sombra.settle`
> ganhou dedupe intra-execução (pick duplicado não liquida 2×), CLV só com
> fechamento válido (nunca NaN no ledger) e recusa de linha O/U inteira (push
> não implementado); (4) `record_result` rejeita placar negativo; (5) comentário
> do `config.yaml` reconciliado com a flag `ensemble_xg` ligada. Suíte
> **302 → 320 verdes** (+18 hostis: Shin degenerado, liquidação duplicada,
> banco truncado, concorrência WAL, etc. — `tests/test_hostil_2026_07_18.py`).
>
> **Sombra (2026-07-19)**: H3 = 4 picks / 2 liquidados (ROI +17,5%, CLV médio
> −5,03%); H5 = 2 picks / 1 liquidado (CLV −6,87%). CLV negativo em 3/3 —
> coerente com a abertura-fantasma, mas amostra irrisória: **nenhuma conclusão
> antes de 100 liquidados** (marco congelado no trials.json). Achado
> operacional: run noturno de 2026-07-18 02:00Z morreu com exit 0xC000013A
> (processo interrompido — shutdown/logoff), heartbeat ficou `STARTED` e o
> lock ficou órfão; o runner sabe recuperar lock órfão (precedente de
> 2026-07-16) — observar o próximo run noturno.

> ## ADENDO ECOSSISTEMA (2026-07-18)
>
> Vendor de `predictor_core` byte-idêntico ao canônico (`sync_core.py --check`,
> `tools/vendor_byte_audit.py`), sincronizado em `5276f65`. Suíte: **302
> passed**. Settlement teve 2 bugs financeiros reais corrigidos numa rodada
> anterior (`e54a55d`: `match_date` para desambiguar confrontos repetidos;
> idempotência por `bet_id` em vez de posição de arquivo) — ver
> `FINAL_FORENSIC_REVIEW.md`. Auditoria hostil adicional 2026-07-18 (goal
> model com histórico vazio/degenerado, odds inválidas, placar negativo):
> nenhum bug novo encontrado. Sem incidente de segurança próprio. Pendências
> reais: `PENDENCIAS_ABERTAS.md` (SCI-5 amostra do shadow mode, DEBT-3
> `brier` duplicado em scripts scratch — nenhuma bloqueante). Documento
> canônico do ecossistema: `../ECOSYSTEM_HANDOFF.md`.
>
> ## 🔴 ABERTURA-FANTASMA CONFIRMADA — O SINAL DA H1 ERA ARTEFATO (2026-07-17)
>
> Auditoria da fonte + falsificação executada (adendos 2026-07-17 em
> `docs/RELATORIO_BACKTEST_2026-07-10.md`): o `initialFractionalValue` do
> Sofascore é abertura-template (favorece OVER em ~64% vs ~14% no
> fechamento; 60% dos pares ficam mais perto do fechamento INVERTIDO;
> parser inocentado). **Backtest refeito a preço de fechamento
> (`scripts/backtest_close.py`): OU2.5 vira ROI −7,8%, PSR 0,14** — o
> +7,9%/CLV +19,55% da H1 morava inteiramente na abertura fictícia.
> Coerente com o forward 2026 (ROI −22% a odds correntes).
>
> Consequências: (1) "ampliar N da H1" perdeu a motivação; (2) nunca mais
> julgar edge por backtest em abertura — só populações de sombra a odds
> CORRENTES com timestamp (H3 baseline, H5 ensemble) decidem GO; (3) zero
> aposta real continua sendo a única postura defensável.

> ## 🟢 FLAG LIGADA + H5 PRÉ-REGISTRADA (2026-07-17, mesmo dia)
>
> **`ensemble_xg.enabled: true`** — o serving (predict/prever/display) agora
> blenda com o atk/def-xG; toda predição blended sai carimbada
> `model: ensemble_xg` no predictions.jsonl. Após o merge, rodar
> `python -m src.cron_update_models` no repo principal para criar o cache
> (sem ele o serving degrada para baseline com aviso, nunca cai).
>
> **H5 pré-registrada**: `h5-ensemble-xg-sombra-2026` no trials.json
> (`scripts/registrar_h5.py` — script separado do governanca.py de
> propósito: re-rodar o governanca apagaria o sharpe 0.0722 observado da
> H1). Funil idêntico ao da H3 (OU2.5, edge 2–15%, sombra 0u), só muda a
> fonte da probabilidade. Decisão com n≥100 liquidados: CLV IC95 > 0 ∧
> ROI IC_lower > −2%. **A H3 segue baseline puro por construção**
> (sombra.py chama model.predict_match direto, imune à flag); a H5 roda em
> PARALELO nos mesmos jogos via `sombra_h5_*.jsonl` — o agendador diário
> (cron → settle → capture → report) cobre as duas sem mudança. Mudar
> blend/hiperparâmetros do ensemble é tentativa N+1. Suíte **298 verdes**,
> CI 5/5.

> ## 🟢 ENSEMBLE ATK/DEF-xG INTEGRADO AO SERVING, ATRÁS DE FLAG (2026-07-17)
>
> A simulação walk-forward 2025+2026 (`docs/SIMULACAO_2025_2026.md`)
> diagnosticou o modelo como calibrado-mas-sem-resolução e validou o
> **ensemble 50/50 baseline × atk/def estimado em xG**: dBrier 1X2 −0,0073,
> IC95 [−0,0122, −0,0019], significativo em cada ano isolado, OU2.5
> preservado. Acerto 1X2: 50,3% → 52,1%.
>
> **Integração**: `src/xg_model.py` (fit em 2 etapas: forças em
> 0,85·xG+0,15·gols, α/ρ nos gols reais; hiperparâmetros congelados pela
> validação 2024-H2) + cache `xg_model_parameters` (JSON, escrito pelo
> `cron_update_models` quando ligado) + hook único `maybe_blend` nos 3
> caminhos de serving (predict.show, display.compute, prever.py). Predição
> blended é carimbada `model: ensemble_xg` no predictions.jsonl.
>
> **`ensemble_xg.enabled: false` por padrão** — H1/H3 foram medidas com o
> baseline puro; ligar em produção exige pré-registro novo (governança).
> Flag OFF = serving byte a byte idêntico (testado). Suíte **293 verdes**,
> CI 5/5. Falha do ensemble degrada para baseline com aviso, nunca derruba.

> ## 🔵 AUDITORIA DE INTEGRAÇÃO COM O CORE v1.3.0 (2026-07-12)
>
> **Sincronização 100%**: vendor em **predictor_core v1.3.0-ga-20260711**
> (aggregate `3445e37f43c458cc`, sync 2026-07-12), byte a byte idêntico ao
> core canônico — drift zero. Consumo real: `contracts`, `testing`,
> `measurement`, `obs`; os 7 módulos não importados (kernel/rating, ledger,
> data, etc.) são omissões intencionais do roadmap (agosto/2026).
>
> **Duas duplicações identificadas — dívida de manutenção para a próxima
> janela de código** (não urgente em modo de observação):
> 1. Shin de-vig: `src/math_utils.shin_probabilities` (12 arquivos usam) vs
>    `core.measurement.calibration.shin_devig` (0 usam). A local devolve
>    `(probs, z, overround)` — interface mais rica; convergir quando o core
>    expor o equivalente.
> 2. Bootstrap: `src/bootstrap.py` reimplementa percentile bootstrap em vez
>    de compor sobre `core.measurement.bootstrap.bootstrap_ci` (que outros
>    scripts do repo já usam) — duas fontes de IC95% no projeto.
>
> Pendência W2 herdada do wc (bet_id no livro): **já fechada** — bet_log.py
> sincronizado com o fix de 2026-07-11 do wc-predictor-v2 + test_bet_id.py.
> Brasileirão em **modo de observação** (sombra automática; próxima marca:
> reexecutar varredura forward com N=40 —
> `docs/RELATORIO_FORWARD_18JOGOS_2026-07-12.md`).

> ## 🔴 BACKTEST CONCLUÍDO — VEREDITO NO-GO (2026-07-10, mesmo dia)
>
> Ciclo completo executado: coleta (1.165 eventos, 2024+2025+2026 parcial) →
> espelho (937 jogos + 228 fixtures) → cache (a=0.199 b=0.708 α=0.0006
> ρ=0.014) → harness PASSOU → H1/H2 pré-registradas → walk-forward (4 blocos
> de 19 rodadas, 1.673 apostas no funil).
>
> **H1 (OU2.5): NO-GO.** n=455, ROI +7,9%, **CLV open +19,55%**, PSR 0,94 —
> mas IC95 do pnl [−0,022, +0,172] cruza zero e DSR 0,94 < 0,95. Sinal de
> preço forte, conversão em lucro ainda sem significância. **Zero aposta
> real.** Investigação: ingerir 2023 (season_id 48982) e rodar 2026 em modo
> SOMBRA para ampliar N; NÃO variar configuração (N+1 deflaciona).
> **H2 (picks 1T ≥60%): VALIDADA informativa** — n=1.493, acerto 79,0% vs
> confiança 79,8%. **1X2 reproduziu a Copa: ROI −15,4%, CLV −6% — nunca.**
> Sharpes observados gravados no trials.json (denominador imortal).
>
> Detalhes e plano da retomada (16-17/07 jogos atrasados; rodada cheia
> 21/07): `docs/RELATORIO_BACKTEST_2026-07-10.md`. Suíte **241 verdes**,
> CI 5/5. odds_shop --from-file validado com snapshot de teste.

> ## 🟢 CRIAÇÃO DO DOMÍNIO (2026-07-10)
>
> **Projeto criado a partir do wc-predictor-v2 pós-Copa.** Backup limpo
> (sem .venv/__pycache__/.pytest_cache/worktrees/caches de coleta), repo git
> NOVO (histórico da Copa fica no wc-predictor-v2 original, intocado).
> Vendor no **predictor_core v1.1.0** — `sync_core --check` reporta os 4
> consumidores em sincronia, incluindo este. *(Superado: v1.3.0 desde
> 2026-07-11 — ver auditoria 2026-07-12 no topo.)*
>
> **Limpeza da Copa (PASSO 1.2)**: bets/bankroll/predictions/period_predictions
> zerados (arquivos mantidos); `results.jsonl` da Copa preservado como
> `results_wc2026_historico.jsonl` e um novo vazio criado; artefatos derivados
> (backtest_bets.csv, live_decisions.csv, bootstrap_cache.json, wc.log)
> removidos; `matches.db` manteve o SCHEMA e perdeu os DADOS do domínio Copa —
> decisão consciente: manter os ~49k jogos de seleções contaminaria a
> calibração do Poisson (o fit filtra por DATA, não por torneio) e o Elo de
> clubes não compartilha times com seleções. Base do Brasileirão nasce limpa.
>
> **Adaptações de domínio**: telemetria/logger `wc` → `brasileirao`
> (obs/ingest/predict/status/backtest/prever); constantes da Copa viraram
> config (`league`, `tournament_name`; display._tournament_avg e
> simulator.derive_groups agora leem config); smoke do CI usa
> Flamengo × Palmeiras; odds_shop com sport key configurável
> (`soccer_brazil_campeonato` — CONFIRMAR no /v4/sports com chave real).
> Simulador de bracket NÃO se aplica a pontos corridos (encerra com aviso).
>
> **Dados**: Sofascore ut_id **325**, seasons 2024=**58766**, 2025=**72034**,
> 2026=**87678** (descobertos via `--seasons 325` em 2026-07-10; a season
> "20/21" na lista é a temporada COVID — assinatura de que 325 é o Brasileirão).
> `matches` é alimentada por `scripts/sync_matches_from_sofascore.py`
> (upsert idempotente, tournament="Brasileirão Série A", neutral=0). **NÃO
> rodar `python -m src.ingest`** (repovoaria a base com seleções do martj42).
>
> **Governança (ordem obrigatória)**: `scripts/governanca.py` roda o harness
> de controle positivo (edge sintético: ataque do mandante ×1,3 no funil O/U
> real; ruído: jitter ±3pp pagando vig) → emite o atestado → pré-registra
> **H1** (OU2.5, edge 2–15%, walk-forward) e **H2** (picks 1T conf ≥60%,
> informativa) em `data/trials.json`. Só então
> `scripts/backtest_walkforward.py` (blocos de 19 rodadas, params
> recalibrados por bloco, Elo forward, bootstrap por cluster de jogo, DSR
> descontado pelo registro) produz o **GO/NO-GO**: PSR ≥ 0,80 ∧ IC_lower > 0 ∧
> DSR ≥ 0,95. **Nenhuma aposta real antes de GO.**
>
> Pendências herdadas do wc: W2 (bet_id uuid no livro), generalização do
> Ledger no core (agosto/2026 — até lá o bet_log é por domínio).

## O que é o projeto

Sistema CLI em Python que prevê resultados do Brasileirão Série A e opera
apostas de valor com governança anti-data-snooping. Roda 100% local
(Python + SQLite, sem cloud). Idioma do projeto: português.

Máquina do Leo: Windows, em `C:\Claude-projetos\Claude\brasileirao-predictor`,
atrás de proxy corporativo Volvo com inspeção TLS (resolvido em
`src/sofascore.py` via CA bundle do Windows). A coleta do Sofascore roda na
máquina do Leo (o sandbox de CI não alcança o Sofascore).

## Mapa rápido

- Motor: `src/ratings.py` (Elo+decay) → `src/model.py` (NB+Dixon-Coles, MLE)
  → `src/predict.py`/`src/display.py` (serving) — genérico, zero mudança.
- Coleta: `src/ingest_sofascore.py` (config-driven) →
  `scripts/sync_matches_from_sofascore.py` → `src/cron_update_models.py`.
- Pesquisa: `scripts/backtest_walkforward.py` (read-only, P12).
- Governança: `scripts/governanca.py` + vendor `measurement/trials.py`
  (TrialRegistry, DSR) + `testing/harness.py` (controle positivo).
- Operação: `scripts/odds_shop.py`, `src/bet_log.py`, `src/settle.py`.
- CI: `scripts/ci_check.py` (pytest + 4 barreiras estáticas/smoke).
