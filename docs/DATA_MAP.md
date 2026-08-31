# Mapa de dados e artefatos operacionais

Este documento responde três perguntas: **onde** fica cada artefato, **o que**
ele contém e **como** conferir ou operar sem misturar pesquisa, serving e
coleta prospectiva. Caminhos relativos partem da raiz do repositório.

> O conteúdo de `data/` é operacional e quase todo fica fora do Git. Um clone
> limpo não contém o banco, snapshots, logs nem ledgers locais. As exceções
> versionadas estão indicadas abaixo. Nunca grave chave de API em arquivos:
> `ODDSPAPI_KEY` existe somente como variável de ambiente.

## Inventário rápido

| Caminho | O que contém | Git | Escrita / regra |
|---|---|---:|---|
| `data/matches.db` | SQLite operacional: jogos, odds históricas, estatísticas, ratings e parâmetros | não | ingestão/serving; pesquisa abre com `mode=ro` |
| `data/matches.db-wal`, `data/matches.db-shm` | arquivos auxiliares do SQLite em modo WAL | não | geridos pelo SQLite; não copiar isoladamente |
| `data/team_aliases.json` | aliases canônicos para resolver identidade de equipes | sim | revisão humana; fuzzy matching não decide sozinho |
| `data/teams_brasileirao.json` | cadastro canônico dos clubes | sim | alterado somente quando o domínio muda |
| `data/trials.json` | ledger científico de hipóteses, status e protocolos | sim | append/governança; nomes únicos e status obrigatório |
| `data/trials.harness_attestation.json` | atestado do harness de controle positivo | sim | requisito para registrar nova trial |
| `data/odds_snapshots/AAAA-MM-DD.jsonl` | snapshots PIT do coletor A1, append-only e encadeados por hash | não | coletor A1; cada linha permanece `homologated=false` até PASS formal |
| `data/odds_quarantine/quarantine.jsonl` | aliases desconhecidos, violações PIT/schema, conflitos e erros da fonte | não | append-only; revisão humana, nunca fluxo principal |
| `data/collector_state/` | estado local necessário ao coletor/dedupe/hash-chain | não | interno do coletor; preservar junto dos snapshots |
| `data/collector_metrics/AAAA-MM-DD.json` | coverage, continuidade, resolução, conflitos e consumo diário | não | gerado por `collector_daily_metrics.py` |
| `data/collector_metrics/gate_a1_verdict.json` | resultado agregado do Gate A1 | não | gerado por `evaluate_gate_a1.py`; não editar à mão |
| `data/research/` | ledgers e resultados de pesquisa/shadow | não | regras específicas de cada protocolo em `docs/experiments/` |
| `data/predictions.jsonl` | previsões pré-jogo congeladas antes do kickoff | não | append-only; caminho substituível por `PREDICTIONS_LOG_PATH` |
| `data/period_predictions.jsonl` | previsões por período/primeiro tempo | não | append-only |
| `data/bets.jsonl` | ledger operacional de banca/apostas | não | capital permanece bloqueado sem GO explícito |
| `data/live_predictions.jsonl` | ledger separado de previsões live | não | não pertence às coortes pré-jogo |
| `data/collection_only/brasileirao_events.jsonl` | arquivo bruto do pipeline collection-only | não | append-only, sem decisão econômica |
| `data/brasileirao.log` | log local da aplicação | não | diagnóstico; pode conter eventos de runtime |
| `schemas/odds_snapshot_v1.json` | contrato JSON dos snapshots A1 | sim | vocabulário fechado; alterar exige versionamento |
| `docs/` | protocolos, relatórios, cobertura e decisões | sim | documentação; resultados brutos continuam em `data/` |

## Banco operacional (`data/matches.db`)

`config.yaml` aponta o banco padrão para `data/matches.db`. Ele é a fonte local
do pipeline Sofascore → `sofascore_matches` → `matches`, além dos dados usados
por odds, ratings e calibração. Não é um arquivo distribuído pelo Git.

Inventário observado em **2026-08-26** (é um snapshot, não um número fixo):

| Tabela | Linhas |
|---|---:|
| `sofascore_matches` | 2.321 |
| `matches` | 2.281 |
| `match_statistics` | 439.764 |
| `odds_lines` | 17.820 |
| `odds_snapshots` | 25.142 |
| `sofascore_player_ratings` | 65.733 |
| `player_comp_stats` | 5.210 |
| `current_elo` | 30 |
| `model_parameters` | 1 |
| `xg_model_parameters` | 0 |

No mesmo inventário, o arquivo tinha **49.508.352 bytes**, SHA-256
`8A3A2415AAB9B8525708EE18EE7B3FB360B40031904095F5C71B35871E5946CD` e
`PRAGMA integrity_check = ok`. O hash muda quando o banco é atualizado.

Para conferir o estado atual sem escrever no banco:

```powershell
Get-Item data/matches.db | Select-Object FullName,Length,LastWriteTime
Get-FileHash data/matches.db -Algorithm SHA256
uv run python -m brasileirao_scripts.inventario_dados
```

Ao abrir SQLite manualmente, use URI read-only:

```python
sqlite3.connect("file:data/matches.db?mode=ro", uri=True)
```

Não copie somente `matches.db` enquanto houver escrita ativa: os arquivos WAL e
SHM podem fazer parte do estado consistente. Use o mecanismo de backup:

```powershell
uv run python -m brasileirao_predictor.backup_restore create --output C:\backups\brasileirao-AAAA-MM-DD
uv run python -m brasileirao_predictor.backup_restore verify --backup C:\backups\brasileirao-AAAA-MM-DD
```

## Coletor A1

O coletor A1 não escreve em `matches.db`. Seus quatro conjuntos são isolados:

```text
data/odds_snapshots/    dados PIT válidos, um JSONL por dia
data/odds_quarantine/   dados rejeitados e respectivos motivos
data/collector_state/   continuidade, dedupe e hash-chain
data/collector_metrics/ métricas diárias e veredito do gate
```

Fluxo operacional:

```powershell
# descoberta semanal de fixtures
uv run python -m brasileirao_scripts.collect_odds_a1 --discover

# coleta shadow; a chave é lida somente do ambiente
uv run python -m brasileirao_scripts.collect_odds_a1 --collect

# consolidação diária
uv run python -m brasileirao_scripts.collector_daily_metrics

# avaliação do gate
uv run python -m brasileirao_scripts.evaluate_gate_a1

# contrato da cadeia; na operação, o coletor também verifica antes de selar o dia
uv run pytest tests/test_collector_contract.py -q
```

O modo econômico foi dimensionado para **245 requests/mês**: quatro capturas
por rodada em 60 jogos (`4 × 60 = 240`) mais cinco chamadas de discovery. Ele é
`REHEARSAL_ONLY`; não mede continuidade suficiente para homologação formal.

Estado observado em **2026-08-26**:

- dias de shadow: **0**;
- arquivos diários de snapshots: **0**;
- quarentenas A1: **0**;
- veredito: **`NOT_STARTED`**;
- `homologated`: **false**;
- capital: **bloqueado**.

Os critérios completos e as semânticas de append-only, `supersedes`, PIT,
identidade e hash-chain vivem em
`docs/experiments/MARKET_05_A1_COLLECTOR_SPEC.md`. Coverage operacional fica em
`docs/COVERAGE.md`.

## Pesquisa, serving e holdouts

- Pesquisa deve abrir `matches.db` read-only e registrar resultados em
  `data/research/`; não deve atualizar cache ou parâmetros de serving.
- `current_elo` e `model_parameters` são estado de serving, não atalhos para
  avaliação histórica. Walk-forward usa estado disponível no instante correto.
- `data/trials.json` é a fonte canônica para saber quais hipóteses existem e
  seus status. Não selecione hipótese consultando holdout.
- As restrições vigentes para 2024, 2025 e diagnóstico 2026 estão no checkpoint
  mais recente de `HANDOFF.md` e no protocolo da trial correspondente.
- Relatórios em `docs/RELATORIO_*.md` explicam resultados; JSON/JSONL em
  `data/research/` preservam as evidências locais detalhadas.

## Comandos de auditoria rápida

```powershell
# arquivos locais, tamanho e data
Get-ChildItem data -Recurse -File |
  Sort-Object FullName |
  Select-Object FullName,Length,LastWriteTime

# contratos e regressão do repositório
uv run ruff format --check src scripts tests
uv run ruff check src scripts tests
uv run pyright
uv run pytest -q
uv run python -m brasileirao_scripts.ci_check

# trials: quantidade, nomes únicos e presença de status
uv run python -c "import json; x=json.load(open('data/trials.json',encoding='utf-8')); print('total=',len(x),'unicos=',len({t['name'] for t in x}),'sem_status=',sum(not t.get('status') for t in x))"
```

Se um caminho operacional não existir, isso pode significar apenas que aquele
pipeline ainda não rodou neste checkout. Não crie arquivo vazio para mascarar a
ausência: os scripts e o CI devem reportar a condição ambiental explicitamente.
