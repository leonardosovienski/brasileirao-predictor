# Auditoria integral OU2.5 — 2026-08-28

## Escopo e regra de decisão

A auditoria foi retomada sobre o repositório público `https://github.com/leonardosovienski/brasileirao-predictor`, com a `main` sincronizada para o commit-base solicitado `bec073dcb748dbac63cffe737496f6a7ed8825ac`. O pai imediato do commit é `1d83b02b83bbd8d7a14bc66deef93bb969711328`. O working tree estava limpo antes das alterações desta auditoria e nenhum arquivo local existente foi descartado.

O objetivo foi confrontar implementação, dados, testes, artefatos, hipóteses, resultados e documentação. A regra científica permanece conservadora: replay estritamente temporal, seleção aninhada somente no passado, bloco seguinte sem retuning, registro de combinações perdedoras, Holm por família declarada, comparação com apostar sempre/não apostar/mercado de-vigado e separação entre probabilidade, EV conservador e força 0–100. 2024–2026 são observados/contaminados; não foram tratados como validação prospectiva nova. Capital e Kelly permanecem desabilitados, a política continua `NO_BET` e a força máxima permanece 40 até existir evidência prospectiva A1.

## Achados priorizados

| Prioridade | Achado | Evidência | Estado |
|---|---|---|---|
| Alta | O replay OU2.5 externo e interno cortava por índice e podia dividir jogos com o mesmo `kickoff_at` entre treino e teste. O label de um jogo simultâneo podia contaminar a seleção/ajuste de outro jogo do mesmo instante. | Regressão sintética com quatro jogos no mesmo kickoff falhava no commit-base; o primeiro fold tinha treino de 20 linhas e iniciava o teste no meio do grupo. | **Corrigido** com limites por grupo de kickoff no replay externo, no replay interno e no ancoramento. |
| Alta | O gate de odds `1,20–5,00` e overround `1,00–1,30` existia apenas no gerador anual. `score_row` aceitava o placeholder `51,0/1,002`; o ancoramento e políticas de certeza também não tinham gate compartilhado. | Regressão sintética reproduziu um pick emitido para `51,0/1,002`. | **Corrigido** por `valid_ou25_price_pair`, reutilizado pelo scorer, baseline, ancoramento, certeza e relatório anual. |
| Média | Os manifestos dos replays publicados referem-se ao commit de geração `1d83b02...` e a um SHA de `data/matches.db` operacional que não está no clone limpo. Os hashes declarados dos artefatos não batem com os bytes presentes no checkout atual. | O verificador encontrou todos os três hashes de artefatos divergentes em cada manifesto nested e 13 hashes divergentes no manifesto anual; o backfill público, por outro lado, bate byte a byte com seu próprio SHA. | **Não reescrito**: os artefatos históricos foram preservados. O fato foi registrado como limitação de reprodução e não como evidência de corrupção. |
| Média | Os smokes de serving e live da barreira CI não puderam rodar porque `data/matches.db` não é versionado e está ausente no sandbox. | `scripts/ci_check.py` ficou verde, mas reportou os dois smokes como `PULADO (sem banco)`. | **Bloqueio ambiental explícito**, sem fabricar banco ou resultado. |
| Média | A suíte .NET não pôde ser executada porque o SDK `dotnet` não está instalado no sandbox. | Restore/teste não iniciado; o estado foi registrado como `DOTNET_NOT_INSTALLED`. | **Não contado como aprovação**. |
| Baixa | A suíte do commit-base tinha cobertura insuficiente para simultaneidade no funil OU2.5 e para odds-placeholder fora do gerador anual. | As duas novas regressões falharam antes do fix e passaram depois dele. | **Corrigido** com quatro testes novos no total. |

## Correções implementadas

O núcleo `src/research/ou25_nested_replay.py` agora possui um gate finito e plausível para pares OU2.5 e helpers que recuam o início para o primeiro jogo de um grupo de kickoff e avançam o fim até o término do grupo. O replay externo e cada replay interno ajustam o limite antes de construir o prefixo; nenhum jogo com o mesmo instante do primeiro teste pode entrar no treino. O ancoramento usa o mesmo corte e exclui odds inválidas antes da comparação de Brier. A sua função de perda também usa explicitamente a probabilidade esportiva original não ancorada quando essa coluna existe, evitando mistura recursiva entre previsão já transformada e previsão original.

`score_row` agora bloqueia qualquer par ausente, não finito, fora do intervalo plausível ou com overround fora do intervalo contratado. Odds de fechamento só alimentam CLV quando o par de fechamento também passa o mesmo gate; preço agregado retrospectivo continua sem CLV elegível. O gerador anual conserva o alias privado `_valid_price_pair` para compatibilidade dos testes, mas delega a regra ao único gate compartilhado.

O congelamento de candidato passou a registrar contagens por lado e faixa de odd e verificações de estabilidade por pior temporada, pior lado e pior faixa. A elegibilidade retrospectiva exige amostra total, mínimo por lado/faixa, estabilidade não negativa, limite inferior de ROI positivo e limite inferior de CLV positivo. A elegibilidade nunca habilita capital: o estado operacional continua `NO_BET`, capital falso e força máxima 40.

Foram adicionadas regressões para: grupo de kickoff simultâneo no replay aninhado; placeholder `51,0/1,002` no scorer; grupo simultâneo no ancoramento; exclusão de preço inválido no ancoramento; e os gates de estabilidade/amostra mínima do congelamento de candidato. Todas as alterações de código foram formatadas pelo Ruff.

## Testes e validações executados

| Verificação | Resultado |
|---|---|
| Regressão antes do fix | 2/2 falharam, reproduzindo os dois defeitos principais |
| Regressão OU2.5 após o fix | 16 passed em replay, ancoramento, anual e congelamento de candidato |
| Suíte Python completa após o fix | **814 passed, 1 deselected, 3 warnings**; o total foi atualizado após a regressão de congelamento de candidato |
| Ruff format | passou; 296 arquivos formatados |
| Ruff check | passou |
| Pyright | `0 errors, 0 warnings, 0 informations` |
| `scripts/ci_check.py` | verde; cinco barreiras reportadas, com smokes predict/live pulados por ausência do banco |
| .NET | não executado: SDK ausente; não contado como aprovação |
| JSON estrito | 81 JSONs lidos; nenhum `NaN`, `Infinity` ou erro de parsing |
| Ledger de trials | 29 entradas, 29 nomes únicos, 0 sem status |
| Backfill SQLite | integridade `ok`, 1.140 linhas, 0 não conciliadas |
| Gate de preços no backfill | 1.140/1.140 pares válidos; nenhum não finito; overround de 1,05045 a 1,08059 |

Os três avisos Python são os warnings conhecidos de `rho=0,4000` cravado no limite do teste sintético. Eles não foram ocultados nem reinterpretados como ganho de modelo.

## Auditoria de dados e proveniência

O backfill público `reports/ou25_v2/ou25_backfill.sqlite` contém 380 partidas por temporada em 2021–2023 e SHA-256 `73a31a5ca780a03b35a06631bc5410b87046fb385b9541e2a929290bb3f7f980`. O manifesto declara corretamente que os preços são agregados retrospectivos, sem bookmaker nominal e sem horário de captura; portanto não são elegíveis para CLV executável, A1 prospectivo ou capital. O arquivo não foi usado para inventar `data/matches.db` nem para preencher snapshots A1.

O banco operacional `data/matches.db`, os ledgers locais e os snapshots A1 não são versionados e não estavam presentes. Por isso, não foi possível regenerar honestamente o caminho completo de serving a partir do commit-base. Os manifests nested e anual preservam dependência de um banco operacional específico e de artefatos produzidos no commit `1d83b02...`; a auditoria os trata como resultados publicados historicamente, não como uma nova execução byte-a-byte deste checkout.

Os artefatos publicados ainda reconciliam internamente os seus próprios números. O relatório anual tem 1.682 perdas individuais e lucro contrafactual total de `-15,041` unidades, exatamente igual à soma dos CSVs por temporada. A política governada fez zero apostas e zero unidades. Os nested serving e Dixon–Coles registram, respectivamente, 6.480 avaliações em quatro folds; o serving tem dois picks e o Dixon–Coles não tem picks. Como os preços são agregados retrospectivos, CLV fica nulo e nenhum desses números é prova de executabilidade.

## Hipóteses, seleção e resultados

O ledger mantém 29 hipóteses com nomes únicos e estados explícitos. A documentação registra desenvolvimento 2021–2023, validação histórica 2024, holdout 2025 aberto/contaminado por solicitação explícita e 2026 exploratório/contaminado. A auditoria não promoveu nenhuma hipótese a partir de 2025 ou 2026 e não executou tuning nesses conjuntos.

A grade fatorial publicada preserva 1.620 combinações por fold e 77.760 avaliações no pacote fechado, com resultados ruins incluídos. A correção de Holm permanece declarada. Os baselines de apostar sempre, não apostar e mercado de-vigado permanecem conceitualmente separados; o mercado de-vigado é benchmark probabilístico, não aposta executável. Os relatórios também separam chance do resultado, EV conservador com haircut/fricção e força da indicação.

O resultado anual contrafactual é o seguinte:

| Temporada | n | Resultado | ROI | IC95 inferior do ROI | Estado |
|---|---:|---:|---:|---:|---|
| 2021 | 180 | −31,630 u | −17,57% | −30,77% | retrospectivo exploratório |
| 2022 | 380 | −40,470 u | −10,65% | −19,95% | retrospectivo exploratório |
| 2023 | 380 | −32,360 u | −8,52% | −19,06% | retrospectivo exploratório |
| 2024 | 149 | −0,154 u | −0,10% | −16,84% | observado/contaminado |
| 2025 | 374 | +89,450 u | +23,92% | +13,20% | observado/contaminado |
| 2026 parcial | 219 | +0,123 u | +0,06% | −11,36% | parcial/contaminado |

O ganho de 2025 permanece uma observação retrospectiva contaminada, feita com preço agregado sem capture time e sem bookmaker executável. Mesmo retirando os cinco maiores ganhos do CSV de 2025, a soma ainda é positiva, mas essa análise de sensibilidade não remove seleção retrospectiva, não restaura cegamento e não cria CLV. Ela é apresentada somente como diagnóstico de concentração, não como validação.

As perdas individuais permanecem em `reports/ou25_v2/ou25_annual_2021_2026/ou25_20{21,22,23,24,25,26}_individual_losses.csv` e no nested serving em `reports/ou25_v2/ou25_nested_serving/individual_losses.csv`. Nenhuma perda, odds, captura, lucro ou snapshot foi fabricado nesta auditoria.

## Estado congelado e próximo gate legítimo

O candidato congelado continua nulo, com ação `NO_BET`, capital desabilitado, Kelly desabilitado e força máxima 40. A promoção futura exige uma coorte A1 prospectiva, candidato pré-registrado antes do primeiro label, bookmaker nomeado, timestamp PIT, pelo menos 200 liquidações, mínimo de 30 por lado e por faixa populada, IC inferior de ROI e CLV estritamente positivo, estabilidade temporal/lateral/por faixa, correção de multiplicidade e autorização humana separada. 2024–2026 não podem cumprir esse papel.

A única conclusão econômica honesta é ausência de evidência prospectiva de vantagem. Nenhuma promessa de lucro foi feita, e o resultado contrafactual não autoriza aposta, promoção, capital ou ajuste de força.

## Manifesto e reprodução

O manifesto desta auditoria fica em `reports/ou25_v2/audit_2026-08-28/manifest.json`. Ele registra o commit-base, o estado de reprodução, os hashes SHA-256 dos arquivos alterados e dos artefatos auditados, os comandos executados, os resultados e os bloqueios ambientais. Os hashes declarados nos manifests históricos não foram adulterados para esconder a ausência do banco operacional; a divergência ficou registrada.

Para reproduzir o que é possível neste clone:

```bash
uv sync --all-extras --locked
uv run pytest -q
uv run ruff format --check src scripts tests
uv run ruff check src scripts tests
uv run pyright
uv run python scripts/ci_check.py
```

Para reproduzir o replay científico completo, ainda é necessário fornecer uma cópia consistente do `data/matches.db` operacional correspondente ao SHA declarado nos manifests, preservando os arquivos WAL/SHM quando aplicáveis. Sem esse insumo, o correto é bloquear alto e não gerar números substitutos.

## Referências

[1] [Repositório brasileirao-predictor](https://github.com/leonardosovienski/brasileirao-predictor).

[2] [Commit-base bec073dcb748dbac63cffe737496f6a7ed8825ac](https://github.com/leonardosovienski/brasileirao-predictor/commit/bec073dcb748dbac63cffe737496f6a7ed8825ac).

[3] Protocolo local [`docs/OU25_NESTED_REPLAY.md`](./OU25_NESTED_REPLAY.md), que define replay temporal, contaminação 2024–2026, preços retrospectivos e gates A1.

[4] Contratos locais [`contracts/ou25-recommendation-v2.json`](../../contracts/ou25-recommendation-v2.json) e [`contracts/ou25-nested-future-candidate.json`](../../contracts/ou25-nested-future-candidate.json), que definem `NO_BET`, capital desabilitado, força máxima 40 e promoção prospectiva.
