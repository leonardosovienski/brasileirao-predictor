# Auditoria de conferência: markdown x estado real dos 5 repositórios (2026-09-06)

Escopo: `core-predictor`, `predictor-ops`, `stocks-predictor`, `cripto-predictor`,
`brasileirao-predictor`. Pergunta: **o que os `.md` afirmam corresponde ao que o
código, os pins e os artefatos realmente são hoje?**

Método: leitura dos pontos de entrada (`README`, `HANDOFF`, `CLAUDE.md`, `CHANGELOG`),
conferência dos pins em `pyproject.toml`/`uv.lock` contra as GitHub Releases reais,
verificação de existência de todo arquivo citado com crase, leitura dos atestados de
poder e **execução das cinco suítes** em Python 3.13 com o core instalado a partir do
`main` (3.2.0).

## Resultado das suítes (Python 3.13, core do `main` = 3.2.0)

| repo | coletados | resultado |
|---|---|---|
| core-predictor | 264 | 264 passaram |
| predictor-ops | 67 | 65 passaram; 2 falhas de ambiente (console script fora de `/usr/bin`, sandbox sem `uv`) |
| stocks-predictor | 374 | 374 passaram |
| brasileirao-predictor | 915 | 914 passaram; 1 falha de ambiente (`numba` ausente) |
| cripto-predictor | 947 | **939 passaram, 5 falhas reais** (ver A1) + 2 falhas de ambiente |

As "falhas de ambiente" são artefatos do sandbox (instalação editable em vez de wheel,
extras não instalados) e não são achados.

## Achados

### A1 — `cripto-predictor` quebra contra o core 3.2.0 (ALTO)

Cinco testes falham com `PowerAttestationMissingError` em
`tests/test_experiment_registry.py` e `tests/test_trials.py`: o 3.2.0 passou a exigir
atestado de controle positivo **também no caminho de atualização** de `status`/`sharpe`
de uma trial existente. O cripto usa esse caminho (reexecução da mesma config, fecho de
sharpe pós-backtest, divisão de eras, maturação da H6).

O repo está pinado em `predictor-core==3.0.0`, então **hoje está verde** — mas o
`CHANGELOG` do core anuncia o 3.2.0 como "aditivo… nenhuma chamada existente muda de
comportamento" no parágrafo de abertura, enquanto a própria seção *Governança* do
mesmo release diz "**Mudança de contrato**". Para o cripto, a segunda frase é a
verdadeira. O bump não é um bump de rotina: exige emitir atestado antes de cada
atualização de veredito.

### A2 — Três versões do core convivem, e a documentação de cada repo aponta para uma diferente (ALTO)

Release publicada mais recente: **v3.2.0** (2026-09-06).

| repo | `pyproject.toml` | markdown | atestado vigente |
|---|---|---|---|
| brasileirao | 3.2.0 | 3.2.0 (HANDOFF) | `core_version: 3.2.0` |
| stocks | **3.0.0** | **3.1.0** (`CLAUDE.md`, `docs/RUNBOOK_H18.md`) | **`core_version: 3.1.0`** |
| cripto | 3.0.0 | 3.0.x (HANDOFF) | `core_version: 3.0.0` |

Em `stocks-predictor` a contradição é **interna**: o `CLAUDE.md` manda instalar a wheel
v3.1.0, o `pyproject.toml`/`uv.lock` resolvem v3.0.0, e o atestado em
`trials.harness_attestation.json` foi emitido com 3.1.0. Quem seguir o `CLAUDE.md` e
quem seguir o `uv sync` rodam contra cores diferentes. Como a H18 está prestes a rodar,
isso decide sob qual código o veredito nasce.

Consequência científica: as duas correções do 3.2.0 que valem para pesquisa — DSR que
**trava** em vez de degenerar em PSR silencioso (`strict=True`), e recusa de atestado
com árvore suja — **não valem hoje para stocks nem para cripto**. O stocks passa 374/374
contra o 3.2.0, ou seja, o caminho de upgrade está livre; o cripto não (A1).

### A3 — `predictor-ops`: README e HANDOFF ainda anunciam 4.0.0 (MÉDIO)

`pyproject.toml` = `4.1.0`, release `v4.1.0` publicada em 2026-09-05, `CHANGELOG` com a
entrada 4.1.0. Mas `README.md:3` diz "versão 4.0.0" e `README.md:16` instrui
`pip install predictor_ops-4.0.0-py3-none-any.whl`. Ironia relevante: o próprio 4.1.0
existe para corrigir "uma divergência de identidade" em que `predictor-ops==4.0.0`
designava dois conteúdos diferentes — e o README continua mandando instalar exatamente
essa versão ambígua.

O cripto também pina `predictor-ops==4.0.0` (a wheel ambígua), enquanto o brasileirão já
está em 4.1.0.

### A4 — `stocks-predictor`: os vereditos H14/H15/H16 citam relatórios que não existem no repo (MÉDIO)

`HANDOFF.md:3052-3063` e `RESEARCH_FREEZE.md:312-339` remetem a
`reports/h14_verdict_adhoc.md`, `h15`, `h16` "para detalhes completos". Os três nunca
foram commitados (`git log --all` vazio para eles), enquanto os relatórios de H1-H13
estão versionados. `reports/*` é gitignored e o versionamento é opt-in via `git add -f`
— então isto é omissão de procedimento, não perda: o ledger `trials.json` tem as 15
trials (H1-H16 sem H3) e sustenta o `CLOSED_FOR_H1_THROUGH_H16`. Ainda assim, os três
últimos vereditos da série são hoje os únicos sem evidência auditável fora da máquina do
operador.

### A5 — `stocks-predictor/CLAUDE.md` omite a única dependência de runtime real (MÉDIO)

A seção "Ambiente" diz "stdlib-first. `numpy` pré-aprovado (ainda não usado)… `pytest` é
dev. Qualquer outra dependência: justificar no HANDOFF". Mas `pyproject.toml` declara
`PyYAML>=6.0,<7` como dependência de runtime e `requirements.txt` a lista — e ela é
usada de verdade em `stocks_predictor/rj_power.py:101` e `rj_pipeline.py:375`. `numpy`
de fato não é usado (confere). O `CLAUDE.md` descreve a política corretamente e a
composição incorretamente: quem ler só ele conclui que o runtime é stdlib puro.

### A6 — Referências mortas menores (BAIXO)

- `stocks-predictor/docs/RJ_DESIGN.md`: cita `tests/test_power_gate.py` e
  `src/families.py`; os arquivos reais são `tests/test_rj_power_gate.py` e não há `src/`.
- `stocks-predictor/HANDOFF.md`: cita `scripts/sync_core.py` (não existe mais desde a
  migração para wheels) e `ECOSYSTEM_HANDOFF.md` — este último **já está anotado** como
  inexistente na própria linha 1598, ou seja, o HANDOFF se autocorrige.
- `predictor-ops/docs/legacy-behavior-migration-matrix.md`: a coluna de destino aponta
  para `tests_v2/test_consumer_contracts.py` em ~10 linhas; o arquivo não existe. A
  matriz descreve migração planejada, não executada — o `.md` não diz isso.
- `stocks-predictor/README.md:163`: "252 testes" contra 374 reais. É afirmação datada
  ("no momento deste commit") e o HANDOFF já registra que essas contagens são datadas;
  fica registrado apenas para quem lê o README isolado.

## O que está correto (conferido, não presumido)

- `stocks`: a política de `known_at` do `CLAUDE.md` bate com o código —
  `roe`/`leverage`/`net_margin` passam `use_known_at=False` (H7/H9/H10/H12), o caminho
  de valor de H18/H19 e `accruals` (H17) usam a data observada, e `revenue_growth_signals`
  (H13) mantém embargo estimado com o comentário "JULGADA" no lugar certo.
  `known_at_policy: observed` está selado nos três blocos `[H17/H18/H19-FROZEN]`.
- `stocks`: `tests/conftest.py` recusa mesmo o core vindo de `vendor/`, como o `CLAUDE.md`
  afirma; a errata de 2026-09-06 no `CLAUDE.md` está correta.
- `stocks`: a decisão pendente anunciada no `CLAUDE.md` (fixar a ordem das rodadas antes
  da primeira) está de fato aberta no HANDOFF:67, com a ordem H17→H18→H19 proposta e não
  fechada.
- `brasileirao`: é o repositório mais alinhado. O checkpoint de 2026-09-06 declara Core
  3.2.0 / Ops 4.1.0 e é exatamente o que os pins dizem; o atestado vigente traz
  `code_version package:3.2.0;git:61f72e7b`, sem `;dirty`, expirando em 2026-09-13.
- `cripto`: a contagem de testes do README (948 com `--extra test`) confere com os 947
  coletados aqui (±1, extras ausentes no sandbox).
- Todos os cinco repositórios têm CI (`.github/workflows/ci.yml`); core e ops têm ainda
  `release.yml` e `dependency-review.yml`.

## Recomendações, em ordem

1. **stocks, antes de rodar a H18**: resolver A2 escolhendo *uma* versão do core e
   alinhar `pyproject.toml`, `uv.lock`, `CLAUDE.md` e `docs/RUNBOOK_H18.md`. A suíte já
   passa 374/374 contra o 3.2.0, e só o 3.2.0 dá o DSR `strict` e a recusa de árvore
   suja. Rodar a H18 sob 3.0.0 e documentar 3.1.0 é o pior dos três mundos. Reemitir o
   atestado após a decisão (o vigente é de 3.1.0 e expira em 2026-09-11).
2. **core**: corrigir a abertura do `CHANGELOG` 3.2.0 — "nenhuma chamada existente muda
   de comportamento" é falso para o caminho de atualização de veredito (A1), como a
   própria seção *Governança* admite.
3. **ops**: atualizar `README.md:3,16` e `HANDOFF.md:3` para 4.1.0.
4. **cripto**: planejar o bump para 3.2.0 como trabalho, não como pin — exige emitir
   atestado nos 5 pontos que hoje atualizam veredito sem ele. Bumpar `predictor-ops` para
   4.1.0 em seguida.
5. **stocks**: `git add -f` dos três relatórios H14/H15/H16, ou uma nota explícita no
   `RESEARCH_FREEZE.md` de que esses três vereditos só têm evidência local.
6. **ops**: marcar a matriz de migração como plano, já que `tests_v2/test_consumer_contracts.py`
   não existe.
