# Consolidação da main — 08/09/2026

O pedido desta etapa é reunir o conteúdo útil das branches na `main` e remover
as outras branches. A integração une a main local `d42a3e0` à main publicada
`3a88f31`, com base comum `7b5f83`. O histórico não é reescrito.

## Conteúdo preservado

As duas branches Claude ainda publicadas (`audit-predictor-ecosystem-cvx0wg` e
`auditoria-projetos-esr8na`) já são ancestrais de `3a88f31`. A branch
`codex/session-2026-09-07-validated` é ancestral de `d42a3e0`. As nove refs locais
obsoletas, que o fetch podou por já não existirem no GitHub, também são ancestrais
da main remota. Portanto, os 12 históricos estão cobertos pelos dois pais desta
consolidação; não há commit exclusivo a descartar.

Foram mantidos o runtime Redis v2, inbox/ACK, outbox, leases, health e os testes
da sessão local. Da main remota vieram Core 3.2.0, Ops 4.1.0, locks/hashes,
DSR estrito, proveniência de trials, cobertura de geradores de evidência,
avaliadores prospectivos e auditorias. Docker conserva a instalação por lock
e hashes. O CI conserva Redis descartável identificado por run_id e Compose
isolado por execução. Os checkpoints anteriores continuam como histórico.

Os registros versionados `data/trials.json`, `data/trials.v2.json` e
`data/trials.harness_attestation.json` incorporam as versões já publicadas na
main remota: normalização de vocabulário e atestado preexistente de Core 3.2.0.
Nenhum atestado operacional foi gerado nesta etapa. As versões anteriores
continuam nos pais Git e nos bundles de segurança. Nenhum banco operacional,
ledger, coorte, agenda ou resultado científico foi recalculado.

## Correções necessárias na integração

- A dependência mínima declarada agora exige Core 3.2, pois o código incorporado
  usa suas APIs. O lock permaneceu idêntico após `uv lock --offline`; a metadata
  da wheel construída também foi conferida.
- H14/H15 adquirem uma trava exclusiva antes das leituras e métricas. Sucesso,
  erro ou interrupção conservam a trava; somente `AGUARDANDO_N` a libera.
  Alterar a pasta do relatório ou o caminho do registro não libera nova tentativa.
  Transportar o ledger junto da pasta `.prospective_evaluation_claims` conserva
  a trava em outra raiz Windows. Renomear/copiar deliberadamente o dataset não
  é uma identidade rastreável por este mecanismo de filesystem e continua
  sujeito à mesma política de governança.
- O relatório é publicado completo por hardlink atômico, sem sobrescrita.
  Filesystems sem esse recurso falham com a trava preservada. Os dois corpos
  científicos são idênticos aos originais por comparação AST; limiares, sementes,
  tamanho da coorte e critérios de aprovação não foram alterados.
- A fixture Windows de término da árvore de processos foi revisada porque o
  descendente terminava naturalmente apenas 300 ms depois do timeout. O
  `taskkill` medido demorou cerca de 410–440 ms, tornando a fixture uma corrida.
  A verificação passa a observar a morte do processo no heartbeat final com
  uma janela de vida suficiente. O runtime conserva o erro explícito quando
  não pode confirmar a limpeza da árvore.

## Verificação e publicação

A preparação ocorreu em worktree destacada e ambiente virtual próprios, com
Core 3.2.0/Ops 4.1.0. A instalação operacional Core 3.1.0/Ops 4.0.0 não foi
atualizada. Os testes usam dados sintéticos e caminhos isolados; acesso Python
a dados operacionais e rede externa foi bloqueado no executor de validação.

Os 39 testes específicos de H14/H15, Ruff, formatação, Pyright e metadata da
wheel passaram. A primeira suíte ampla encontrou duas falhas: a corrida da
fixture acima e a recusa correta de Core 3.2 a emitir um atestado sintético em
árvore ainda suja pelo merge. O aceite final exige repetir a suíte no commit
limpo, sem desabilitar a exigência de proveniência.

No commit limpo `3db29a8`, passaram 1.541 testes locais (um skip de plataforma,
30 integrações reservadas ao Redis isolado), Ruff, Pyright e os gates de
cobertura global e por categoria. O primeiro CI desse commit passou Python
3.13 e 3.14, incluindo Redis, mas encontrou uma fixture .NET incompleta:
o subprocesso de health recebia apenas os caminhos VORP/titularidade e herdava
implicitamente Redis/bancos do ambiente. No runner Linux essas três variáveis
não existiam, levando à saída 134 antes da verificação de saúde. A fixture
passa a fornecer Redis descartável e os dois caminhos sintéticos explicitamente,
e a mostrar a saída do subprocesso em caso de falha. A validação de configuração
do Worker em produção foi preservada. O resultado do novo CI deve ser associado
ao commit da correção, conforme o recibo final abaixo.

Os resultados finais, SHA consolidado, inventários local/remoto e remoções
confirmadas são registrados fora da árvore versionada em
`outputs/GIT_MAIN_UNICA/ESTADO_FINAL.json`, na pasta da tarefa de origem.
Os logs locais ficam em `work/main_consolidation/validation`. O CI do GitHub
deve ser consultado pelo SHA publicado; um CI verde do pai remoto não valida
este merge. A remoção de cada branch exige que seu SHA ainda seja o auditado e
ancestral da main publicada. Os bundles anteriores às operações preservam as
refs originais, sem recriar branches no repositório ativo.

## Migração

O ZIP de dados já entregue é uma captura imutável vinculada a `d42a3e0`.
Consolidar branches não atualiza essa captura. O novo bundle da main inclui
esse commit no histórico, permitindo tanto reproduzir a captura quanto adotar
o código consolidado. Não sobrescreva registros versionados mais novos com os
antigos do ZIP. Preserve junto do ledger qualquer estado de avaliação única
criado posteriormente, inclusive pastas ocultas. Consulte `docs/MIGRACAO_WINDOWS.md`.

Esta etapa não comprova lucro, não reabre estudos fechados e não implanta serviços
no computador de destino. Os limites operacionais do host Windows/Docker
descritos nos checkpoints anteriores continuam independentes da consolidação Git.
