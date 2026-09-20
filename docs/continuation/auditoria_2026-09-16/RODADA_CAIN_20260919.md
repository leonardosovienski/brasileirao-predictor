# Rodada CAIN × Brasileirão — encerramento de 2026-09-19

## Estado publicado

Esta rodada foi encerrada com o código pertencente à execução publicado nas branches `main` dos dois repositórios.

- CAIN: `6f9d254776b2a3c251f6cce14529087c57ebbeae` — orçamento efetivo do provedor, diagnóstico limitado de falhas HTTP, preservação de `provider_failure` e testes de regressão.
- Brasileirão Predictor: `a51a68dd5d23734d6ac882cbcf95bc4d5c15b7a6` — ordenação determinística de linhas walk-forward por kickoff e teste de contrato.

O commit do CAIN foi rebaseado sobre o `main` vigente. A resolução do conflito em `analysis.py` preservou tanto a lógica preexistente de grupos/revisões quanto o orçamento efetivo de entrada do provedor.

## Verificação

- CAIN integrado: 906 testes passaram, 1 foi ignorado e houve 2 avisos de dependências; Ruff e `git diff --check` passaram.
- Brasileirão: 21 testes passaram; Ruff check e Ruff format check passaram.
- Os hashes foram confirmados em `refs/heads/main` por `git ls-remote`.

## Conclusão científica

- Lucro demonstrado: não.
- Hipótese nova cientificamente validada: não.
- Melhoria técnica de orçamento e diagnóstico: implementada e testada como engenharia.
- Melhoria semântica geral do CAIN: não demonstrada; a candidata reservada falhou e não foi promovida.
- Correção walk-forward: implementada e testada; não promove resultados exploratórios anteriores.
- O backfill agregado OU2.5 não fornece odds executáveis de fechamento e não remove o bloqueio de H1/MARKET06.

## Continuidade local

Os artefatos brutos, respostas originais do CAIN, recibos de avaliação reservada e manifesto SHA-256 permanecem no diretório local da execução `outputs/completion-20260919`. Eles não foram enviados ao GitHub para evitar publicar bancos, configurações, prompts operacionais ou evidência bruta sem revisão específica.

Os checkouts originais continuam deliberadamente sem limpeza. No Brasileirão, os arquivos da rodada observados no checkout antigo correspondem ao conteúdo publicado, exceto pela formatação anterior do teste walk-forward. No CAIN, há mudanças históricas e experimentais divergentes no checkout destacado; elas não foram atribuídas a esta rodada nem publicadas automaticamente.

A continuidade após apagar o chat deve partir deste arquivo e do recibo local `GIT_PUBLICATION_20260919.md`. Não se deve interpretar o estado sujo dos checkouts originais como trabalho ausente desta rodada.
