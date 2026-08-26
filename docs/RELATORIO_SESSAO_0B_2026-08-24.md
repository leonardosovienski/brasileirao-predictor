# Relatório da sessão 0B — 2026-08-24

## Veredito executivo

**`NO_GO_STRUCTURAL`**. Em desenvolvimento 2021–2023 (`n=940` após burn-in),
BTTS apresentou `std=0,012855485`, abaixo do gate congelado de `0,02`.
OU2.5 passou isoladamente, mas a política exige que ambos passem. O runner
encerrou antes de carregar 2024. Capital: **`LOCKED`**.

## Integridade e relógio

- banco: 49.508.352 bytes; SHA-256
  `8A3A2415AAB9B8525708EE18EE7B3FB360B40031904095F5C71B35871E5946CD`;
- desenvolvimento bruto: 1.140 jogos; painel após burn-in: 940 previsões;
- `validation_2024_loaded=false`;
- `holdout_2025_touched=false`;
- `diagnostic_2026_touched=false`.

## Tabela de variância 0B

| Medida | OU2.5 | BTTS |
| --- | ---: | ---: |
| média | 0,398467753 | 0,441895979 |
| desvio-padrão populacional | 0,026911810 | 0,012855485 |
| variância | 0,000724246 | 0,000165263 |
| mínimo | 0,365598890 | 0,356549242 |
| máximo | 0,565409310 | 0,465300497 |
| range | 0,199810421 | 0,108751256 |
| P10 | 0,375794046 | 0,426908770 |
| P90 | 0,434516257 | 0,456443618 |
| P90−P10 | 0,058722210 | 0,029534848 |
| coverage de odds no desenvolvimento | 808/940 (85,96%) | 809/940 (86,06%) |
| gate de resolução | PASS | **FAIL** |

Histograma em bins de 5pp (somente bins não vazios):

| Faixa | OU2.5 n | BTTS n |
| --- | ---: | ---: |
| 0,35–0,40 | 624 | 13 |
| 0,40–0,45 | 275 | 672 |
| 0,45–0,50 | 30 | 255 |
| 0,50–0,55 | 10 | 0 |
| 0,55–0,60 | 1 | 0 |

## Distribuição de lambda total

`n=940`, média `2,280226749`, std `0,103328106`, variância `0,010676698`,
mínimo `2,156525994`, máximo `2,952029340`, range `0,795503346`, P10
`2,194511129` e P90 `2,416514155`. A concentração confirma a amarra escalar
do serving; BTTS permanece comprimido apesar da variação observada em OU2.5.

## Gates e blocos

- 1.1 variância estrutural: **NO_GO_STRUCTURAL** por BTTS.
- 1.2 coverage por temporada 2021–2024: não executado; o gate anterior proíbe
  carregar 2024. A coverage de desenvolvimento foi registrada apenas como
  diagnóstico secundário.
- 1.3 protocolo completo e validação única 2024: não executados.
- 1.4 comparação bônus com H1: não executada; H1 não foi reaberta.
- Blocos 2–5: não executados, pois o prompt manda ir diretamente ao Bloco 6
  após `NO_GO_STRUCTURAL`.
- Drift versus ruído T2-2026: **não avaliado**.
- Inter/Bahia: **não avaliado**.
- Prêmio teórico contra mercado: **não estimado**.
- MARKET-05: permanece dependente do coletor Pinnacle×soft; nenhuma simulação
  com SofaScore agregado foi feita.
- Live: permanece `HOLD_NO_LIVE_VIABILITY_GO`.

## Árvore de decisão ocupada

`0B NO_GO_STRUCTURAL → pré-jogo com modelo atual encerrado em todos os
mercados → energia para coletor Pinnacle×soft (Gate A1) e estudo live`.

## Próxima ação única recomendada

Implementar e operar o coletor append-only de snapshots PIT Pinnacle×soft até
satisfazer o Gate A1 (cinco ou mais casas nomeadas, sete dias consecutivos,
coverage auditável de pelo menos 90% e auditoria humana de 50 matches), sempre
em `SHADOW_ONLY`, sem picks, stake ou liberação de capital.

## Desvios explícitos do prompt

1. Coverage 2024, protocolo completo, pergunta bônus e Blocos 2–5 não foram
   executados porque o gate 1.1 determinou encerramento imediato e proibiu
   carregar 2024.
2. Não foi possível preencher números de drift, Inter/Bahia ou prêmio teórico
   sem contrariar essa árvore de gates; os campos permanecem não avaliados.
3. A pesquisa live não foi atualizada nesta sessão porque o fluxo saltou ao
   Bloco 6. O estado anterior `HOLD_NO_LIVE_VIABILITY_GO` foi preservado.

## Validação técnica

- suíte completa: **732 passed, 1 deselected, 3 warnings conhecidos**;
- Ruff: **verde**;
- Pyright: **0 errors, 0 warnings**;
- `git diff --check`: verde;
- dependências sincronizadas pelo `uv.lock` (`predictor-core 2.3.0`, Numba
  0.66.0); a primeira corrida fora do ambiente travado falhou em quatro testes
  por `predictor-core 2.2.0` e ausência de Numba, e foi substituída pela corrida
  canônica acima;
- nenhum commit ou push foi feito.
