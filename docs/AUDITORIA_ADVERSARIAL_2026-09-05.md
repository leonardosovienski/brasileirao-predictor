# Auditoria adversarial do ecossistema — 2026-09-05

## Escopo e regra de decisão

Auditoria independente e hostil dos três repositórios do ecossistema, conduzida
em ambiente remoto limpo em 2026-09-04/05, sobre a branch
`claude/audit-predictor-ecosystem-cvx0wg` de cada repositório (HEAD idêntico a
`origin/main` nos três no momento da coleta):

| Repositório | HEAD auditado | Assunto |
|---|---|---|
| `leonardosovienski/core-predictor` | `29eb8b7` | primitivas científicas neutras |
| `leonardosovienski/predictor-ops` | `ab41e6a` | runtime operacional genérico |
| `leonardosovienski/brasileirao-predictor` | `61036fc` | domínio (previsão de futebol) |

**A tese submetida a falsificação foi:** *"Este ecossistema é honesto sobre o
que sabe. Nenhuma afirmação é mais forte que a evidência que a sustenta, e um
terceiro consegue verificar isso sozinho."*

Regra de decisão adotada: toda documentação foi tratada como afirmação sob
suspeita, nunca como evidência. Nenhum achado foi registrado sem comando e
saída reproduzíveis. Achados sem execução direta estão rotulados como
inferência, com o grau de confiança e o que os confirmaria ou derrubaria.
Nenhuma correção foi aplicada **no momento em que este documento foi escrito** —
por decisão explícita do mantenedor, o registro veio antes do conserto, para que
as correções fossem decididas separadamente da sessão que descobriu os problemas.
As correções foram autorizadas e aplicadas depois, uma a uma; o estado atual de
cada achado está no **Adendo 2026-09-06** no fim deste documento. As seções de
achado abaixo descrevem o ecossistema **como ele estava em 2026-09-05** e não
foram reescritas — o valor delas é histórico.

**Veredito em uma linha:** a tese se sustenta na camada de engenharia e falha
na camada científica — o CI é real e reproduzível e as fronteiras são código
executável, mas nenhuma das 29 trials do registro é reproduzível por terceiro.

---

## Sumário dos achados

| # | Severidade | Achado | Confiança | Rastreamento |
|---|---|---|---|---|
| 1 | Crítico | Nenhuma trial é reproduzível por terceiro: 29/29 com proveniência `UNKNOWN` | Alta (medido) | brasileirao#56 |
| 2 | Crítico | O desconto do Deflated Sharpe é quase inoperante na prática | Alta (mecanismo) / Média (magnitude) | core-predictor#20 |
| 3 | Alto | Bypass do gate de atestação de poder por sobrescrita de veredito | Alta (executado) | core-predictor#21 |
| 4 | Alto | A wheel `predictor-ops 4.0.0` em produção nunca passou pelos gates de release | **Alta (confirmado por log)** | predictor-ops#18 |
| 5 | Médio | Colisão de versão `4.0.0` — já conhecido, correção em voo | Alta | predictor-ops#17 |
| 6 | Médio | O código que produz as evidências é o menos testado do repositório | Alta (medido) | brasileirao#57 |
| 7 | Baixo | Atestação de poder emitida a partir de árvore de trabalho suja | Alta | brasileirao#58 |

Este documento foi registrado em brasileirao-predictor#55. Cada achado tem uma
issue no repositório onde está o código, com o que a fecharia; o documento
preserva o raciocínio e a evidência, as issues preservam o trabalho pendente.

---

## O que passou — reprodução manual do CI

Os três pipelines de `.github/workflows/` foram reproduzidos passo a passo à
mão, fora do GitHub Actions. Números reais obtidos em 2026-09-04:

| Repositório | Testes | Cobertura medida | Gate declarado | Ruff | Pyright |
|---|---|---|---|---|---|
| core-predictor | 244 passed (3,13 s) | **86 %** | `--fail-under=80` ✅ | limpo (91 arq.) | 0 erros |
| predictor-ops | 67 passed + 1 posix (11,80 s) | **88,74 %** | 80 % ✅ | limpo (37 arq.) | 0 erros |
| brasileirao-predictor | 907 passed + 1 integration (43,87 s) | **50 %** | `--fail-under=45` ✅ | limpo (339 arq.) | 0 erros |

Comandos, na ordem dos workflows:

```
# core-predictor (.github/workflows/ci.yml, job "test")
uv sync --frozen --python 3.13 --group dev --extra http --extra scraping
uv run --no-sync coverage run --source=src/predictor_core -m pytest -q
uv run --no-sync coverage report --fail-under=80
uv run --no-sync ruff check . && uv run --no-sync ruff format --check .
uv run --no-sync pyright

# predictor-ops (.github/workflows/ci.yml, job "test", leg ubuntu/3.13)
uv sync --python 3.13 --all-extras
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run python -W error::ResourceWarning -m pytest --cov --cov-report=term-missing
uv run python -W error::ResourceWarning -m pytest posix_integration -q
uv build

# brasileirao-predictor (.github/workflows/ci.yml, job "python", leg 3.13)
redis-server --daemonize yes --port 6379 --save ''
export REDIS_URL=redis://127.0.0.1:6379/15
uv sync --all-extras --locked
uv run python brasileirao_scripts/validate_env_example.py
uv run python brasileirao_scripts/seed_test_fixtures.py
uv run ruff check  brasileirao_predictor brasileirao_scripts tests
uv run ruff format --check brasileirao_predictor brasileirao_scripts tests
uv run pyright brasileirao_predictor
uv run coverage run -m pytest
uv run coverage run --append -m pytest -m integration
uv run coverage report --fail-under=45
```

### Ataques que não tiveram sucesso

Registrados porque um ataque que falha é informação sobre a solidez do sistema.

**O pin de hash das wheels compartilhadas resiste.** Baixadas as duas wheels
canônicas direto das releases e conferidas contra o arquivo de constraints:

```
$ cd wheelhouse && sha256sum --check /…/constraints/shared-wheels.sha256
predictor_core-3.1.0-py3-none-any.whl: OK
predictor_ops-4.0.0-py3-none-any.whl: OK
```

Construída uma wheel `4.0.0` a partir do HEAD do ops (`uv build`), o pin a
**rejeitou** corretamente — `661136d636965ebc728a85dcfbbd28f0364452c4199e15a8ec6966657a1e15aa`
contra `a79b895492181c88c428ee8984a38d5f3da0d0105f060f89a061376d5cfe2b2b`.

**A cadeia do core-predictor está limpa byte a byte.**

```
$ diff -r wheelhouse/x_core/predictor_core core-predictor/src/predictor_core
(saída vazia)
```

A wheel `predictor_core-3.1.0` tem `create_system=3` (Unix) e foi publicada por
`github-actions[bot]` — construída pelo pipeline, como o contrato afirma.

**As fronteiras de domínio são fato, não convenção.**

```
$ grep -rniE "brasileir|futebol|football|soccer|dixon|odds|kelly|1x2|ou25" \
    --include=*.py core-predictor/src predictor-ops/src
(nenhum vazamento de domínio)
```

**A barreira de capital do ops é código executável.** Enumerados os oito
`JobType` com `capital_permission=True`; sete rejeitados por validador
`pydantic`, apenas `EXECUTION` aceito, e `EXECUTION` sem permissão também
rejeitado:

```
BLOQUEADO | SPORTS_COLLECTION+capital   -> capital_permission is allowed only for EXECUTION jobs
BLOQUEADO | MARKET_COLLECTION+capital   -> (idem)
BLOQUEADO | FORECAST_GENERATION+capital -> (idem)
BLOQUEADO | SHADOW_DECISION+capital     -> (idem)
ACEITO    | EXECUTION+capital
BLOQUEADO | SETTLEMENT+capital          -> (idem)
BLOQUEADO | RECONCILIATION+capital      -> (idem)
BLOQUEADO | RISK_MONITORING+capital     -> (idem)
BLOQUEADO | capital sem job_type        -> (idem)
BLOQUEADO | EXECUTION sem capital       -> EXECUTION jobs require capital_permission=true
```

**A barreira de capital do domínio é incondicional.**
`brasileirao_predictor/prediction_protocol.py:95` é
`if item.capital_enabled: block("CAPITAL_BLOCKED", "capital must remain disabled")`
— sem chave de configuração. Ligar capital exige editar código-fonte.

**O gate de atestação de poder resiste ao ataque direto.** Tentativa de
registrar trial nova sem atestado e de sobrescrever trial existente com params
diferentes, ambas em cópia isolada do registro:

```
-> registrar trial NOVA sem atestado:
   BLOQUEADO: PowerAttestationMissingError
-> sobrescrever trial existente com params DIFERENTES:
   BLOQUEADO: ValueError — "variação de configuração é tentativa nova:
              registre com um name novo (N+1)"
```

O gate verifica esquema, expiração, versão do core, métrica declarada e
`pipeline_fingerprint`. É o mecanismo de governança mais bem construído do
ecossistema. Sua falha está no achado 3, não aqui.

**Os dois registros de trials estão sincronizados.** `data/trials.json` e
`data/trials.v2.json` têm 29 entradas cada, zero divergência de `status` e zero
de `sharpe`.

---

## Achado 1 — Crítico — Nenhuma trial é reproduzível por terceiro

**Repositório:** brasileirao-predictor · **Confiança: alta (medido, não inferido).**

O esquema `trial-registry/2.0.0` define campos de proveniência que existem
justamente para permitir reprodução independente. Contagem sobre as 29 entradas
reais de `data/trials.v2.json`:

```
$ python3 -c "…contagem de campos == 'UNKNOWN' em data/trials.v2.json…"
total trials: 29
seed                   UNKNOWN= 29  ausente=  0  /29
dataset_hash           UNKNOWN= 29  ausente=  0  /29
code_version           UNKNOWN= 29  ausente=  0  /29
data_cutoff            UNKNOWN= 29  ausente=  0  /29
executed_at            UNKNOWN= 29  ausente=  0  /29
selection_path         UNKNOWN= 29  ausente=  0  /29
model_version          UNKNOWN= 29  ausente=  0  /29
feature_version        UNKNOWN= 29  ausente=  0  /29
n_trials_ecosystem     UNKNOWN= 29  ausente=  0  /29
metric                 UNKNOWN=  7  ausente=  0  /29
```

O `predictor-core` **exporta** as funções que preencheriam esses campos —
`dataset_fingerprint` e `current_code_version` estão em `predictor_core.__all__`.
Contagem de consumidores reais no repositório de domínio, excluindo `.venv`:

```
$ for s in validate_scientific_transition ScientificState ScientificPromotionError \
           TrialRegistryV2 validate_trial_v2 require_trial_v2 dataset_fingerprint \
           current_code_version; do
    grep -rn "$s" --include=*.py brasileirao_predictor brasileirao_scripts tests | wc -l
  done
validate_scientific_transition: 0
ScientificState:                0
ScientificPromotionError:       0
TrialRegistryV2:                0
validate_trial_v2:              1
require_trial_v2:               0
dataset_fingerprint:            0
current_code_version:           0
```

A maquinaria de proveniência foi construída no core e não foi ligada no domínio.

**Agravante — o dataset não existe de forma verificável.** `data/matches.db` é
ignorado pelo git (`/data/*` em `.gitignore`, com exceções nomeadas que não o
incluem). O banco presente durante o CI é fixture gerado por
`seed_test_fixtures.py`:

```
$ python3 -c "import sqlite3; print(sqlite3.connect('data/matches.db')
      .execute('select count(*) from matches').fetchone())"
(0,)
```

Não existe dataset publicado, nem hash de dataset em nenhuma trial, contra o
qual um terceiro pudesse comparar. A suíte de testes do próprio projeto declara
o princípio violado — `tests/test_trials_registry_schema.py` cita a docstring do
core: *"o registro só protege o DSR se todo campo do denominador for
interpretável"* — mas valida o esquema v1, não a proveniência v2.

**O que derrubaria este achado:** um `dataset_hash` real preenchido em qualquer
trial, ou um dataset publicado com fingerprint conferível.
**O que o fecharia:** preencher `dataset_hash`, `code_version` e `seed` via as
funções que o core já exporta, e uma regressão que falhe se um veredito fechado
tiver proveniência `UNKNOWN`.

---

## Achado 2 — Crítico — O desconto do Deflated Sharpe é quase inoperante

**Repositório:** core-predictor (`src/predictor_core/measurement/trials.py`) ·
**Confiança: alta para o mecanismo; média para a magnitude.**

A fórmula implementada está correta e é a de Bailey & López de Prado (2014):
`DSR = PSR(returns, SR0)` com `SR0 = E[max SR]` estimado por
`sqrt(V[SR]) * ((1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e)))`. O defeito não está na
matemática, está na alimentação dela.

`deflated_sharpe_ratio` estima `V[SR]` **apenas com os sharpes efetivamente
registrados**, enquanto `N` conta o registro inteiro. No registro real, 3 de 29
trials têm sharpe numérico — e as três são variantes do mesmo experimento OU2.5
walk-forward, isto é, a subamostra menos diversa possível:

```
N tentativas no registro = 29
sharpes finitos usados p/ estimar V[SR] = 3 -> [0.0722, 0.1043, 0.09109420983909514]
```

Com a mesma série de retornos e o mesmo `n_trials=29`, variando apenas quanto do
registro está preenchido:

```
registro REAL (V[SR] de 3 trials):   SR0=0.033226   DSR=0.9791   <- PASSA no gate 0.95
contrafactual, 29 sharpes, sd=0.05:  SR0=0.1102     DSR=0.6980
contrafactual, 29 sharpes, sd=0.10:  SR0=0.2441     DSR=0.0172   <- REPROVA
contrafactual, 29 sharpes, sd=0.20:  SR0=0.3793     DSR=0.0000
nenhum sharpe registrado:            SR0=0.0000     DSR=0.9964   == PSR puro
```

A última linha é o modo de falha silencioso: com menos de dois sharpes finitos,
`variance()` devolve 0, `expected_max_sharpe` devolve 0 por guarda explícita, e
o DSR **degenera exatamente em PSR com benchmark zero** — sem desconto algum —
enquanto continua reportando `n_trials=29` no dicionário de saída. Quem lê o
resultado vê o denominador, não vê que ele não foi usado.

**Agravante:** os testes do gate não exercitam a deflação real.
`tests/test_prospective_validation_scaffold.py:82,94` fazem
`monkeypatch.setattr(metrics.registry_module, "deflated_sharpe_ratio", lambda *_: {"dsr": 0.96})`.

**Ressalva de precisão, para não superdeclarar:** o contrafactual acima usa uma
série de retornos sintética (`random.gauss(0.02, 0.35)`, n=400, seed 1), não os
retornos reais do projeto. O que está demonstrado é a **sensibilidade do
mecanismo** ao preenchimento do registro, não que algum número publicado
específico esteja errado. Nenhum resultado publicado foi recalculado.

**O que derrubaria este achado:** uma justificativa documentada de por que
estimar `V[SR]` a partir de um subconjunto não representativo é conservador.
**O que o fecharia:** exigir `sharpe` (ou marcação explícita de não-aplicável)
em toda trial que entre no denominador; e fazer o DSR sinalizar, em vez de
degenerar em silêncio, quando `V[SR]` não for estimável.

---

## Achado 3 — Alto — Bypass do gate de atestação por sobrescrita de veredito

**Repositório:** core-predictor (`src/predictor_core/measurement/trials.py`,
`register_trial`) · **Confiança: alta (executado).**

O gate de atestação de poder está no ramo `else` de um `for … else`: ele só é
avaliado quando o `name` **não** existe no registro. O caminho de atualização —
mesmo `name`, mesmos `params` — atravessa sem passar por nenhuma verificação de
atestado.

Executado em cópia isolada do registro; o repositório real não foi tocado:

```
ANTES : refutada | sharpe 0.0722 | metric None

-> mesmos params EXATOS, mesma metric, status flipado, sharpe inflado:
   ACEITO -> status: comprovada | sharpe: 9.99
   atestado exigido? NÃO — o caminho de update não passa pelo gate.

$ git status --porcelain data/
(vazio — repositório real intocado)
```

Uma hipótese `refutada` vira `comprovada` sem atestado de controle positivo, e o
registro não guarda histórico do veredito anterior: o estado antigo desaparece.
Como o `status` é exatamente o que o `README.md` e o `HANDOFF.md` reportam ao
leitor, a alteração seria invisível na leitura normal do projeto.

**Defesa parcial observada:** o `sharpe` inflado (9,99) explodiu `SR0` para
11,76 e levou o `DSR` a 0 — o DSR se defende contra inflação do próprio sharpe.
Mas um flip de `status` com sharpe plausível, ou com `sharpe: null` (como é o
caso da única trial `comprovada` hoje), passaria sem sinal algum.

**O que o fecharia:** exigir atestado válido também no caminho de atualização
quando `status` ou `result` mudarem; e tornar o registro append-only quanto a
vereditos, preservando o estado anterior.

---

## Achado 4 — Alto — A wheel `predictor-ops 4.0.0` em produção nunca passou pelos gates de release

**Repositório:** predictor-ops · **Confiança: alta — confirmado por log de
execução, não por inferência.**

A wheel `predictor_ops-4.0.0-py3-none-any.whl` publicada como release asset é a
que o `brasileirao-predictor` consome em produção, com pin de SHA-256 em
`constraints/shared-wheels.sha256` e URL fixa em `[tool.uv.sources]`.

### Indício inicial: metadados de build incompatíveis com o pipeline

```
core  3.1.0 : create_system=3 (Unix),    LF,   release publicada por github-actions[bot]
ops   4.0.0 : create_system=0 (Windows), CRLF em 13/13 módulos,
              release publicada por leonardosovienski (humano)
```

`.github/workflows/release.yml` do ops roda em `ubuntu-latest`, e portanto não
pode produzir `create_system=0` nem CRLF. As releases `v3.0.0` e `v3.1.0` do ops
foram publicadas pelo `github-actions[bot]`; a `v4.0.0`, por humano. Há
precedente explícito: o corpo da release `v2.0.1` diz *"Wheel/sdist reproduzidos
localmente do commit 8d0ac13"*.

### Confirmação: a run de Release da tag falhou antes de qualquer gate

Cronologia verificada em 2026-09-05 pela API do GitHub
(run [33443380439](https://github.com/leonardosovienski/predictor-ops/actions/runs/33443380439)):

| Horário (UTC) | Evento |
|---|---|
| 31/08 21:50:49 | push da tag `v4.0.0` (commit `6b695ea`) dispara o workflow Release |
| 31/08 21:51:01 | `uv run pyright` falha, exit 1; o job `build` morre em ~12 s |
| 31/08 21:54:17 | release `v4.0.0` publicada por `leonardosovienski` (humano) |
| 31/08 22:53:30 | `workflow_dispatch` em `main` (`46cd8e2`) passa, mas o job `release` exige `refs/tags/` e não publica nada † |

† **Única linha desta tabela não verificada diretamente por esta auditoria.**
Foi reportada pelo mantenedor e é consistente com `release.yml` — o job
`release` tem `if: startsWith(github.ref, 'refs/tags/')`, de modo que um
`workflow_dispatch` em `main` de fato não publicaria asset algum. Mas a run em
si não foi lida: a API de listagem consultada não honrou o filtro por
`workflow_id` e isolá-la exigiria paginação extensa. As duas linhas que
sustentam o achado — a falha da run da tag e a publicação manual — foram
verificadas diretamente e estão transcritas abaixo. Confirmar esta terceira
linha não muda a conclusão; ela apenas mostra que houve uma tentativa
posterior de rodar o pipeline que não podia publicar.

Metadados da run 33443380439, verbatim: `"name":"Release"`, `"event":"push"`,
`"head_branch":"v4.0.0"`, `"head_sha":"6b695ea…"`, `"conclusion":"failure"`,
`"created_at":"2026-08-31T21:50:49Z"`, `"updated_at":"2026-08-31T21:51:04Z"`.

Log do job `Build and validate package`, verbatim:

```
2026-08-31T21:51:01.7978893Z /home/runner/work/predictor-ops/predictor-ops/tests_v2/test_models_config.py
2026-08-31T21:51:01.7985180Z   …/tests_v2/test_models_config.py:41:31 - error: Argument of type
   "Literal['redis']" cannot be assigned to parameter "backend" of type "Literal['local']"
   in function "__init__"
2026-08-31T21:51:01.7987773Z     "Literal['redis']" is not assignable to type "Literal['local']" (reportArgumentType)
2026-08-31T21:51:01.7988678Z 1 error, 0 warnings, 0 informations
2026-08-31T21:51:01.8466611Z ##[error]Process completed with exit code 1.
```

**Controle:** `v3.0.0` e `v3.1.0` tiveram runs de tag com `conclusion=success` e
releases publicadas pelo `github-actions[bot]` no mesmo minuto.

### Consequência

Na ordem de passos de `release.yml`, `pyright` é o terceiro gate. Passaram
apenas *Validate tag against project version* e *Ruff*. **Nunca executaram**,
para o artefato que está em produção: `pytest --cov`, `uvx pip-audit`,
`uv build`, o smoke da wheel em ambiente isolado e `actions/attest`
(atestação de proveniência do artefato).

### Precisão — o que este achado **não** afirma

Não houve substituição de conteúdo. A wheel publicada corresponde exatamente ao
commit da tag:

```
$ git archive 6b695ea src/predictor_ops | tar -x -C tagsrc
$ diff -rq --strip-trailing-cr wheel_extraida/predictor_ops tagsrc/src/predictor_ops
(saída vazia — idêntico)
```

Além disso, o erro do `pyright` era em `tests_v2/test_models_config.py`, arquivo
de teste, e não em `src/` — o runtime publicado provavelmente estava correto. O
defeito registrado é **a ausência de verificação**, não um defeito conhecido no
código publicado. A distinção importa: o sistema não mentiu sobre o conteúdo;
ele publicou sem o processo que garante o conteúdo.

**Agravante estrutural:** `release.yml` usa `gh release upload --clobber`, que
permite substituir um asset na mesma tag sem deixar rastro na release. O pin de
SHA-256 do consumidor é a única defesa contra isso — e ela pertence ao
consumidor, não ao publicador.

**O que o fecharia:** republicar `v4.0.0` (ou a versão sucessora) por uma run de
Release verde, com atestação; e tornar o processo de publicação manual
impossível ou explicitamente rastreável.

---

## Achado 5 — Médio — Colisão de versão `4.0.0` (já conhecido, correção em voo)

**Repositório:** predictor-ops · **Confiança: alta.**

O commit `ab41e6a` ("feat: add operational provenance contract"), presente em
`origin/main`, adicionou cinco campos públicos a `JobConfig`
(`config_version`, `input_reference`, `output_reference`, `retry_count`,
`host_or_environment`) e passou a emiti-los no registro de auditoria do runner,
mantendo `version = "4.0.0"` — a mesma versão da wheel publicada, que não os
contém.

```
$ diff --strip-trailing-cr -u wheel_v4.0.0/models.py  main/src/predictor_ops/models.py
+    config_version: str | None = None
+    input_reference: str | None = None
+    output_reference: str | None = None
+    retry_count: Annotated[int, Field(ge=0)] = 0
+    host_or_environment: str | None = None

$ sha256sum  (build de main)      661136d636965ebc728a85dcfbbd28f0364452c4199e15a8ec6966657a1e15aa
$ sha256sum  (wheel publicada)    a79b895492181c88c428ee8984a38d5f3da0d0105f060f89a061376d5cfe2b2b
```

`predictor-ops==4.0.0` designa dois conteúdos diferentes conforme a origem da
instalação. `tests_v2/test_version_contract.py` não detecta porque compara o
cabeçalho do CHANGELOG com `pyproject.toml`, e nenhum dos dois foi tocado.

**Registro honesto de autoria do achado:** este não é um achado desta auditoria.
O [PR #17](https://github.com/leonardosovienski/predictor-ops/pull/17) já o
documenta e propõe bump para `4.1.0` mais `.gitattributes`. Ele conta a favor da
tese central — o sistema detectou o problema sobre si mesmo. O que o PR **não**
identifica é a causa raiz do CRLF: ele a atribui à ausência de `.gitattributes`,
sem notar que `release.yml` roda em Linux e portanto a wheel publicada não saiu
do pipeline (achado 4). A descrição do PR merece correção nesse ponto.

---

## Achado 6 — Médio — O código que produz as evidências é o menos testado

**Repositório:** brasileirao-predictor · **Confiança: alta (medido).**

Cobertura por módulo, extraída da mesma execução que produziu os 50 % globais:

```
$ uv run coverage report --include='*research_xg_ensemble*,*backtest_walkforward*,…'
Name                                                   Stmts  Miss  Branch  BrPart  Cover
brasileirao_predictor/research/market_edge_ordering.py   135     3      38       2    97%
brasileirao_scripts/backtest_walkforward.py              212   162      74       2    22%
brasileirao_scripts/benchmark_predictor.py               320    97      98       6    69%
brasileirao_scripts/research_market_edge_ordering.py      43    43       4       0     0%
brasileirao_scripts/research_xg_ensemble.py              101    44      20       2    54%
brasileirao_scripts/trial_draw_calibration_a10.py         79    51      12       2    35%
```

`backtest_walkforward.py` (22 %) é quem calcula o DSR.
`research_xg_ensemble.py` (54 %) é quem produz o **único** veredito
`comprovada` do registro. O gate global de 45 %, com 50 % reais sobre 16.704
statements, é satisfeito por cobertura alta nos contratos, enquanto o caminho
que vai do dado bruto até a afirmação publicada fica na cauda inferior.

**O que o fecharia:** um gate de cobertura por categoria que trate os geradores
de evidência como categoria homologada (>80 %), em vez de diluí-los no global.

---

## Achado 7 — Baixo — Atestação de poder emitida de árvore de trabalho suja

**Repositório:** brasileirao-predictor (`data/trials.harness_attestation.json`) ·
**Confiança: alta.**

```json
"code_version": "git:08370d3e4403218c9fdd25612b691e39c7b7ae49;dirty",
"passed_at":  "2026-09-02T23:37:28Z",
"expires_at": "2026-09-09T23:37:28Z",
"pipeline_fingerprint": "3bbf3be2588d8440fe391a83743a2ef44176e01d5f1e04c2641a9e2252c9ca58"
```

O commit existe (`08370d3 feat: harden shadow economic decisions`), e o sufixo
`;dirty` é honesto: declara que havia modificações não commitadas. A
consequência é que o código que passou no controle positivo de poder — o
controle que autoriza registrar trials novas — **não é identificável**. A
atestação ainda estava válida na data desta auditoria (expira 2026-09-09).

**Nota de repositório:** o artefato vive no `brasileirao-predictor`, e é por isso
que a issue correspondente foi aberta lá e não no `predictor-ops`.

**O que o fecharia:** recusar emissão de atestação a partir de árvore suja, ou
registrar o diff junto do fingerprint.

---

## Sobre h12 — o único veredito `comprovada`

Submetido a ataque direto e **não derrubado na citação**. Cada número das notas
do registro bate exatamente com o artefato de evidência
`reports/research_xg_ensemble_2026-08-22.json`:

| Grandeza | Registro | Artefato |
|---|---|---|
| n | 1318 | 1318 |
| RPS com ensemble | 0,217749 | 0,21774923923782205 |
| RPS sem ensemble | 0,213339 | 0,21333924501140134 |
| ganho pareado | 0,004410 | 0,004409994226420718 |
| IC95 | [0,001436; 0,007741] | [0,0014361447785403748; 0,007741362272108646] |

A proveniência declara espontaneamente a limitação mais séria do próprio
resultado: *"NÃO é pré-registro cego: o efeito foi observado antes, em duas
corridas não pareadas… Este experimento acrescenta o IC95 pareado, na MESMA
amostra em que o efeito foi visto."* Isso é honestidade acima da média e deve
ser registrado como tal.

Onde h12 cai é no achado 1: `dataset_hash: UNKNOWN`, dataset ausente do
repositório, script gerador a 54 % de cobertura. **A citação é fiel; a reprodução
independente é impossível.** Note-se ainda que o DSR nunca toca h12
(`metric: rps`, `result.sharpe: null`) — o mecanismo anti-p-hacking do projeto
não se aplica ao único veredito positivo que ele possui.

---

## O que NÃO foi verificado, e por quê

Registrado explicitamente porque um "não testado" honesto vale mais que um
"provavelmente ok".

- **Job `dotnet` do CI do brasileirao** (worker .NET 10, gate de 80 % de linha
  *e* de branch): não reproduzido — `dotnet: command not found` no ambiente
  remoto.
- **Job `containers`** (`docker compose config/build/up --wait`, smoke
  `hotpath_smoke`, perda e reconexão do Redis, shutdown gracioso com verificação
  de exit code 0): não reproduzido — o binário `docker` existe, mas não há
  daemon; `docker info` falha.
- **Matriz Python 3.14**: não reproduzida localmente; apenas a perna 3.13 foi
  executada nos três repositórios.

  **Correção posterior a estes três itens.** A primeira redação deste documento
  afirmava "zero cobertura de auditoria" sobre o worker .NET e "nenhuma das
  garantias de compose foi exercida". Isso era mais forte que a evidência
  disponível, e a evidência estava a uma consulta de distância. A run
  [33932961360](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/33932961360),
  do commit `c1f6c48` deste mesmo documento, tem os quatro jobs verdes, com os
  passos nomeados individualmente:

  - `.NET 10 build and test` → `dotnet restore --locked-mode`, `dotnet build
    --warnaserror`, `dotnet test --collect:"XPlat Code Coverage"` e
    **`Enforce Worker line and branch coverage` com `conclusion: success`** —
    isto é, o gate de 80 % de linha e de branch passa.
  - `Compose build and health` → `docker compose config --quiet`, `build`,
    `up --detach --wait`, `Versioned Python Redis .NET smoke`,
    **`Redis loss and reconnection`** e **`Graceful shutdown`**, todos
    `success`.
  - `Python 3.14` → verde, mesma sequência da perna 3.13.

  A distinção que importa: isto **não** é verificação independente desta
  auditoria. Eu não reproduzi esses jobs nem li os números que eles produziram
  — li a conclusão de uma execução feita pela infraestrutura do próprio
  projeto, que é exatamente o tipo de afirmação que esta auditoria se propôs a
  não aceitar sem conferir. O estado correto destes três itens é "não
  reproduzido por esta auditoria, e verde no CI deste commit", não "zero
  cobertura" e não "verificado".

  **O que faria destes itens verificação de verdade:** um ambiente com daemon
  Docker e SDK .NET 10, onde os jobs sejam reexecutados à mão e os números
  reais de cobertura do worker (linha e branch) sejam lidos, em vez do
  booleano do gate.
- **Divergência de versões de ferramenta**: a auditoria usou `uv 0.8.17`,
  enquanto o CI fixa `0.12.1`; Redis local 7.0.15 contra `redis:8.2.1-alpine3.22`
  no CI. Os números de cobertura podem diferir na margem.
- **`uvx pip-audit` e `uvx detect-secrets` do predictor-ops**: não executados.
- **Reprodução numérica de h12**: impossível — o dataset não está disponível.
  Essa impossibilidade é o achado 1, não uma lacuna da auditoria.
- **Fora de escopo por decisão de orçamento**, priorizando profundidade no
  caminho dado bruto → afirmação publicada: os ~70 relatórios de `docs/`,
  o diretório `research/kimi_market05/`, e o exame individual das trials do
  registro uma a uma.

  Correção de 2026-09-06: a versão original desta linha dizia "as 27 trials com
  status `refutada`, `inconclusiva`, `exploratoria`, `substituida` e
  `pre-registrada`". O número estava errado e a lista misturava vereditos
  fechados com abertos. A contagem real, medida:

  ```
  $ python -c "import json,collections; print(collections.Counter(t['status'] for t in json.load(open('data/trials.json'))))"
  Counter({'pre-registrada': 8, 'refutada': 6, 'inconclusiva': 6,
           'informativa': 3, 'substituida': 3, 'exploratoria': 2, 'comprovada': 1})
  ```

  São 29 trials: **19 com veredito fechado** (`refutada`, `inconclusiva`,
  `informativa`, `substituida`, `comprovada`) e **10 em aberto** (8
  `pre-registrada` + 2 `exploratoria`). O erro era meu, na redação do escopo, e
  não afeta nenhum achado — o achado 1 mede 29/29 e essa contagem foi verificada
  em separado.

---

## Julgamento final

O ataque não foi fraco. Foram quebradas: a reprodutibilidade científica
(achado 1), o mecanismo anti-p-hacking (achado 2), o gate de governança
(achado 3) e a cadeia de publicação do ops (achado 4). Também não foram
quebradas: o pin de hash das wheels, a cadeia do core, as fronteiras de domínio
entre os três repositórios, a barreira de capital em nenhuma das duas camadas, e
o gate de atestação para trials novas.

O padrão é consistente e vale registrar como conclusão, não como impressão: **as
afirmações do ecossistema sobre engenharia são mais fortes que suas afirmações
sobre ciência.** O rótulo `ENGINEERING_READY / CAPITAL_BLOCKED` é preciso — a
engenharia está pronta e o capital está travado por código, não por convenção.
O que não se sustenta é a implicação de que o registro formal de hipóteses é
auditável por um terceiro. Ele é um formulário bem desenhado, com governança
real na entrada, e com o campo de proveniência em branco em 100 % das entradas.

---

## Adendo 2026-09-06 — estado das correções

Escrito no dia seguinte à auditoria, depois que o mantenedor autorizou as
correções em grupos. Nada acima foi reescrito: as seções de achado continuam
descrevendo o ecossistema de 2026-09-05. Esta seção registra o que mudou.

### Situação por achado

| # | Achado | Correção | Estado |
|---|---|---|---|
| 1 | 29/29 trials com proveniência `UNKNOWN` | brasileirao#59 | mergeado |
| 2 | DSR degenera em PSR sem sinalizar | core-predictor#24 | mergeado em `main`, **fora da wheel publicada** |
| 3 | Bypass do gate de atestação no caminho de update | core-predictor#23 | mergeado em `main`, **fora da wheel publicada** |
| 4 | Wheel `predictor-ops 4.0.0` nunca passou pelos gates | predictor-ops#17 + tag `v4.1.0` + brasileirao#60 | **fechado ponta a ponta** |
| 5 | Colisão de versão `4.0.0` | predictor-ops#17 | mergeado |
| 6 | Código gerador de evidência é o menos testado | brasileirao#59 | mergeado, com piso medido |
| 7 | Atestação a partir de árvore suja | core-predictor#22 | mergeado em `main`, **fora da wheel publicada** |

Todas as issues de achado foram fechadas, exceto predictor-ops#18, fechada por
verificação (abaixo).

### O que foi verificado, e não apenas afirmado

O achado 4 foi o único fechado com verificação byte a byte do artefato que
produção passou a consumir. A `v4.1.0` foi publicada pelo pipeline em
2026-09-05, e o pin só mudou depois de:

```
sha256         6d428a4d3d4fbd3f692725bf684024131f0fa65cc11d0e739e9ccb82ba9834e4
               (igual ao digest declarado pela API do GitHub)
create_system  3 (Unix)     — a 4.0.0 era 0 (Windows)
CRLF           0 de 13      — a 4.0.0 tinha 13 de 13
uploader       github-actions[bot], 21:43:58
conteúdo       `diff -rq` contra `git archive a9a4743 src/predictor_ops`
               vazio, sem normalizar terminadores de linha
```

Na `4.0.0` foi preciso `--strip-trailing-cr` para conseguir comparar. A run de
Release da `v4.1.0` (33993850404) executou todos os gates que nunca haviam
rodado para a `v4.0.0`: pytest, pip-audit, `uv build`, o smoke da wheel em venv
isolado e `actions/attest`.

### O achado 5 se repetiu no core — e continua aberto na prática

Os PRs core-predictor#22, #23 e #24 mergearam em `main` mantendo
`version = "3.1.0"`, a mesma versão da wheel publicada, que não contém nenhum
deles. Isso é literalmente o achado 5, agora no core: `predictor-core==3.1.0`
passou a designar dois conteúdos diferentes conforme a origem da instalação.

O core-predictor#25 corrigiu o número para `3.2.0` e mergeou em `main`
(`9fd8317`). **A tag `v3.2.0` não foi criada até a data deste adendo**, medido:

```
$ list_tags leonardosovienski/core-predictor
v3.1.0 (29eb8b7), v3.0.0, v2.3.0, v2.2.1, v2.2.0, v2.1.0, 1.0.1, 1.0.0
```

`29eb8b7` é o commit anterior aos quatro PRs. Consequência, e é a que importa:
**os achados 2, 3 e 7 estão corrigidos no repositório e ausentes da wheel que
o brasileirao instala.** Produção roda `predictor_core-3.1.0-py3-none-any.whl`.

Isso vale ser nomeado pelo que é: o ecossistema fechou o achado 5 no ops e
reproduziu o mesmo padrão no core dentro da mesma semana. A trava que faltava —
um teste que compare a versão do `pyproject` com a última release publicada, e
não com o CHANGELOG — continua faltando nos dois repositórios.

Fica bloqueado atrás da tag:

1. Atualizar o pin do brasileirao para core 3.2.0, com a mesma verificação byte
   a byte aplicada à ops 4.1.0.
2. Ligar `strict=True` do `deflated_sharpe_ratio` num gate. O parâmetro não
   existe na 3.1.0 pinada — verificado na wheel instalada, cuja assinatura é
   `(returns, trial_sharpes) -> dict`.

### O que continua sem correção, e por quê

- **O atestado de poder `data/trials.harness_attestation.json` ainda é o emitido
  a partir de árvore suja**, e expira em **2026-09-09**. Até lá ele continua
  destravando o registro de trials novas. Reemitir exige o `matches.db` real —
  `brasileirao_scripts/_attest_only.py` abre o banco para refitar os parâmetros
  — e a cópia disponível no ambiente de auditoria tem 0 linhas. É uma pendência
  operacional, na máquina do mantenedor, não uma decisão em aberto.

- **Fora de escopo desde o início e assim permanece**: os ~70 relatórios de
  `docs/` e a maior parte de `research/kimi_market05/`.

### Duas afirmações mais fortes que sua evidência, ainda no repositório

Encontradas durante a auditoria, reportadas e não corrigidas — as duas são
exatamente o tipo de coisa que a tese sob teste nega, então ficam registradas
mesmo sem correção:

1. `research/kimi_market05/bet_engine/bet_engine.py` afirma no docstring
   *"Casa lenta (edge real 8-18%): detectada, ROI +13.7%, DSR 0.999"*, enquanto
   a entrada correspondente do registro,
   `market-05-pinnacle-soft-structural-edge`, está como `pre-registrada` com a
   nota *"Hipótese registrada sem dados ou resultado econômico."* Um número
   econômico publicado num docstring contra uma hipótese que o registro declara
   sem resultado.

2. `brasileirao_scripts/_attest_only.py` continua versionado apesar do próprio
   docstring instruir *"Apague este arquivo depois de rodar; nao faz parte do
   repo canonico"*.

### Julgamento revisado

O veredito de 2026-09-05 não muda: a tese se sustenta na engenharia e falha na
ciência. O que o dia seguinte acrescenta é uma observação sobre o mecanismo de
correção em si — **corrigir no repositório não é corrigir em produção**, e o
ecossistema demonstrou duas vezes, em repositórios diferentes, que não tem
trava para essa distância. Enquanto a `v3.2.0` não existir, três dos sete
achados estão fechados no rastreador e vivos no artefato.

---

## Adendo 2026-09-06 (segunda entrada) — encerramento, e duas coisas que eu li errado

O adendo acima foi escrito de manhã, quando a tag `v3.2.0` ainda não existia e
três achados estavam corrigidos só no repositório. À tarde a tag saiu e o resto
foi fechado. Esta entrada registra o encerramento e, principalmente, **dois
erros meus na auditoria original**, porque um relatório que só acumula acertos
não é um relatório.

### O estado final, medido

```
main do brasileirao-predictor    0fae082
predictor_core-3.2.0             9166dd6bd3be99668c0eb8bd3c59a92061e765186608465c0caf48a2417e3009
predictor_ops-4.1.0              6d428a4d3d4fbd3f692725bf684024131f0fa65cc11d0e739e9ccb82ba9834e4
atestado core_version            3.2.0
atestado code_version            package:3.2.0;git:61f72e7b1d0abb35fcbcb96561ab10ad31f13525
atestado expires_at              2026-09-13T16:42:06Z
pipeline_fingerprint             3bbf3be2588d8440fe391a83743a2ef44176e01d5f1e04c2641a9e2252c9ca58
```

Os sete achados estão fechados **no repositório e no artefato**. Até a manhã de
2026-09-06 três deles existiam apenas no `main` do core; a wheel que produção
instalava não os continha.

A `v3.2.0` foi publicada pelo pipeline (run 34045356305, 13 passos verdes) e
verificada byte a byte antes de qualquer pin mudar: sha256 igual ao digest da
API, `create_system=3`, 0 CRLF em 41 módulos, `diff -rq` vazio contra
`git archive 9fd8317 src/predictor_core` sem normalizar terminadores, e upload
por `github-actions[bot]`. As três correções foram conferidas **importando da
wheel**, não do checkout.

Por que a tag demorou: ela existia como **rascunho** desde as 02:52 e só foi
publicada às 16:24. Uma release em rascunho não cria a tag, e sem a tag o
`release.yml` (gatilho `v*.*.*`) nunca dispara.

### Erro meu 1 — o `;dirty` do achado 7 era, em boa parte, bug do produtor

O achado 7 afirmou que o atestado vigente fora "emitido a partir de árvore de
trabalho suja". Eu li o campo `code_version` pelo valor de face.

Ao reemitir, o script saiu `;dirty` a partir de uma árvore **comprovadamente
limpa** (`git status --porcelain` vazio antes de rodar). Causa, em
`brasileirao_scripts/renew_core3_harness.py`:

```python
def run() -> dict:
    record = attest_rps_power()      # <- ESCREVE o arquivo do atestado
    ...
    "code_version": _code_version(), # <- e SO ENTAO mede a arvore
```

`_code_version()` rodava `git status --porcelain` depois de a própria função
ter escrito `data/trials.harness_attestation.json`. A árvore estava suja pela
escrita do próprio atestado. O campo mentia por defeito de ordenação, não por
estado do repositório.

**O que o achado 7 acertou mesmo assim:** o campo era inútil como garantia de
reprodutibilidade, e um consumidor não tinha como distinguir "árvore realmente
suja" de "artefato do produtor". A correção certa continua sendo a do core
3.2.0 — gravar `code_version` dentro de `attest_pipeline_power`, antes da
escrita, e recusar árvore suja.

Um teste estava **protegendo o defeito**: `test_core3_harness_contract` exigia
`code_version.startswith("git:")`, exatamente o formato pobre que o override
com bug produzia. Substituído por um teste que exige o contrário.

### Erro meu 2 — eu apontei o script errado para reemitir o atestado

Registrei no relatório, na issue #62 e num comentário de PR que reemitir o
atestado exigia a `matches.db` real e só era possível na máquina do mantenedor.
**Falso, e o erro foi propagado para três lugares.**

O `brasileirao_scripts/_attest_only.py` de fato abre o banco — mas não é ele
quem produz este atestado. O campo `note` do arquivo committado diz
`RESEARCH-01A`, e o produtor é o `renew_core3_harness.py`, cujo
`attest_rps_power` é **puramente sintético**: `probabilistic_predictor` com
seeds fixas 13 e 17, e `dataset_reference_fingerprint` é o hash de um JSON
constante, não do banco. Nunca abre `matches.db`.

A lição que sobra: eu identifiquei o produtor por proximidade de nome em vez de
casar o campo `note` do artefato com o script que o escreve. O artefato dizia
quem o produziu; eu não li.

### Um achado novo, que só apareceu porque o gate novo existe

Depois da reemissão o CI continuou vermelho com o local verde:

```
FAILED tests/test_h10_fadiga_walkforward.py::test_main_registers_a_new_trial_with_attestation
DirtyWorkingTreeError: árvore de trabalho suja (package:3.2.0;git:438d3937...;dirty)
```

O passo `Verify canonical shared wheel hashes` do `ci.yml` baixa as wheels
canônicas para **`wheelhouse/`**, e esse diretório **não estava no
`.gitignore`** — enquanto o `.wheelhouse-e2e/`, que faz o mesmo no job de
containers, estava.

Reproduzido em clone limpo antes de corrigir:

```
git status → limpo   →  package:3.2.0;git:7d2fc09
mkdir wheelhouse/    →  package:3.2.0;git:7d2fc09;dirty
```

**A árvore do CI sempre esteve suja durante o pytest inteiro**, do passo 6 em
diante. O gate do core 3.2.0 não introduziu o problema — expôs um que já
existia e passava calado, porque o core 3.1.0 não olhava. Qualquer atestado
emitido em CI teria nascido `;dirty` sem ninguém notar.

Virado contrato em `tests/test_ci_nao_suja_a_arvore.py`, com dois testes: todo
diretório de artefato do CI tem que estar ignorado, e a lista não envelhece —
se o `ci.yml` ganhar um `--output` para diretório não catalogado, falha.

Isso generaliza o achado 7: a limpeza da árvore virou propriedade **do
pipeline**, não só do desenvolvedor.

### O achado 2 saiu do papel e virou trava de capital

`brasileirao_predictor/research/prospective_validation/metrics.py` é o gate de
capital: `eligible = ... dsr >= policy.dsr_gate`. Era ali que o achado 2 mordia
— com menos de dois sharpes finitos no denominador, o SR0 não é estimável, o
DSR degenera em PSR puro, e um número alto sem desconto aplicado é
indistinguível de um descontado. **Ele destravava o gate.**

Agora usa `strict=True`, e a não-estimabilidade **trava**: `dsr` vira `None`,
o gate fica `LOCKED`, e o relatório carrega `dsr_deflation_applied`,
`dsr_sr0_estimable`, `dsr_sharpe_coverage` e `dsr_not_estimable_reason` — um
`None` sem motivo é indistinguível de "ainda não calculado".

`market_edge_ordering.py` **não** usa `strict`: é caminho de pesquisa, reporta
e não decide. Publica os mesmos diagnósticos.

Dois dubles de teste devolviam `{"dsr": 0.96}` — um retorno que esconde
exatamente o que o achado expôs. Substituídos por um duble que respeita o
contrato inteiro.

### A trava que continua faltando

Não existe, em nenhum dos três repositórios, um teste que compare a versão do
`pyproject.toml` com a **última release publicada**. O `test_version_contract`
do ops compara `pyproject` com `CHANGELOG`, e os dois estavam consistentes nas
duas vezes em que a divergência aconteceu — porque nenhum dos dois sabe o que
está publicado.

Isso deixou passar o achado 5 no ops e o repetiu no core na mesma semana. É a
única recomendação desta auditoria que **não foi implementada**.

### Inventário de branches (2026-09-06)

Levantado ao fim da sessão, e vale registrar porque não é óbvio:
`brasileirao-predictor` tem **duas histórias git disjuntas**.

```
raiz do main                    b3468e74
raiz de 8 branches de agosto    bc74926f
```

As oito (`agent/h9-runtime-collection`, `claude/affectionate-cannon-ds4j6j`,
`claude/brasileirao-p0-housekeeping-tlyyds`,
`claude/brasileirao-predictor-overview-e6r03o`,
`claude/brasileirao-setup-push-yndysg`,
`claude/predictor-ecosystem-audit-srpwl3`, `fix/f0-wheel-integrity`,
`p1/ecosystem-plugin-v1`) não têm ancestral comum com o `main`: o repositório
foi refeito entre 2026-08-23 e 2026-09-04.

Conteúdo conferido arquivo a arquivo: cada uma tem 5–6 arquivos ausentes do
`main`, todos no layout antigo (`src/`, `scripts/`) que virou
`brasileirao_predictor/` e `brasileirao_scripts/`. Todos têm sucessor, e o do
`main` é maior (`model.py` 257 → 421 linhas, `economic_decision.py` 41 → 95).
Nenhuma linha de código se perde ao apagá-las; a história de agosto, sim.

O `main` tem ~4,29 milhões de linhas que elas não têm, quase todas em
`reports/ou25_v2/*.json`.

### Julgamento, terceira e última revisão

O veredito de 2026-09-05 continua de pé: a tese se sustenta na engenharia e
falha na ciência. Nada feito em 2026-09-06 torna as 29 trials históricas
reproduzíveis — elas seguem com proveniência `UNKNOWN`. O que existe agora é a
trava que impede a trigésima de nascer assim.

O que os dois dias acrescentam é uma observação sobre auditoria, não sobre o
ecossistema: **dois dos sete achados estavam parcialmente mal lidos, e os dois
erros só apareceram quando alguém tentou executar a correção.** Ler um artefato
não é o mesmo que reproduzi-lo. O achado 7 leu um campo; quem reemitiu
descobriu que o campo mentia por bug. O relatório afirmou que a reemissão
exigia um banco; quem tentou reemitir descobriu que não.

Isso é exatamente o que a tese sob teste dizia — *"um terceiro consegue
verificar isso sozinho"*. A auditoria também está sujeita a ela.

### Onde foi parar o que não cabe num relatório

O estado que não está versionado — `matches.db`, o procedimento de renovação do
atestado de poder, a coleta agendada no Windows Task Scheduler, as diferenças
entre ambiente local/CI/sandbox e as permissões de sessão automatizada — foi
escrito em [`ESTADO_LOCAL_E_OPERACAO.md`](ESTADO_LOCAL_E_OPERACAO.md).

Motivo de existir um segundo documento: este aqui é um **registro datado** de
uma auditoria e não deve ser reescrito. Aquele é **operacional** e envelhece —
o atestado vence a cada 7 dias, as tarefas do agendador ligam e desligam, o
sandbox muda. Misturar os dois faria o registro apodrecer ou o runbook mentir.
