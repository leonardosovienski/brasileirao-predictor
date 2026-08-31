# Filtro OU2.5 — replay temporal aninhado

## Estado da evidência

O filtro está implementado, mas não promovido. As temporadas 2024, 2025 e
2026 são dados já observados/contaminados. Nenhum resultado delas constitui
validação prospectiva A1. Capital permanece desabilitado e a força da indicação
fica limitada a 40/100 até os dois limites inferiores de IC95 (ROI e CLV) serem
positivos numa coorte A1 futura, congelada antes do primeiro label.

Em 2026-08-27 foi feita uma coleta reproduzível de 1.140 resultados de
2021–2023. O endpoint histórico do SofaScore devolveu preços 1X2, mas zero pares
OU2.5. Sem preço OU2.5 executável não há como medir EV, retorno ou CLV. Esse é
um bloqueio de dados, não um resultado negativo nem autorização para substituir
preços reais por odds sintéticas.

## Método

O modelo de probabilidade é executado prequentialmente pelo evaluator existente.
O novo módulo recebe apenas seu ledger PIT e faz uma segunda camada temporal:

1. cada fold externo usa um prefixo de treino e o bloco imediatamente seguinte;
2. dentro do prefixo, combinações de filtro são comparadas por replay expansivo;
3. o filtro escolhido é congelado e aplicado ao próximo bloco sem retuning;
4. todos os filtros, inclusive perdedores, são preservados no JSON;
5. p-valores unilaterais recebem correção family-wise de Holm em cada fold;
6. a ordenação é lexicográfica: limite inferior do ROI, limite inferior do CLV,
   pior temporada, pior lado, pior faixa de odd e amostra;
7. o resultado traz baselines de apostar sempre, nunca apostar e probabilidade
   de mercado de-vigada proporcionalmente.

O haircut do EV conservador é o quantil superior dos gaps absolutos de
calibração por decil, calculado somente no passado disponível. Chance do
resultado, EV bruto, EV conservador e força 0–100 são campos distintos.

## Execução

```powershell
uv sync --all-extras --locked
uv run python -m brasileirao_scripts.research_ou25_nested_replay --output data/research/ou25_nested
```

O comando falha alto se `data/matches.db` estiver ausente ou se não houver
pares de odds. Gera `nested_replay.json`, `individual_losses.csv`,
`frozen_candidate.json` e `manifest.json`, com hashes SHA-256 do banco e dos
artefatos. O registro em `contracts/ou25-nested-future-candidate.json` congela
a ausência de candidato elegível (`candidate_id: null`). Um candidato futuro
terá de ser pré-registrado antes do primeiro label A1 que o avaliará.

Para coleta enxuta de resultados e odds disponíveis na fonte:

```powershell
uv run python -m brasileirao_predictor.ingest_sofascore --outcomes-odds-only --through-season 2023 --rate-limit 0.05
uv run python -m brasileirao_scripts.sync_matches_from_sofascore
```

`--rate-limit` deve respeitar a fonte; o valor baixo acima só é apropriado para
uma execução controlada e pode precisar ser aumentado.
