# Roadmap de Execução — brasileirao-predictor

> **Status:** revisado em 2026-08-21, depois do primeiro veredito real da
> agenda de pesquisa (RESEARCH-01A → REFUTADA).
>
> Consolida o *Roadmap Técnico Consolidado v1.0-final* (que até aqui vivia só
> como arquivo solto na máquina do operador — uma sessão nova não tinha acesso
> a ele) e acrescenta a camada de EXECUÇÃO: o que já foi medido, o que mudou de
> prioridade e o que está bloqueando.
>
> Estado do repositório, caminhos na máquina do operador e histórico das
> sessões: ver `HANDOFF.md`.

---

## 1. Veredito estrutural

**ENGINEERING READY / SCIENTIFICALLY SOUND / PREDICTIVE MODEL STILL LIMITED /
ECONOMICALLY UNPROVEN / CAPITAL BLOCKED**

A engenharia e a governança estão maduras. O instrumento de medição está
completo e validado nos dois sentidos (controle positivo e negativo). O que
falta é a única coisa que importa: **demonstrar resolução preditiva e edge
econômico prospectivo**.

Placar atual: **12 trials registradas, ZERO comprovadas.**

---

## 2. Regras inegociáveis

> Problema conhecido se corrige **no mecanismo que o produz** — nunca se
> mascara com threshold, filtro de confiança, boost manual, escolha oportunista
> de subset ou calibração cosmética.

1. **2026 é território exploratório.** Nenhuma arquitetura se valida nele.
2. **Hiperparâmetro é prior de pesquisa** até validação. Nada herdado de
   experimento anterior é "aprovado" para arquitetura nova.
3. **Não mascarar no filtro o que o motor produz.** Empate baixo → corrigir
   lambdas. Favorito excessivo → corrigir estados. Lambda comprimido →
   corrigir a geração dos lambdas.
4. **Capital bloqueado** até gate pré-registrado. Sem exceção.
5. **P0 antes de tudo**: não perder dado prospectivo da H9 enquanto a pesquisa
   acontece.
6. **Uma alteração por experimento.** Nunca duas coisas ao mesmo tempo.
7. **Holdout de 2025 é intocável.** Se for usado para escolher hiperparâmetro,
   deixa de ser holdout. Os scripts recusam por padrão; `--unseal-holdout`
   existe e **não deve ser usado**.
8. **Trial preditiva ≠ trial econômica.** Gates separados; nunca forçar CLV em
   trial que não mede mercado.
9. **`SEM_PALPITE` é armadilha.** Accuracy alta com coverage baixo é
   cherry-picking, não melhoria.
10. **Nome de trial só no pré-registro real** — nunca reservado no roadmap.
11. **Toda estratificação carrega `n`.** Sem tamanho de amostra a métrica é
    ruído.
12. **Accuracy é `DIAGNOSTIC_ONLY`.** Nunca métrica de promoção.

---

## 3. Divisão temporal dos dados

| Período | Uso | Acesso |
| --- | --- | --- |
| 2021-2023 | Treino / burn-in | ✅ livre |
| 2024 | Validação / seleção de arquitetura e hiperparâmetro | ✅ livre |
| 2025 | **Holdout final selado** | ❌ intocado até a arquitetura estar congelada |
| 2026 | Exploratório / sanity | ⚠️ nunca como evidência confirmatória |
| 2027+ | Confirmação prospectiva / sombra | ✅ coorte verdadeiramente cega |

Na prática: todo experimento roda com `--period 2021-01-01,2024-12-31`.

---

## 4. Régua canônica

`scripts/benchmark_predictor.py` é o painel único.

**Primária:** RPS, com IC95 por bootstrap de bloco móvel.
**Guardrails:** Brier 1X2, Brier OU2.5, log-loss, ECE, calibration slope
(alvo 0,9-1,1), resolution, sharpness.
**Diagnóstico:** coverage, accuracy 1X2, hit rate OU2.5, variância de
`lambda_total`.

Promoção exige: **primária melhora com IC95 inteiramente abaixo de zero E
nenhum guardrail materialmente pior** (guardrail só veta quando o IC está
inteiro do lado ruim — guardrail que dispara com ruído vira veto arbitrário).

**Dois motores** (`--engine`):

* `dixon_coles` (default) — Poisson + DC puro. É o histórico.
* `serving` — a pilha que realmente prevê: Elo + NB/DC + ensemble de xG,
  reconstruída a cada refit sobre histórico truncado.

Baselines de skill score: só `climatology` está implementado. `elo_baseline`,
`current_v3` e `market_no_vig` falham alto se pedidos — nunca silenciam.

**Validação do instrumento** (as duas metades, ambas prontas):

* Controle **positivo**: `attest_pipeline_power` — a régua detecta sinal
  sintético.
* Controle **negativo**: `scripts/permutation_test.py` — a régua rejeita ruído
  nos dados reais. Se o modelo bater a climatologia com os resultados
  embaralhados, é vazamento, não modelo.

---

## 5. O que o 01A ensinou

`h11-refit-cadence-rodada-vs-100jogos` → **REFUTADA**. n=1.318, ganho de RPS
+0,001764, IC95 [−0,001650, +0,004750].

Três lições que mudam a execução daqui pra frente:

1. **Efeito pequeno não é detectável com n≈1.300.** O IC tem largura de
   ~0,0064 em RPS. Qualquer hipótese cujo efeito plausível seja menor que isso
   vai dar inconclusiva por construção. Antes de gastar CPU, pergunte: *o efeito
   esperado é grande o bastante para esta amostra enxergar?*
2. **Custo entra no veredito.** O braço tratado custou 12x o controle. Mesmo
   com IC positivo, 0,8% de RPS por 12x de custo não se paga.
3. **O pré-requisito era real.** Sem a guarda de bloco de kickoff, o braço com
   refit frequente teria ganhado por vazamento — falso GO.

---

## 6. Ordem de execução

### P0 — Higiene, antes de qualquer experimento novo

1. **Commitar o que só existe na máquina do operador**: `data/trials.json` (com
   a `h11`), `data/trials.harness_attestation.json` **renovada** (a do repo
   está expirada: 2026-08-16, core 2.2.0, metric psr) e o relatório do 01A.
2. **Regerar o baseline v4** com o código atual — o que existe saiu antes das
   correções de bootstrap e slope:
   ```
   python scripts/benchmark_predictor.py --model H4_DIXON_COLES_CALIBRATED \
       --period 2021-01-01,2024-12-31 \
       --output reports/benchmark_baseline_v4_<data>.json
   ```
   O `benchmark_baseline_v3` que está no repo é **inválido como régua**: foi
   medido até 2026, atravessando o holdout selado.
3. **Rodar o controle negativo** — confirma que nada mais vaza:
   ```
   python scripts/permutation_test.py --period 2021-01-01,2024-12-31
   ```

### P1 — A decisão que destrava (ou trava) tudo

**Custo do walk-forward.** `fit_dixon_coles_parameters` (`src/dixon_coles.py`)
avalia o objetivo num laço Python que constrói uma `DixonColesMatrix` inteira
**por jogo e por avaliação**, e o `minimize` roda **sem gradiente analítico** —
o scipy faz diferenças finitas sobre ~52 parâmetros, ~53 avaliações por passo
do gradiente.

Consequência: ~4h30 por experimento com refit por rodada. **A agenda abaixo tem
dezenas de experimentos.** Nesse ritmo ela não fecha.

Vetorizar em numpy ou fornecer o jacobiano daria ganho de ordens de grandeza.
**Mas mexe na numérica e pode mover resultados já congelados** — exige decisão
explícita do operador e re-congelamento das réguas depois.

*Enquanto isso não for decidido, tratar como o gargalo real do projeto.*

### P2 — A pergunta barata que nunca foi respondida

**O ensemble de xG que está LIGADO em produção ajuda ou atrapalha?**

`config.yaml` tem `ensemble_xg.enabled: true`, mas as trials H5 ficaram
"substituída" e "inconclusiva" — nunca houve medição limpa. Agora dá:

```
python scripts/benchmark_predictor.py --model H4_DIXON_COLES_CALIBRATED \
    --engine serving --period 2021-01-01,2024-12-31 \
    --output reports/benchmark_serving_v1_<data>.json
```

Comparar com o v4 (`--engine dixon_coles`) responde direto. Conferir também
`block_guard.xg_fit_failures`: se vier alto, o ensemble degrada para o baseline
com frequência e o que se mede não é o que se pensa medir.

**Se o ensemble estiver piorando, você serve um modelo pior que o baseline há
meses** — e isso é mais urgente que qualquer experimento novo.

### P3 — TRACK A (modelo esportivo), em sequência

Cada item é trial pré-registrada, uma variável por vez.

| Experimento | O que testa | Condição |
| --- | --- | --- |
| ~~01A~~ | refit por rodada vs. 100 jogos | ✅ **REFUTADA** |
| 01B | xG com janela única vs. curta+longa | controle barato de *recency* |
| 02 | estados dinâmicos curto/longo por clube | **núcleo do upgrade** |
| 02B | Elo ainda agrega depois de atk/def modelados? | só se 02 der GO |
| 03 | incerteza probabilística + shrinkage por precisão | só se 02 der GO |
| 04 | ambiente de gols dinâmico (`mu_t`) | só se 02 der GO |
| 05 | priors de promovido / retornando | só se 02 der GO |
| 06 | HFA dinâmico, depois hierárquico | só se 02 der GO |
| — | **congelar o melhor motor de lambda** | depois de 02-06 |
| 07 | NB+DC vs. Bivariate Poisson vs. Conditional Poisson | com os MESMOS lambdas |
| 08+ | features de contexto, uma por trial, com checklist PIT | depois de 07 |

Em 02, `mu` e HFA ficam **congelados** (viram experimento próprio em 04 e 06),
e a contribuição do Elo fica no valor atual. `attack_signal` trabalha em espaço
**log-rate**, não em gols crus.

Priors de pesquisa para 02 (**não** são valores aprovados; calibrar por grid
search em 2021-2024, com 2024 como validação): `alpha_short≈0.3`,
`alpha_long≈0.05`, `w_xg=0.85`, `ridge_reg=1.0`, `eps=0.1`.

### P4 — TRACK B (mercado), **em paralelo**

Independe da TRACK A e está mais adiantada do que parece:
`src/research/market_residual.py` já implementa o resíduo com logit do mercado
como *offset* (essencialmente o MARKET-02), e `src/research/residual_gate.py`
já tem o gate econômico com PSR e bootstrap.

| Experimento | Estado |
| --- | --- |
| MARKET-01 — consenso de casas, com de-vig individual antes do consenso | falta |
| MARKET-02 — multinomial residual com offset de mercado | ~pronto |
| MARKET-03 — features de contexto no residual, uma por trial | falta |
| MARKET-04 — coorte prospectiva em sombra | falta |

Parâmetros de consenso (`median` vs. `trimmed_mean`, `minimum_books`,
ponderação) escolhem-se por **robustez probabilística** no desenvolvimento
2021-2024 — **nunca pelo ROI**.

Gate econômico do MARKET-04: ROI IC95_lower > 0, CLV IC95_lower > 0, PSR ≥
0,80, DSR ≥ 0,95. **Shadow only** — nunca promover na mesma amostra da
concepção.

### P5 — Pendências menores

* **Baseline `market_no_vig`** — o teste de teto. Se o modelo não bate o
  fechamento sem vig, não há edge econômico. Depende da cobertura de odds
  históricas na base.
* **Linha órfã de jogo adiado** — PK de `matches` é
  `(date, home_team, away_team)`; adiamento muda a data e a linha antiga fica.
  Exige migração de schema (`event_id` em `matches`).
* **Encoding de acentos** no `by_team` do relatório (`AtlÃ©tico Mineiro`) —
  cosmético, na ingestão do Sofascore.

---

## 7. Integração entre as trilhas

**Não fundir automaticamente.**

* TRACK A boa, B ruim → sport model puro.
* TRACK A marginal, B boa → market residual.
* Ambas boas em regimes diferentes → ensemble ponderado por regime, com
  pré-registro.
* A melhora predição e B acha edge → **duas trials separadas**; nunca misturar
  os gates.

---

## 8. Meta realista

Não usar "70% de accuracy" — não é atingível em futebol (os melhores modelos do
mundo ficam em 52-56%; o limite é do esporte, não do código).

| Métrica | Direção | Threshold |
| --- | --- | --- |
| RPS | ↓ | significativo vs. baseline (IC95 abaixo de zero) |
| Brier | ↓ | significativo vs. baseline |
| Log-loss | ↓ | melhora ou não piora materialmente |
| Calibration slope | ≈1 | 0,9-1,1 |
| ECE | ↓ | < baseline |
| Resolution | ↑ | > baseline |
| RPS skill score | ↑ | > 0 |
| Consistência temporal | ✅ | robusto em múltiplas temporadas |
| Holdout selado | ✅ | 2025 intocado até a decisão final |

E só depois disso: *"essa melhora aparece de forma prospectiva contra preço de
mercado?"*
