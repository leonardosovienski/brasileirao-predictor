# Roadmap de Execução — brasileirao-predictor

> O histórico consolidado do raciocínio, incluindo hipóteses formais,
> tentativas técnicas, ideias ainda não testadas e caminhos rejeitados, está
> em `docs/PROJECT_LOGIC_REGISTER.md`.

> **Atualização 2026-08-24:** o sweep da seção 17 do registro testou todas
> as variações simples disponíveis sem tocar em 2025. Nenhuma passou
> desenvolvimento 2021–2023 + validação 2024. A meia-vida NB/DC de 360 dias,
> embora agora corretamente conectada, deu NO-GO preditivo contra pesos
> uniformes. O próximo passo não é mais tuning dos mesmos controles: exige
> informação PIT nova ou arquitetura causal nova.

> Previsões operacionais devem seguir `docs/PREDICTION_PROTOCOL.md` e passar
> pelo gate executável de `docs/PREDICTION_REQUIREMENTS.md`. A divisão temporal
> científica abaixo não autoriza omitir, no serving, resultados que já eram
> conhecidos antes de uma previsão de 2026.

> **Status:** revisado em 2026-08-22 à noite. Há 14 trials: H12 comprovada e
> H13 pré-registrada. O serving resolve contra climatologia, mas perde do
> mercado de fechamento sem vig. TRACK A02 (primeira formulação) e MARKET-02
> 1X2 foram medidos nesta data e deram NO-GO; nenhum foi promovido.
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

**ENGINEERING READY / SCIENTIFICALLY SOUND / PREDICTIVE RESOLUTION DEMONSTRATED /
ECONOMICALLY UNPROVEN / CAPITAL BLOCKED**

A engenharia e a governança estão maduras. O instrumento de medição está
completo e validado nos dois sentidos (controle positivo e negativo). O que
falta é a única coisa que importa: **demonstrar resolução preditiva e edge
econômico prospectivo**.

Placar atual: **14 trials registradas, 1 comprovada, 1 pré-registrada e 12 fechadas.**

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

Baselines de skill score: `climatology` e `market_no_vig` estão implementados.
O segundo usa fechamento 1X2 de-vigado por Shin e pareamento na mesma amostra;
`elo_baseline` e `current_v3` falham alto se pedidos — nunca silenciam.

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

### P0 — Higiene — ✅ **CONCLUÍDO em 2026-08-22**

Os três itens fecharam. Artefatos commitados, baseline v4 regerado
(`n=1318`, RPS 0,216870) e controle negativo **PASSOU nos dois motores**
(`reports/permutation_2026-08-22.json` para o `dixon_coles`,
`reports/permutation_serving_2026-08-22.json` para o `serving`).

### P1 — Custo do walk-forward — **reavaliar antes de decidir**

`fit_dixon_coles_parameters` avalia o objetivo num laço Python sem gradiente
analítico (~42-52 parâmetros por diferenças finitas). Media-se o ganho de uma
reformulação exata em `scripts/p1_cost_probe.py`: **~85-95x**, com o objetivo
concordando a ~1e-15 (o normalizador da grade DC tem forma fechada — τ ≡ 1 fora
das 4 células magras).

**Mas o gargalo é de UM motor.** Medido em 2026-08-22:

| motor | ajuste por refit | 1318 previsões |
| --- | --- | --- |
| `dixon_coles` | `fit_dixon_coles_parameters`, ~42-52 params | **~20 min** |
| `serving` | `model.fit_goal_model`, 4-5 params | **~3 s** |

O motor lento **não é o que se serve**. A agenda da TRACK A poderia rodar sobre
`--engine serving` em segundos — mas trocar de motor troca a régua, e todas as
medições congeladas são do `dixon_coles`. **Decidir isto antes de mexer na
numérica.** Opções e riscos em `docs/RUNBOOK_P0-P2.md`; `src/dixon_coles.py`
segue intocado.

### P2 — ensemble xG — **RESPONDIDO / H12 COMPROVADA**

O ensemble foi medido pareado em 2021–2024 (`n=1318`) e piorou todas as
métricas: delta RPS +0,004410, IC95 [+0,001436,+0,007741]. A trial
`h12-ensemble-xg-ligado-vs-desligado` foi comprovada e
`ensemble_xg.enabled` está `false`. Não religar sem hipótese nova.

Comando histórico/reprodutível do motor de serving:

Os quatro IC acima de zero: o ensemble piorava **todas** as métricas.
`ensemble_xg.enabled: false` desde então, com a justificativa no `config.yaml`.

O relatório canônico é `reports/benchmark_serving_noxg_2026-08-22.json`; o
contraste pareado está no relatório da H12 descrito no `HANDOFF.md`.

### P3 — TRACK A (modelo esportivo), em sequência

Cada item é trial pré-registrada, uma variável por vez.

| Experimento | O que testa | Condição |
| --- | --- | --- |
| ~~01A~~ | refit por rodada vs. 100 jogos | ✅ **REFUTADA** |
| 01B | xG com janela única vs. curta+longa | controle barato de *recency* |
| 02 | estados dinâmicos curto/longo por clube | primeira formulação NO-GO; reformular antes de nova medição |
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

Independe da TRACK A. `src/research/market_residual.py` contém os motores
binário e multinomial com o mercado como *offset*, e
`src/research/residual_gate.py` contém o gate econômico com PSR e bootstrap.
O primeiro contraste multinomial MARKET-02 foi executado e falhou; isso não
invalida a infraestrutura, mas impede promover essa especificação.

| Experimento | Estado |
| --- | --- |
| MARKET-01 — consenso de casas, com de-vig individual antes do consenso | falta |
| MARKET-02 — multinomial residual com offset de mercado | **NO-GO** em 2024; residual do serving piorou a abertura |
| MARKET-03 — features de contexto no residual, uma por trial | falta |
| MARKET-04 — coorte prospectiva em sombra | falta |

Parâmetros de consenso (`median` vs. `trimmed_mean`, `minimum_books`,
ponderação) escolhem-se por **robustez probabilística** no desenvolvimento
2021-2024 — **nunca pelo ROI**.

Gate econômico do MARKET-04: ROI IC95_lower > 0, CLV IC95_lower > 0, PSR ≥
0,80, DSR ≥ 0,95. **Shadow only** — nunca promover na mesma amostra da
concepção.

### P5 — Pendências menores

* **Baseline `market_no_vig`** — implementado para 1X2. Em 2021–2024 o
  serving perdeu do mercado (RPS delta +0,011240, IC95
  [+0,006923,+0,015455], n=1316); capital continua bloqueado. Não estender o
  teto a OU2.5 na mesma base: cobertura de 2023–2024 é só 66%/63%.
* **Linhas órfãs de jogos adiados — corrigido.** O bruto é preservado e
  marcado como superseded; o espelho `matches` usa `event_id`, exclui as
  versões substituídas e mantém 380 jogos concluídos em 2021–2025.
* **Encoding de acentos** no `by_team` do relatório (`AtlÃ©tico Mineiro`) —
  cosmético, na ingestão do Sofascore.
* **Stats de jogador:** `player_comp_stats` contém 5.210 agregados 2021–2026
  derivados dos caches de lineup Sofascore, com fonte e `available_at`.
  Consumidores PIT devem respeitar esse relógio; o agregado final da temporada
  não é feature válida para jogos anteriores da mesma temporada.

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
