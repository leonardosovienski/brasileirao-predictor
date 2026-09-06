# Estado local e operação — o que não está neste repositório

Criado em 2026-09-06, ao fim da auditoria adversarial.

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

**Onde:** máquina Windows do mantenedor, tarefas com prefixo `brasileirao-*`.

**Estado informado pelo mantenedor:** **desabilitadas em 2026-09-04.**

**Consequência, e isto não é defeito:** qualquer série prospectiva que pare
depois de 2026-09-04 parou porque a coleta foi desligada. Uma auditoria futura
que encontre séries truncadas nessa data não deve registrar isso como bug de
pipeline.

`tests/test_windows_scheduler_contract.py` valida o contrato das tarefas, não o
estado ligado/desligado delas — o teste passar não significa que a coleta esteja
rodando.

**Não verificado por mim:** não tenho acesso à máquina. Confirme antes de tirar
conclusões de qualquer série interrompida.

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
