# Diagnósticos residuais — 2026-08-24

## Resumo executivo

- OU2.5-only dev: **`ARCHIVE_OU25_CURRENT_RESIDUAL`**, sem consumir 2024.
- T2-2026: **`RESULT_NOISE_NOT_PARAMETER_DRIFT`**.
- Internacional/Bahia: **força mal estimada**, não mando heterogêneo.
- prêmio teórico do mercado: **0,011193 RPS** no painel completo e
  **0,009477 RPS** quando o modelo previu mandante.
- estado econômico: `SOFASCORE_AGGREGATE_UNNAMED_DIAGNOSTIC_ONLY` e
  `CAPITAL_GATE: LOCKED`.

## MARKET-06 — OU2.5 dev-only

A trial foi registrada antes da ordenação, limitada a 2021–2023 e com
`validation_2024_allowed=false`. Coverage completa: 808 jogos. A MDE
aproximada para uma eventual validação de 380 jogos a odd 1,90 é 13,67% ROI.

| De-vig | Lado | n por faixa (<−5/−5–0/0–5/5–10/≥10pp) | ROI por faixa | Monotônico | Nulo monotônico |
| --- | --- | --- | --- | --- | ---: |
| Shin | Over | 283/306/163/53/3 | −4,72%/−3,43%/−16,55%/−22,74%/+116,67% | não | 10,0% |
| Shin | Under | 56/163/306/189/94 | −1,18%/−0,16%/−7,11%/−4,55%/−10,59% | não | 21,3% |
| Power | Over | 275/292/172/64/5 | −4,22%/−4,83%/−13,28%/−19,26%/+30,00% | não | 15,1% |
| Power | Under | 69/172/292/182/93 | −0,58%/−2,17%/−6,20%/−5,52%/−9,62% | não | 21,4% |

Nenhuma faixa atingiu o poder requerido para ROI alvo de 5%. O aparente salto
do Over ≥10pp sob Shin tem `n=3` contra requisito aproximado de 11.251 e não
é evidência. A formulação atual fica arquivada; 2024 não deve ser gasto nela.

## T2-2026 — drift ou ruído

Accuracy: 10/35 = 28,57%. Sob Binomial(35, 0,50), o intervalo preditivo 95%
para acertos é `[12,23]`; 10 fica fora.

| Lado | λ médio previsto | gols médios reais | previsto−real | IC95 pareado |
| --- | ---: | ---: | ---: | --- |
| Casa | 1,4532 | 1,1429 | +0,3104 | [−0,0360; +0,6567] |
| Fora | 1,0340 | 1,1143 | −0,0803 | [−0,3839; +0,2233] |

Ambos os intervalos incluem zero. A queda de accuracy é extrema, mas não há
drift marginal de lambda confirmado: **ruído de resultado**. Accuracy T2
histórica: 2022 48,42%, 2023 43,68%, 2024 46,32%, 2025 52,11% (`n=190` cada).

## Internacional e Bahia

Baseline de erro do modelo em 2026: 52,89%.

| Clube | Jogos | Erros | Erro mandante | Erro visitante | Veredito |
| --- | ---: | ---: | ---: | ---: | --- |
| Internacional | 23 | 16 | 75,00% (9/12) | 63,64% (7/11) | força mal estimada |
| Bahia | 23 | 16 | 58,33% (7/12) | 81,82% (9/11) | força mal estimada |

O excesso ocorre nos dois papéis. Não há campo de estádio/venue na base;
`matches.city` existe, mas está vazio nesses 32 registros e não pode ser usado
como proxy. Tarefa: enriquecer estádio/venue PIT por fonte declarada, sem
inferência.

### 32 jogos com erro

Internacional: 28/01 Internacional 0–1 Athletico; 04/02 Flamengo 1–1
Internacional; 25/02 Remo 1–1 Internacional; 15/03 Internacional 0–1 Bahia;
19/03 Santos 1–2 Internacional; 01/04 Internacional 1–1 São Paulo; 05/04
Corinthians 0–1 Internacional; 11/04 Internacional 0–0 Grêmio; 19/04
Internacional 1–2 Mirassol; 25/04 Botafogo 2–2 Internacional; 03/05
Internacional 2–0 Fluminense; 09/05 Coritiba 2–2 Internacional; 23/07
Internacional 1–2 Cruzeiro; 29/07 Internacional 1–1 Flamengo; 09/08 Palmeiras
0–0 Internacional; 17/08 Internacional 1–1 Remo.

Bahia: 28/01 Corinthians 1–2 Bahia; 05/02 Bahia 1–1 Fluminense; 12/02 Vasco
0–1 Bahia; 11/03 Bahia 1–1 Vitória; 15/03 Internacional 0–1 Bahia; 11/04
Mirassol 1–2 Bahia; 25/04 Bahia 2–2 Santos; 03/05 São Paulo 2–2 Bahia; 10/05
Bahia 1–2 Cruzeiro; 17/05 Bahia 1–1 Grêmio; 25/05 Coritiba 3–2 Bahia; 21/07
Atlético Mineiro 1–1 Bahia; 26/07 Bahia 1–1 Corinthians; 30/07 Fluminense 0–0
Bahia; 09/08 Bahia 0–0 Vasco; 16/08 Chapecoense 3–3 Bahia.

## Benchmark contra mercado — 2021–2024

| Temporada | n | RPS modelo | RPS mercado | prêmio mercado | Brier prêmio | Log-loss prêmio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2021 | 180 | 0,204551 | 0,189191 | 0,015360 | 0,030811 | 0,047259 |
| 2022 | 380 | 0,210715 | 0,203368 | 0,007347 | 0,015861 | 0,023245 |
| 2023 | 380 | 0,218833 | 0,210820 | 0,008013 | 0,017321 | 0,025513 |
| 2024 | 378 | 0,214532 | 0,198260 | 0,016272 | 0,033554 | 0,048306 |
| Total | 1.318 | 0,213309 | 0,202115 | **0,011193** | **0,023398** | **0,034366** |

| Turno | n | RPS modelo | RPS mercado | prêmio mercado |
| --- | ---: | ---: | ---: | ---: |
| 2021-T1 | 173 | 0,204178 | 0,189812 | 0,014365 |
| 2021-T2 | 7 | 0,213778 | 0,173823 | 0,039956 |
| 2022-T1 | 190 | 0,214916 | 0,205999 | 0,008918 |
| 2022-T2 | 190 | 0,206515 | 0,200737 | 0,005777 |
| 2023-T1 | 190 | 0,213526 | 0,205764 | 0,007762 |
| 2023-T2 | 190 | 0,224140 | 0,215876 | 0,008264 |
| 2024-T1 | 190 | 0,215589 | 0,198199 | 0,017390 |
| 2024-T2 | 188 | 0,213464 | 0,198322 | 0,015142 |

O `n=7` de 2021-T2 é consequência do burn-in de 200 jogos, não coverage
seletiva; não deve ser comparado isoladamente aos turnos completos.

Por confiança do modelo, o prêmio em RPS é 0,016625 para `<40%` (`n=318`),
0,012325 para 40–50% (`n=594`), 0,007296 para 50–60% (`n=299`) e −0,000343
para `≥60%` (`n=107`). A informação ausente concentra-se nos jogos menos
resolvidos pelo modelo.

### Recorte “modelo previu mandante”

`n=1.088`: RPS modelo 0,211410, mercado 0,201933; prêmio **0,009477**.

| P(mandante) do mercado | n | Vitória real | Empate real | RPS modelo−mercado |
| --- | ---: | ---: | ---: | ---: |
| <35% | 136 | 28,47% | 29,93% | +0,025950 |
| 35–45% | 257 | 42,02% | 26,85% | +0,008225 |
| 45–55% | 302 | 48,68% | 30,13% | −0,001305 |
| ≥55% | 393 | 65,14% | 19,59% | +0,012881 |

O mercado separa materialmente vitória de empate: sua probabilidade média de
mandante cresce de 29,54% para 63,05%, enquanto a taxa real cresce de 28,47%
para 65,14% e empates caem para 19,59% na faixa superior. O prêmio é tamanho
de alvo para arquitetura futura, não promessa de capturabilidade.

## Relógio e desvios

- MARKET-06 não abriu 2024; a validação segue não consumida nessa trial.
- O benchmark usa 2024 como diagnóstico da regra 1X2 já avaliada por MARKET-03,
  sem seleção ou novo gate.
- A reconstrução do serving congelado em 2026 usa 2025 somente como passado
  cronológico operacional; 2025 não selecionou parâmetros, thresholds ou
  hipóteses.
- SofaScore agregado não foi promovido a evidência econômica.

## Validação técnica

- suíte: 735 passed, 1 deselected, 3 warnings numéricos conhecidos;
- Ruff: verde;
- Pyright: 0 erros, 0 warnings;
- ledger JSON e `git diff --check`: verdes;
- nenhum commit ou push.
