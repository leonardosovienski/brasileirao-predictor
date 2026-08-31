# Ruff baseline

O primeiro scan completo de `src`, `scripts` e `tests` encontrou 965 achados. Principais regras:

| Regra | Quantidade inicial |
|---|---:|
| E702 | 364 |
| E501 | 237 |
| I001 | 95 |
| E701 | 91 |
| UP017 | 51 |
| E402 | 35 |
| F401 | 29 |
| F541 | 21 |
| E401 | 11 |

Por diretório: `src` 223, `brasileirao_predictor/research` 31, `scripts` 647 e `tests` 95; classificações podem se sobrepor em
`brasileirao_predictor/research`. Correções seguras foram aplicadas primeiro, seguidas por formatação e revisão manual. Os 85
goldens foram executados entre as etapas.

Baseline atual: **0 achados**, com `ruff check src scripts tests` e `ruff format --check src scripts tests`.
Não há ignore amplo nem exclusão de pesquisa/legado no Ruff.
