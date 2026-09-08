# Estado local e operação — o que não está neste repositório

Criado em 2026-09-06, ao fim da auditoria adversarial.

Esta é a referência histórica daquela auditoria. A consolidação de 08/09 reuniu
o código das duas `main`; consulte primeiro `HANDOFF.md` para o estado de código
e validação mais recente. Os dados privados e o ambiente instalado de cada PC
continuam exigindo conferência local. Integrar commits não executa renovação de
atestados, avaliação de coortes ou importação de tarefas.

Este documento existe porque partes do sistema **não estão versionadas e não
são reconstruíveis a partir deste repositório**. Sem elas escritas em algum
lugar, a informação vive só na cabeça do mantenedor ou num chat que vai ser
apagado. Cada item diz **onde está**, **quem depende**, e **o que acontece se
sumir**.

Fatos operacionais aqui foram informados pelo mantenedor ou medidos em
2026-09-06. Onde não foram verificados por mim, está dito.

---

## 1. `data/matches.db` — o banco de partidas

**Onde:** apenas na máquina Windows do mantenedor, em `data/matches.db` na raiz
do clone.

**Por que não está aqui:** `.gitignore` linha `*.db`. Deliberado — o repositório
lê produção read-only e não versiona dado.

**Quem depende:**

- `brasileirao_scripts/_attest_only.py` — abre o banco read-only e refita os
  parâmetros pré-teste (`_fit_params_pre_teste`).
- `brasileirao_scripts/governanca.py` e o pipeline de pesquisa em geral.
- **Não** depende: `brasileirao_scripts/renew_core3_harness.py`, que é quem
  emite o atestado de poder vigente. Ver seção 2.

**Se sumir:** reconstruível por ingestão (`sync_matches_from_sofascore.py`), mas
o histórico coletado prospectivamente não volta — ver seção 3.

**Medido em 2026-09-06:** a cópia presente no ambiente remoto de auditoria tem
`matches: 0` linhas. Qualquer script que dependa do banco falha ou produz lixo
lá. Só a máquina do mantenedor tem o banco real.

---

## 2. Atestado de poder — `data/trials.harness_attestation.json`

Este arquivo **é versionado de propósito** (exceção explícita no `.gitignore`),
mas o procedimento de renovação não estava escrito em lugar nenhum.

**O que ele faz:** destrava o registro de trials novas. Sem atestado válido,
`register_trial` levanta `PowerAttestationMissingError`.

**Validade: 7 dias.** Estado em 2026-09-06:

```
core_version   3.2.0
code_version   package:3.2.0;git:61f72e7b1d0abb35fcbcb96561ab10ad31f13525
expires_at     2026-09-13T16:42:06Z
fingerprint    3bbf3be2588d8440fe391a83743a2ef44176e01d5f1e04c2641a9e2252c9ca58
```

**Quem o emite — importante, e já foi documentado errado uma vez:**

```
brasileirao_scripts/renew_core3_harness.py
```

O campo `note` do arquivo (`RESEARCH-01A: ...`) identifica o produtor. Ele é
**puramente sintético**: `probabilistic_predictor` com seeds fixas 13 e 17, e
`dataset_reference_fingerprint` é o hash de um JSON constante. **Não abre
`matches.db`** e roda em qualquer lugar, inclusive CI.

O `_attest_only.py` **não** é o produtor deste atestado, apesar do nome
sugestivo — ele é a etapa 1 do `governanca.py` e precisa do banco. A auditoria
adversarial apontou o script errado e propagou o erro para três lugares; ver
`AUDITORIA_ADVERSARIAL_2026-09-05.md`, adendo de 2026-09-06 (segunda entrada).

**Como renovar:**

```
git status --porcelain            # TEM que sair vazio
uv run python brasileirao_scripts/renew_core3_harness.py
git add data/trials.harness_attestation.json && git commit && git push
```

A árvore precisa estar limpa: desde o `predictor-core` 3.2.0,
`attest_pipeline_power` recusa árvore suja com `DirtyWorkingTreeError`. Um
atestado cujo `code_version` termina em `;dirty` destrava trials que ninguém
consegue reproduzir.

**Dois gates invalidam o atestado antes do prazo:**

1. **Subir a versão do `predictor-core`.** O registro compara
   `attestation["core_version"]` com a versão instalada e recusa se diferirem.
   Todo bump de core exige reemissão — foi o que travou o PR #63.
2. **Árvore suja no momento da emissão** (acima).

**Sinal de que expirou:** `PowerAttestationMissingError: atestado expirado`, ou
o skip em `tests/test_prereg_serving_vs_climatologia.py`.

---

## 3. Coleta prospectiva agendada — Windows Task Scheduler

**Onde:** máquina Windows do mantenedor.

> **Correção de 2026-09-06.** A primeira versão desta seção dizia que as
> tarefas `brasileirao-*` estavam "desabilitadas em 2026-09-04", como se fosse
> todas. **Está errado.** Foi generalização minha a partir de uma informação
> sobre um trilho específico, sem cruzar com o `HANDOFF.md`, que diz o
> contrário para os outros. Um leitor concluiria que a coleta parou — quando há
> relógio correndo. Segue o quadro real.

Há **quatro grupos distintos**, e o estado difere entre eles:

| Grupo | Tarefas | Estado (fonte: `HANDOFF.md`) |
|---|---|---|
| H3/H5 antigo (`sombra.py`, bookmaker fixo) | 4 tarefas | **desabilitadas** — dormente, não descontinuado |
| H8/H9 (bookmaker dinâmico) | `brasileirao-market-research` (6h), `brasileirao-prospective-readiness` (diária) | ativos e saudáveis |
| H14/H15 persist | `brasileirao-h14-persist`, `brasileirao-h15-persist` (15min) | rodados pelo operador em 2026-09-04, `LastTaskResult=0` |
| Coletor A1 | `brasileirao-a1-collect`, `-discover`, `-metrics` | **confirmadas rodando** desde 2026-09-04, `LastTaskResult=0` |

**Consequência para leitura de séries:** uma série do trilho H3/H5 que pare não
indica defeito de pipeline — aquele trilho está dormente por decisão. Uma série
dos outros três que pare **é** sinal de problema.

**Não verificado por mim:** não tenho acesso à máquina. Tudo acima vem do
`HANDOFF.md` e do que o mantenedor informou. Confirme com
`Get-ScheduledTask brasileirao-*` antes de concluir qualquer coisa.

`tests/test_windows_scheduler_contract.py` valida o **contrato** das tarefas,
não o estado ligado/desligado — o teste passar não significa que a coleta esteja
rodando.

---

## 3b. Prazos em aberto

Itens com relógio correndo. Estes são os que apodrecem se ninguém olhar.

| Prazo | O que é | O que acontece se passar |
|---|---|---|
| **2026-09-10/11** | Relógio de 7 dias do coletor A1, iniciado em 2026-09-04 | `market05-a1-shadow` continua bloqueada; a homologação não avança |
| **2026-09-13** | Validade do atestado de poder (seção 2) | Registro de trials novas trava com `PowerAttestationMissingError` |

Sobre o A1: continua **`REHEARSAL_ONLY`** no plano gratuito da API — a
homologação formal provavelmente exige plano pago. Nenhum campo de trial foi
editado manualmente para simular a evidência do relógio; fazer isso seria
fabricar dado.

---

## 3c. Outros artefatos que só existem na máquina do operador

Levantados do `HANDOFF.md` em 2026-09-06. Não estavam nesta lista na primeira
versão do documento.

- **`data/collector_metrics/key_rotation_attestation.json`** — atestado de
  rotação da `ODDSPAPI_KEY`, gerado pelo operador. Arquivo local, **fora do
  Git**. Sem ele não há prova de quando a chave foi rotacionada.
- **`ODDSPAPI_KEY`** — credencial do coletor A1. Rotacionada e atestada pelo
  operador. Não versionada, como deve ser.
- **Preservação offsite: `preservation.status=BLOCKED`.** Há **2 caminhos
  `UNKNOWN`** que, segundo o `HANDOFF.md`, "só são localizáveis na máquina do
  operador". Essa é a única menção a eles em todo o repositório — não há código,
  manifesto ou script que os defina. **Se a máquina se perder, ninguém sabe o
  que deveria estar preservado offsite.** É o item mais frágil deste documento.
- **4 trials PIT** (escalação, xG isolado, mando hierárquico) travadas por
  `training_gate`. Decisão de governança explícita, não dado ou código faltando
  — registrada aqui para que uma auditoria futura não a leia como defeito.

---

## 4. Ambiente do mantenedor vs. ambiente de CI vs. sandbox

Diferenças que já causaram diagnóstico errado pelo menos uma vez.

| Item | Máquina local | CI | Sandbox de auditoria |
|---|---|---|---|
| `uv` | 0.8.17 | 0.12.1 (fixado) | 0.8.17 |
| Redis | nativo | `redis:8.2.1-alpine3.22` (container, com módulos) | `redis-server` nativo |
| Docker | — | sim | **sem daemon** |
| .NET SDK | sim | `setup-dotnet@v6` | **não instalável** |
| `matches.db` | real | ausente | 0 linhas |

**Consequências práticas:**

- Números de cobertura podem diferir na margem entre local e CI.
- No sandbox, `uv run --isolated` com `--with <url>` pode falhar com **401 do
  `objects.githubusercontent.com`** — é o proxy, não o código. Controle que
  confirma: falha também numa wheel não modificada, e `curl` na mesma URL
  devolve o hash correto. Foi visto em 2026-09-05 e o CI passou no mesmo passo.
- **A árvore do CI fica com `wheelhouse/` a partir do passo `Verify canonical
  shared wheel hashes`.** Já está no `.gitignore` desde 2026-09-06, e
  `tests/test_ci_nao_suja_a_arvore.py` impede a regressão. Se algum passo novo
  do `ci.yml` escrever num diretório não ignorado, a emissão de atestado passa a
  produzir `;dirty` — ou a falhar.

**Estado do sandbox informado como podendo ter mudado.** Confirme antes de
concluir que algo é limitação de ambiente.

---

## 5. Permissões de sessão automatizada

Sessões do Claude Code neste projeto empurram **branches**, mas recebem
**403 em `refs/tags/*`**. Confirmado por tentativa direta em 2026-09-05 e
2026-09-06.

**Consequência:** toda release é manual. E há uma armadilha já observada:

> Uma release salva como **rascunho** não cria a tag. Sem tag, o `release.yml`
> (gatilho `v*.*.*`) nunca dispara, e a wheel nunca é publicada. A `v3.2.0`
> ficou em rascunho das 02:52 às 16:24 de 2026-09-06 exatamente por isso.

O prefixo `v` é obrigatório: `3.2.0` puro não aciona nada.

**Como conferir que a release saiu certa:** a wheel anexada tem que ter sido
subida por **`github-actions[bot]`**, não pelo seu usuário. O autor da *release*
será você (você clicou em Publish); o autor do *asset* é que distingue pipeline
de upload manual. Foi assim que o achado 4 foi detectado.

---

## 6. Fora do repositório e fora de escopo

Nunca auditado, declarado desde o início por orçamento:

- ~70 relatórios em `docs/`.
- A maior parte de `research/kimi_market05/`.

E uma afirmação conhecida e não corrigida:
`research/kimi_market05/bet_engine/bet_engine.py` publica ROI e DSR de
simulação num docstring, contra uma hipótese que o registro declara
`pre-registrada`. O docstring foi anotado em 2026-09-06 para dizer que os
números são sintéticos, mas a divergência com o registro permanece.

---

## 7. A trava que falta

Não existe, em nenhum dos três repositórios, teste que compare a versão do
`pyproject.toml` com a **última release publicada**. O `test_version_contract`
do `predictor-ops` compara `pyproject` com `CHANGELOG` — e os dois estavam
consistentes nas duas vezes em que a divergência aconteceu, porque nenhum dos
dois sabe o que está publicado.

Isso deixou passar o achado 5 no `predictor-ops` e o repetiu no
`predictor-core` na mesma semana: PRs mergeados em `main` mantendo a versão de
uma wheel já publicada que não os continha.

É a única recomendação da auditoria adversarial que **não foi implementada**.
