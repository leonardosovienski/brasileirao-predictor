# Relatório — implementação do Gate A1

## Estado

- PoC da fonte: **PASS**;
- implementação: concluída em shadow, `homologated=false`;
- shadow ativo: **não**;
- relógio formal de sete dias: **não iniciado**;
- motivo: chave rotacionada ainda não confirmada;
- capital e detector: bloqueados.

## Cadência e orçamento

Foi escolhido o modo econômico. Para 60 fixtures/mês:

`4 snapshots × 60 + 5 descobertas semanais = 245 requests/mês`.

O teto gratuito de 250 deixa margem de apenas cinco chamadas e comporta no
máximo cerca de 61 fixtures/mês. Discovery diário daria 270 chamadas e foi
rejeitado. O scheduler roda lógica local a cada 15 minutos, mas só consulta
`/odds` quando vence T-24h, T-6h, T-1h ou T-10m; discovery é semanal.

Consequência: continuity não é mensurável. O avaliador emite
`REHEARSAL_ONLY` para qualquer conjunto econômico, mesmo que os demais
critérios passem. Homologação formal provavelmente exige plano pago e cadência
completa, sempre mediante decisão humana.

## Segurança e escopo

Não houve endpoint histórico, backfill, alteração de `matches.db`, serving,
cache, modelo, detector ou capital. A chave não foi persistida. O instalador
falha fechado sem `ODDSPAPI_KEY`; não foi executado porque a chave anterior
foi exposta.

## Desvio documental

Os três artefatos declarados obrigatórios no pedido não existiam em nenhum
workspace ou anexo pesquisável. A spec, o schema e os 17 testes foram
reconstruídos a partir do texto fornecido, em vez de copiados de uma versão
congelada anterior. Nenhum outro desvio foi introduzido deliberadamente.

## Validação final

- contratos A1: 17/17 passaram;
- suíte completa: 752 passed, 1 deselected, 3 warnings conhecidos;
- Ruff: verde;
- Pyright: 0 erros, 0 warnings;
- `ci_check.py`: cinco barreiras verdes, incluindo smokes pré-jogo/live;
- ledger: 26 registros únicos, todos com status;
- `git diff --check`: verde;
- chave configurada ao final: não;
- tarefas `brasileirao-a1-*` instaladas: não;
- commit/push: não.
