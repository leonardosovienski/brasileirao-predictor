# Readiness audit

Status: `READY_WITH_EXTERNAL_BLOCKER`.

## Gates homologados

- Python 3.13: 413 testes aprovados (1 deselecionado), zero falhas; mais 1 teste de integração Redis real na execução final (414 no total, verificado em CI).
- .NET 10: build Release com warnings como erro, 0 warnings; 30 testes aprovados, zero falhas e zero skips.
- Ruff: `ruff check src scripts tests` e `ruff format --check src scripts tests` verdes, sem ignores amplos.
- Pyright: runtime homologado e fronteiras públicas verdes; pesquisa permanece explicitamente fora do escopo tipado.
- Goldens: 85 testes de Dixon–Coles, Elo, xG, pricing/stakes e matemática preservados.
- Compose: três imagens construídas com wheelhouse temporário validado por SHA-256; Redis, kernel e Worker saudáveis.
- E2E: smoke versionado 3/3, Python → Redis → C# observado, TTL e correlação validados.
- Resiliência: idempotência, replay, timeout/widening, reconexão após perda do Redis e graceful shutdown validados.
- Bancos: Sports DB e Market DB usam paths absolutos distintos; Worker e kernel recebem volumes read-only.

## Cobertura branch-aware

O relatório completo, sem exclusões silenciosas, está em `docs/COVERAGE.md`.

- runtime homologado Python: 81,25%;
- kernel e integração Redis: 81,49%;
- providers homologados: 83,47%;
- Worker .NET: 85,15% linhas e 80,92% branches.

Pesquisa, migração e legado continuam reportados na cobertura global, mas não são promovidos ao runtime homologado.
Nenhum script ou dado legado foi removido.

## Contrato e dependências compartilhadas

O protocolo `brasileirao.redis/1` é validado em Python e C#, incluindo versão desconhecida, identificador ausente,
payload inválido, correlação e serialização. `predictor_core 2.3.0` e `predictor_ops 3.1.0` são carregados de
`site-packages`; os hashes canônicos permanecem em `constraints/shared-wheels.sha256`. O teste operacional de
`predictor_ops` verifica que os pipes próprios de `Popen` são fechados.

## Bloqueadores externos (resolvidos)

1. publicação estável das wheels canônicas em URLs acessíveis ao CI/BuildKit — resolvido: `v2.3.0`/`v3.1.0` publicadas como GitHub Release assets, consumidas com sucesso pela CI atual;
2. geração e versionamento de lockfile portátil a partir desse registry estável — resolvido: `uv.lock` versiona URL + hash sha256 de ambas as wheels.

Os dois artefatos externos que bloqueavam a classificação `READY` já existem; a ressalva `WITH_EXTERNAL_BLOCKER` no topo deste documento refere-se ao estado histórico anterior a essa publicação, não ao estado corrente.
