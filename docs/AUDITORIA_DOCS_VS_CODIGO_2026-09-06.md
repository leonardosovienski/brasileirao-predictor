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

## Adendo — varredura estendida (mesma data)

A primeira versão deste relatório rodou a checagem de referências mortas só em
`stocks`, `core` e `ops`. Ficaram de fora justamente os dois repositórios com mais
documentação. Corrigido: a varredura cobriu os **182 arquivos `.md`** dos cinco
repositórios (stocks 25, core 15, ops 10, cripto 50, brasileirao 82).

### `cripto` e `brasileirao` não produziram achados novos

Todas as referências a arquivos inexistentes nesses dois caem em três categorias
legítimas, verificadas uma a uma:

- **Blocos datados append-only.** O `ADENDO ECOSSISTEMA (2026-07-18)` do
  `brasileirao/HANDOFF.md` cita `tools/vendor_byte_audit.py`,
  `FINAL_FORENSIC_REVIEW.md` e `PENDENCIAS_ABERTAS.md` — artefatos da era vendor,
  num bloco que o próprio documento marca como histórico. `docs/READINESS.md`
  declara no cabeçalho que é log append-only e aponta o HANDOFF como fonte
  corrente. No cripto, `HANDOFF.md:821` cita `core/retry.py` e `core/http_client.py`
  **dizendo que foram deletados** — a referência é ao fato da remoção.
- **Entregáveis planejados.** `docs/POSTMORTEM_COPA_2026.md` (campo "Entregável:"),
  `src/research/ev_detector.py` e `docs/experiments/MARKET_05_A1_AUDIT.md` aparecem
  em checklists `- [ ]` não concluídos.
- **Artefatos locais gitignored.** `data/collector_metrics/key_rotation_attestation.json`,
  `data/research/*.json` e `reports/exp001_*.json` estão sob `.gitignore` e já
  constam de `docs/ESTADO_LOCAL_E_OPERACAO.md` como existentes só na máquina do
  operador. Exceção única: `reports/benchmark_baseline_v4_2026-08-21.json` **não**
  está gitignored e não está no repo, citado em `docs/READINESS.md:191` — dentro de
  um documento que se declara histórico, então baixo.

Conclusão: sob a varredura profunda, `brasileirao` e `cripto` se sustentam. A
disciplina de datar bloco e marcar append-only é o que os segura — é a mesma
disciplina cuja ausência produz os achados A2, A3 e A5.

### A2 é contradição de três documentos, não de dois

Além do `CLAUDE.md` (3.1.0) contra o `pyproject.toml` (3.0.0),
`STOCKS_CURRENT_STATE.md:69` declara "resolução canônica do CI/lock: wheel oficial
`predictor-core==3.0.0`". Ou seja: dois documentos dizem 3.0.0, um diz 3.1.0, e o
atestado vigente foi emitido com 3.1.0 — o único artefato que registra o que de fato
rodou é o que discorda da maioria dos documentos. Para contraste,
`cripto/CR_RESEARCH_FREEZE.md:12` afirma "3.0.0 (pyproject.toml + uv.lock,
consistentes)" e a afirmação confere.

### Relógios correndo

Três atestados de poder com validade de 7 dias, e nenhum documento os reúne:

| repo | expira | core do atestado |
|---|---|---|
| cripto | 2026-09-10 | 3.0.0 |
| stocks | **2026-09-11** | 3.1.0 |
| brasileirao | 2026-09-13 | 3.2.0 |

O do stocks vence antes da H18 se a decisão da ordem das rodadas demorar, e qualquer
bump do core o invalida na hora — o que torna a decisão de A2 e a renovação do
atestado uma coisa só, não duas.

## Limites desta auditoria

Declarado para que ninguém leia mais do que foi feito:

- As suítes rodaram em **Linux**, não no Windows do operador, e com o core instalado
  em modo editable a partir do `main` — não a partir da wheel publicada. Falhas
  específicas de Windows ou de empacotamento não apareceriam aqui.
- Nenhum banco real foi exercitado: `matches.db`, `feature_store.db` e o banco do
  stocks são gitignored e estão só na máquina do operador. Nada sobre **dados** foi
  verificado — só sobre código, documentos e artefatos versionados.
- Os ~180 `.md` foram varridos por referências e por afirmações de versão/contagem;
  **não** foram lidos integralmente um a um. Uma afirmação factual errada no meio de
  um documento de análise, que não cite arquivo nem versão, passaria.
- Os vereditos científicos em si (H1–H16, gates, DSR) não foram reauditados: esta é
  uma conferência de documentação contra código, não uma revisão de método.

## Encerramento — o que foi aplicado (2026-09-06, mesmo dia)

Todos os seis achados foram tratados e mergeados nas `main` no mesmo dia da
auditoria. **Quem ler este relatório depois não deve tratar os achados acima como
abertos** — eles são o registro do que estava errado, não do que está.

| # | achado | como fechou |
|---|---|---|
| A1 | `CHANGELOG` do core se contradizia | abertura do 3.2.0 reescrita: nomeia a quebra, o consumidor afetado e o resultado medido nos três domínios (core#27) |
| A2 | três versões do core, stocks contradizendo-se em 3 documentos | tudo alinhado em **3.2.0** — `pyproject`, `uv.lock`, `ci.yml`, `CLAUDE.md`, `RUNBOOK_H18`, `STOCKS_CURRENT_STATE`, `RESEARCH_FREEZE` (stocks#66) |
| A3 | ops anunciando 4.0.0 | README e HANDOFF em 4.1.0, com aviso de por que 4.0.0 não deve ser instalada (ops#19) |
| A4 | H14–H16 sem relatório versionado | **registrado, não fechado** — nota de evidência no `RESEARCH_FREEZE` diz o que o veredito continua tendo, o que falta e o comando para fechar; a lacuna em si depende da máquina do operador (stocks#66) |
| A5 | `CLAUDE.md` omitindo PyYAML | seção *Ambiente* declara a dependência real e onde é usada (stocks#66) |
| A6 | referências mortas | caminhos corrigidos no `RJ_DESIGN`; matriz do ops marcada como plano (stocks#66, ops#19) |

O cripto subiu **ops 4.1.0** e mantém **core 3.0.0 de propósito** (cripto#103): o
bump do core exige emitir atestado nos cinco pontos que atualizam veredito, e está
registrado como pendência no HANDOFF de lá.

### O achado que só apareceu ao aplicar

Não estava na auditoria e é o mais reutilizável: **os pins de core/ops vivem em
quatro ou cinco arquivos por repositório, e nenhum deriva do outro.**

| repo | onde o pin vive |
|---|---|
| cripto | `pyproject.toml`, `uv.lock`, `Dockerfile`, `.github/workflows/ci.yml`, `scripts/verify_installed_wheels.py` (+ `tests/test_core_integrity.py`) |
| stocks | `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml` |

Trocar só o `pyproject` **passa na suíte local e quebra o CI** com
`ResolutionImpossible`, porque a suíte não enxerga Dockerfile nem workflow. Custou
três rodadas de CI vermelho (duas no cripto, uma no stocks) para o inventário
fechar. Registrado no HANDOFF do cripto, que é quem ainda vai encostar nesses
arquivos ao subir o core.

### Consequência operacional da migração do stocks

Sob o core 3.2.0, rodar a suíte com **qualquer** alteração não commitada derruba 21
testes com `DirtyWorkingTreeError` — é o guard novo funcionando, não regressão
(com a árvore limpa: 374/374). Está no `CLAUDE.md` e no `RUNBOOK_H18` do stocks.

### O que seguiu com o operador

Nada disto é código, e nenhum podia ser feito a partir do sandbox. **A origem de cada
um é diferente e vale distinguir** — dois deles são dívida que esta auditoria criou ou
deixou aberta, e ler a lista como "quatro pendências equivalentes" esconde isso:

| # | pendência | origem | estado |
|---|---|---|---|
| 1 | **Reemitir o atestado do stocks** (exige `git status` limpo) | **criada por esta sessão** — o atestado estava válido até 2026-09-11 e o bump para 3.2.0 o invalidou | dívida nova, com prazo: sem ela a H18 não registra trial |
| 2 | **Fixar a ordem** H17/H18/H19 | **anterior à sessão** — já pendente no `CLAUDE.md` e no `HANDOFF` do stocks | a auditoria só confirmou que segue aberta |
| 3 | **`git add -f`** dos relatórios H14/H15/H16 | **achado A4 desta auditoria** | documentado, **não fechado**: a lacuna existe até os arquivos serem versionados |
| 4 | **Bump do core no cripto** | **achado A1 desta auditoria** | adiado por decisão do operador; caminho mapeado no HANDOFF de lá |

Só o item 1 bloqueia alguma coisa hoje (a H18). Nenhum deles impede ler ou usar os
repositórios, e nenhum contradiz o resultado da auditoria — mas o item 1 é dívida que
não existia antes desta sessão, e o 3 é achado que ficou registrado em vez de resolvido.
Contabilizar os dois como "fechados" seria o mesmo tipo de imprecisão que esta auditoria
foi feita para encontrar.
