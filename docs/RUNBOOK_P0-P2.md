# Runbook P0 → P2 — sessão de 2026-08-22

> **NOTA DE ESTADO (2026-08-22, noite): este runbook é histórico.** P0/P2 já
> foram executados na máquina real. O estado operacional atual está no primeiro
> checkpoint de `HANDOFF.md`: H12 comprovada, ensemble desligado,
> `market_no_vig` implementado e suíte completa com 637 testes. Os comandos e
> medições abaixo permanecem para reprodução e para explicar as decisões; não
> interpretar a tabela antiga de `f0955ab` como estado presente.

> Complementa `docs/ROADMAP.md` (a fila priorizada) e `HANDOFF.md` (o estado).
> Aqui ficam os **comandos exatos** do P0/P2 e o **memorando de decisão do P1**,
> com as medições que sustentam a recomendação.
>
> Esta sessão rodou num container remoto, **sem acesso a `data/matches.db`**.
> Nada que dependa dos dados reais foi executado — os comandos abaixo são para
> a máquina do operador. As medições do P1 são de dados sintéticos e de
> aritmética pura, e não tocam o banco.

---

## Estado verificado no repositório (`f0955ab`)

| Artefato | Estado |
| --- | --- |
| `data/trials.json` | 11 trials, **sem a `h11`**. Vereditos: 2 refutadas, 2 substituídas, 4 inconclusivas, 2 exploratórias, 1 informativa. **Zero comprovadas** |
| `data/trials.harness_attestation.json` | `expires_at 2026-08-16`, `core_version 2.2.0`, `metric psr` — **expirada** |
| `reports/` | só `benchmark_baseline_v3_2026-08-20.json`, inválido como régua (atravessa o holdout) |
| `config.yaml` | `ensemble_xg.enabled: true` |
| painel | `--engine {dixon_coles,serving}`, default `dixon_coles`, `--retrain-every` default **100** |

---

## P0 — higiene

A ordem é sequencial de verdade: a attestation renovada precisa estar no repo
**antes** de o baseline v4 virar régua, e o controle negativo é o que autoriza
confiar nessa régua.

### P0.1 — commitar o que só existe na máquina

Antes de commitar, **conferir a attestation renovada**:

```powershell
Get-Content data\trials.harness_attestation.json
```

Checar três campos contra a versão do repo (`core_version 2.2.0`,
`metric psr`, `expires_at 2026-08-16`):

* `expires_at` tem de estar **no futuro**. Se já venceu de novo, renovar antes
  de qualquer medição — régua produzida sob attestation vencida não é régua.
* `core_version` e `metric` diferentes **não são cosméticos**: mudam o que foi
  atestado. Se mudaram, dizer por quê no corpo do commit.
* `pipeline_fingerprint` diferente é o esperado se o código mudou (PRs #25-#29
  mexeram no pipeline) — é justamente por isso que a attestation velha não serve.

```powershell
git add data\trials.json data\trials.harness_attestation.json reports
git commit -m "RESEARCH-01A: h11 refutada (IC95 cruza zero, n=1318) + attestation renovada"
git push -u origin main
```

Depois do commit, confirmar que a `h11` entrou:

```powershell
python -c "import json;t=json.load(open('data/trials.json'));print(len(t));print([(x['name'],x['status']) for x in t][-2:])"
```

Esperado: **12** trials (hoje são 11), a última com `name` da `h11`
(`h11-refit-cadence-rodada-vs-100jogos`) e `status` **refutada**.

### P0.2 — regerar o baseline v4

`--retrain-every` fica no default (100). Este é o braço **barato** — os ~22 min
do CONTROL do 01A, não as 4h30 do braço tratado.

```powershell
python scripts\benchmark_predictor.py --model H4_DIXON_COLES_CALIBRATED `
    --period 2021-01-01,2024-12-31 `
    --output reports\benchmark_baseline_v4_2026-08-22.json
```

Conferir na saída (`BENCHMARK_WRITTEN`):

* `n` ≈ **1318** — se divergir, o carregamento mudou e o pareamento com o 01A
  deixa de valer.
* `rps` ≈ **0,21687** — o CONTROL do 01A bateu exatamente com o v4 anterior.
  Se o ponto se mover, foi a correção de bootstrap/slope da PR #26 mordendo
  mais do que se supunha, e isso é achado, não ruído a ignorar.
* `metrics[0].delta_ci95` **não pode vir `null`** — é a primária (RPS), e era
  o bug 3 da #26. **Atenção:** `brier_ou25` vem com `baseline_value`, `delta` e
  `delta_ci95` todos `null` **por construção** (`_metric_record(...,
  baseline_value=None, ...)`), porque a climatologia do painel não define
  baseline de OU 2.5. Isso não é o bug 3 voltando.

  Consequência que vale registrar: o Roadmap §4 lista Brier OU2.5 como
  guardrail, mas a regra de promoção diz que guardrail só veta com o IC
  inteiro do lado ruim. Sem baseline não há IC — então **esse guardrail é hoje
  estruturalmente incapaz de vetar**. Corrigir isso muda a superfície de
  promoção e é decisão de pré-registro, não conserto de bug.
* ECE, `calibration_slope`, `resolution` e `sharpness` **não estão em
  `metrics`** — vivem em `guardrails_ou25`, calculados só para o mercado de OU
  2.5, não para o 1X2. O alvo de slope 0,9-1,1 do Roadmap §8 se lê ali.

### P0.3 — controle negativo

Os defaults já são os certos (`--period 2021-01-01,2024-12-31`,
`--permutations 3`, `--retrain-every 100`).

```powershell
python scripts\permutation_test.py --output reports\permutation_2026-08-22.json
```

**Custo:** 1 corrida de referência + 3 permutações = **4 walk-forwards** ≈ 1h30.
Não é o mais barato do P0 — planejar como bloco, não como checagem rápida.

Critério: skill contra climatologia tem de **colapsar para zero** nas
permutações. Códigos de saída (verificados em `main()`, `return 0 if passou
else 2`):

| código | significado |
| --- | --- |
| 0 | passou — nenhuma permutação bateu a climatologia com significância |
| 1 | recusa de guarda (ex.: `--period` alcançando o holdout) |
| **2** | **`beats_climatology` verdadeiro em dados sem sinal = vazamento** |

Com código 2, o P2 não roda: régua vazando mede vazamento.

---

## P2 — o ensemble de xG ajuda ou atrapalha?

Roda **depois** do P0.3 verde. Mesmo período, mesmo `retrain_every`, uma única
variável trocada (`--engine`) — é o pareamento que dá a resposta.

```powershell
python scripts\benchmark_predictor.py --model H4_DIXON_COLES_CALIBRATED `
    --engine serving --period 2021-01-01,2024-12-31 `
    --output reports\benchmark_serving_v1_2026-08-22.json
```

**Custo:** mais que o v4 — a `ServingStackEvaluator` reconstrói Elo + NB/DC +
ensemble de xG + calibração a cada refit, não só o MLE do DC — mas na casa de
dezenas de minutos, não das 4h30. **O P1 não bloqueia este experimento.**

> **Este comando não rodava até 2026-08-22.** `_run_walkforward` lia
> `pred.metadata["rho"]` sem condição, e a `ServingStackEvaluator` nunca
> expôs `rho` — a pilha de serving não é uma Dixon-Coles pura. `--engine
> serving` morria de `KeyError: 'rho'` **depois** do walk-forward inteiro,
> com qualquer banco. Corrigido: o serving passou a entregar `p_over` da
> própria grade servida, e o painel usa esse campo em vez de reconstruir uma
> DC por fora. Se você tinha tentado rodar o P2 antes e desistido, era isso.

Ler, nesta ordem:

1. `block_guard.xg_fit_failures` — **primeiro**. Vem inteiro no motor
   `serving` (e `null` no `dixon_coles`, que não tem ensemble para falhar). Se
   vier alto, o ensemble degradou para o baseline com frequência e a comparação
   não mede o que se pensa medir. Nesse caso o achado é o próprio índice de
   falha, não o RPS.
   Confirmar também `serves_production_model: true` no topo do relatório — é o
   carimbo de que o que rodou foi a pilha servida.
2. `n` — tem de bater com o v4. Sem o mesmo `n` não há comparação pareada.
3. RPS e o IC95 contra o v4.

Interpretação, pelas regras do Roadmap (§4 e §8):

* IC95 do delta **inteiro abaixo de zero** → o ensemble ajuda; segue ligado, e
  agora com prova.
* IC95 **cruzando zero** → inconclusivo com n≈1318. Vale a lição 1 do 01A: a
  largura do IC é ~0,0064 em RPS; efeito menor que isso é indetectável nesta
  amostra **por construção**. Registrar como inconclusiva e **não** desligar o
  ensemble com base em ponto estimado.
* IC95 **inteiro acima de zero** → serve-se um modelo pior que o baseline. É o
  achado mais urgente possível e passa na frente de tudo.

Em qualquer dos três casos: `accuracy` é `DIAGNOSTIC_ONLY` (Regra 12) e não
entra no veredito. Toda estratificação reportada carrega `n` (Regra 11).

---

## P1 — memorando de decisão: custo do walk-forward

**Nada foi alterado em `src/dixon_coles.py`.** Este bloco é a apresentação das
opções que o operador pediu antes de autorizar.

### O gargalo, lido no código

`fit_dixon_coles_parameters` (`src/dixon_coles.py:161`) chama
`minimize(..., method="L-BFGS-B")` **sem `jac`**. Duas multiplicações de custo:

1. **Por avaliação do objetivo**, um laço Python sobre os jogos que constrói
   uma `DixonColesMatrix` inteira por jogo — `_build_grid` monta
   `(max_goals+1)² = 121` células — **para ler uma única célula**,
   `score_prob(h, a)`. As outras 120 existem só para o normalizador.
2. **Sem jacobiano**, o scipy faz diferenças finitas sobre `2·n_times + 2` ≈ 42
   parâmetros → ~43 avaliações por passo de gradiente.

### A observação que muda a análise

O normalizador não precisa da grade. Como `τ ≡ 1` fora das 4 células magras, a
soma dupla colapsa em forma fechada:

```
Σ_{h≤M} Σ_{a≤M} P(h|λ)·P(a|μ)·τ(h,a)
    = F(M|λ)·F(M|μ)  +  Σ_{4 células magras} P·P·(τ−1)
```

Isto é uma **identidade algébrica**, não uma aproximação: mesma matemática,
121 células a menos por jogo. Verificado em 3.000 pares (λ, μ, ρ) aleatórios
na faixa do futebol — erro relativo máximo **1,2e-15**, o piso do float64.

### Medições (dados sintéticos, 20 times; nada do banco real)

Reprodutíveis com `python scripts/p1_cost_probe.py` — a sonda não abre o banco.
Os tempos variam com a carga da máquina; a tabela abaixo é de uma corrida sob
scipy 1.17.1. Numa corrida sob scipy 1.18.0 o fit completo deu 85x em vez de
95x, com os mesmos erros relativos.

Objetivo atual vs. reformulação vetorizada, mesmos parâmetros:

| n jogos | erro relativo do objetivo | 1 avaliação (atual) | 1 avaliação (vetorizado) | speedup |
| --- | --- | --- | --- | --- |
| 380 | 7,1e-16 | 50,2 ms | 0,57 ms | **89x** |
| 1000 | 1,2e-15 | 132,5 ms | 0,82 ms | **163x** |

Em passos de gradiente (43 avaliações por diferenças finitas, 1000 jogos):
**5,70 s** contra **0,035 s**.

Fit completo (`L-BFGS-B`, 380 jogos, mesmo `theta0` e mesmos bounds):

| | atual | vetorizado | diferença |
| --- | --- | --- | --- |
| tempo | 48,95 s | 0,514 s | **95x** |
| `wnll` | 356,974730122 | 356,974730118 | 3,6e-09 |
| `rho` | −0,005225678 | −0,005225270 | 4,1e-07 |
| `home_advantage` | 1,251092798 | 1,251091908 | 8,9e-07 |
| `converged` | True | True | — |
| max \|Δ\| em `attack` / `defense` | — | — | 3,8e-06 / 1,3e-06 |
| **max \|Δ\| em P(home/draw/away)**, 56 confrontos | — | — | **9,9e-07** |

A diferença residual **não é erro de fórmula** — o objetivo concorda a ~1e-15.
É o L-BFGS-B parando um passo diferente, porque o critério de parada compara
contra ruído de arredondamento que mudou de forma.

Evidência disso: repetindo a sonda sob **scipy 1.17.1** e **scipy 1.18.0**, os
resíduos do fit mudam (Δ`wnll` de 3,6e-09 para 1,3e-08; Δ máx em P(1X2) de
9,9e-07 para 4,5e-06) enquanto a concordância do **objetivo** fica cravada em
~1e-15 nas duas. Ou seja: o resíduo é propriedade do otimizador e da build do
scipy, não da reformulação. Tratar a faixa como **~1e-06 a 1e-05**, não como
uma constante.

Contra a largura do IC95 do 01A — **0,0064 em RPS** — mesmo o pior caso dessa
faixa fica ~3 ordens de grandeza abaixo da resolução do instrumento.

### As três opções, e o risco de cada uma

**Opção A — não mexer.** Risco zero na numérica; réguas seguem congeladas.
Custo: a agenda do Roadmap (01B, 02, 02B, 03, 04, 05, 06, 07, 08+) não fecha.
O P0 e o P2 rodam bem sem isso, mas o 02 — o *núcleo do upgrade*, que pede grid
search — é inviável a 4h30 por ponto.

**Opção B — normalizador fechado + vetorização em numpy (recomendada).**
~100x, matemática idêntica por identidade algébrica verificada. É a única das
três em que o risco é *mensurável antes de mexer* — e já foi medido acima.
Risco: o deslocamento de ~1e-06 a 1e-05 nos parâmetros ajustados — três a
quatro ordens de grandeza abaixo da largura do IC95 do 01A. Não move veredito
nenhum, e a mesma variação já existe hoje entre builds do scipy.

**Opção C — jacobiano analítico.** Elimina os ~43 evals por gradiente, ganho
adicional sobre B. Mas é derivação manual sobre 42 parâmetros, com a
renormalização e o `τ(ρ)` dentro; um sinal trocado dá um fit que *converge* em
lugar errado — falha silenciosa, o pior modo possível neste projeto. Exigiria
um teste de gradiente por diferenças finitas como guarda permanente.
**Não recomendo agora**: B já resolve o gargalo, e C é risco desproporcional
ao ganho marginal.

### Recomendação

**Opção B, e ela é implementação separada, não parte do P0.** Regra 6 — uma
alteração por experimento. Sequência sugerida:

1. Fechar o P0 e o P2 com o código atual. As réguas que saírem daí são as
   réguas do estado atual, e não dependem desta decisão.
2. Só então implementar B, numa PR isolada, com **duas guardas**: um teste que
   compara o objetivo novo contra o laço atual em parâmetros aleatórios
   (tolerância ~1e-12), e a regeneração do baseline v4 com o código novo.
3. **Re-congelar a régua** significa então *verificar*, não *re-executar tudo*:
   se o v4 regerado bater com o v4 do P0.2 dentro de ~1e-05 em RPS, os
   vereditos anteriores continuam válidos e isso fica registrado. Se não bater,
   aí sim há o que investigar — e é melhor descobrir com um baseline barato do
   que depois de meia agenda.

O ponto que decide: a 0,5 s por fit, um grid search do 02 deixa de ser projeto
de fim de semana e vira uma tarde. É o que destrava a TRACK A inteira.

---

## Ordem recomendada

```
P0.1 (commit)  →  P0.2 (v4, ~22min)  →  P0.3 (permutação, ~1h30)
                                            ↓ verde
                                        P2 (serving)
                                            ↓
                                        P1 opção B, PR isolada
```

P1 depois do P2, e não antes, por dois motivos: o P2 é a única pergunta da fila
cuja resposta pode ser urgente (se o ensemble atrapalha, serve-se um modelo pior
que o baseline há meses, e nenhuma otimização conserta isso); e o resultado do
P2 muda o cálculo do P1 — se o ensemble estiver atrapalhando, desligá-lo já
reduz o custo do walk-forward de serving sem tocar na numérica.

---

## Validação desta sessão

Sem `data/matches.db` não dá para executar os experimentos, mas dá para
validar os **comandos**. Os três foram rodados exatamente como estão escritos
acima (com `/` no lugar de `\`, num Linux): todos atravessam argparse, o
`load_config()`, a resolução do model tag e a guarda do holdout, e só param no
`sqlite3.connect(...mode=ro)` do banco ausente. Ou seja: **o que falta é o
dado, não o comando.**

Verificado ponto a ponto:

| Afirmação do runbook | Como foi checada | Resultado |
| --- | --- | --- |
| flags `--model/--period/--output/--engine/--retrain-every` | `--help` do painel | conferem |
| `--engine` aceita `serving` | comando do P2 rodado | construiu a pilha antes de falhar no banco |
| `--retrain-every` default 100 | `--help` + `RETRAIN_EVERY = 100` | confere |
| `H4_DIXON_COLES_CALIBRATED` resolve half-life | trial existe com `params.half_life_days: 360` | confere — sem isso cairia no `DEFAULT_HALF_LIFE = 120` calado |
| defaults do `permutation_test` | `DEFAULT_PERIOD = "2021-01-01,2024-12-31"`, `DEFAULT_PERMUTATIONS = 3`, `RETRAIN_EVERY` 100 | conferem — o comando sem flags já é o certo |
| custo = 4 walk-forwards | 1 corrida de referência + laço `for i in range(permutations)` | confere |
| guarda do holdout recusa 2025 | `--period 2021-01-01,2025-12-31` | recusou, código **1** |
| código 2 = vazamento | `return 0 if passou else 2` | confere |
| `metrics[0]` é RPS com `delta_ci95` | RPS é o único `is_primary=True` e recebe `_delta_ci95(...)` | confere |
| `block_guard.xg_fit_failures` existe | escrito no relatório; contador vive na `ServingStackEvaluator` | confere — vem `null` com `--engine dixon_coles`, o que é esperado |
| snippet de verificação do P0.1 | rodado no `trials.json` do repo | imprime `11` e as duas últimas trials |
| continuações PowerShell | sem espaço em branco depois de nenhuma crase | ok |

Estado do repositório na mesma sessão, com as dependências instaladas:

* `pytest` — **566 passaram**, 1 deselecionado (marcador `integration`). Bate
  com o número registrado no `HANDOFF.md`.
* `ruff check` e `ruff format --check` sobre o repo inteiro — limpos (218
  arquivos).
* `scripts/ci_check.py --fast` — **todas as barreiras verdes**. As barreiras
  [4/5] e [5/5] (smokes do predict) se auto-pularam por ausência do banco e
  emitiram WARN, que é o comportamento correto e não conta como falha.
* A barreira [3/5] varre `scripts/` inteiro atrás de `current_elo`/`load_elo`
  — é a que pegaria um script de pesquisa novo com lookahead. Inspecionou 14
  arquivos e passou; `p1_cost_probe.py` não abre banco nenhum, então nem entra
  na varredura.
* `pyright` reportou 75 erros pré-existentes em `src/` (ex.:
  `src/predict.py:136`, comparação `int | str`). **Não vêm desta mudança** —
  o `pyright` está configurado com `include = ["src"]` e o diff desta branch
  toca só `docs/` e `scripts/`. Provavelmente é uma versão de `pyright`
  resolvida diferente da usada quando o `HANDOFF.md` registrou "pyright
  limpo"; fica anotado como divergência a conferir, não como regressão.

Uma consequência prática do penúltimo item: `xg_fit_failures` só tem valor no
relatório do **P2**. No v4 ele vem `null`, e isso não é falha — é o motor
`dixon_coles` não ter ensemble de xG para falhar.
