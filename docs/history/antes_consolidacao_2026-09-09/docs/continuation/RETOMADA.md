# Retomada independente do chat — 7 de setembro de 2026

> Continuação em **09/09/2026**, pasta `C:/BRASILEIRAO/brasileirao-predictor`:
> [preço executável e fronteira econômica](price_feasibility_2026-09-09/RESULTADO.md).
> Main remota f003045 recuperada, ambiente de pesquisa Python 3.13.12 isolado.
> 374/380 vetores 1X2 válidos, zero pares de preços admissíveis por falta de
> casa/clocks. Mediana de melhoria necessária 7,83% no cenário de custo 2%,
> sem oferta independente observada. Rodada encerrada com bloqueio demonstrado;
> sem uso de labels/coortes protegidas, coleta nova, promoção ou capital.
> O pacote de migração original foi preservado; a operação não foi instalada.

> Etapa mais recente: [continuação Docker](docker_completion_2026-09-08/RESULTADO.md).
> Fixture de teste corrigida; validações offline passaram. Acesso administrativo
> não foi concedido pelo Windows; Compose continua sem execução em containers.
> Ler o primeiro checkpoint do HANDOFF e os limites do relatório.


> Etapa mais recente: [recuperação e pendências de software](runtime_recovery_2026-09-08/RESULTADO.md).
> Inbox, ready, outbox, watchdog persistente e health corrigidos e testados.
> Redis e processos reais validados; Compose ainda depende de correção do host.
> Ler primeiro checkpoint do HANDOFF, estado.json e limites de migração.
> Nenhum resultado econômico novo ou capital liberado.


> Etapa mais recente: [correções do runtime v2](runtime_v2_2026-09-08/RESULTADO.md).
> Respostas antigas, lease/retry, descarte de fila e saúde corrigidos. Passaram
> 151 unitários Python, 18 integrações Redis, 81 .NET e 1 entre processos.
> Redis real validado; ambiente temporário removido. Compose/CI remoto pendentes.
> Produtor e consumidor devem migrar juntos. Ler os limites no relatório e o
> primeiro checkpoint do HANDOFF. Não houve novo resultado econômico.


> Etapa mais recente: [revisão do chat completo](whole_chat_review_2026-09-08/RESULTADO.md).
> Quatro falhas de pesquisa corrigidas; 230 testes passaram/1 skip; Ruff e Pyright
> dirigidos passaram. Duas limitações do runtime foram reproduzidas e permanecem
> pendentes, junto de Redis/Compose. Nenhum novo backtest ou resultado econômico.
> Auditoria dos dados deveria preceder a modelagem; 2025 segue exploratório;
> verificações anteriores foram internas por implementações separadas.
> Ler o primeiro checkpoint do HANDOFF e o estado desta revisão.


> Etapa mais recente: [diagnóstico dos erros/acertos e tentativa de correção](price_strength_diagnosis_2026-09-07/RESULTADO.md).
> Três reparos de integridade; nova combinação raw/mercado aprendida só em 2024,
> testada uma vez em 2025 já visto. Nos mesmos 362 jogos, −23,373u / 170 apostas
> contra xG calibrado −65,850u / 307 apostas. ROI novo −13,75%, pior que o bruto
> (−7,96%); contra raw,
> ganho líquido é economia de custos. 1X2 copia mercado, sem edge demonstrado.
> Quarentena de zeros não muda apostas no comum. Estudos anteriores preservados;
> investigação encerrada sem retune/promoção. Ler primeiro checkpoint do HANDOFF.

> Teste posterior: [xG em histórico 2025](price_strength_evaluation_2026-09-07/RESULTADO.md).
> Resultado negativo/misto: calibrado −22,02% ROI hipotético, bruto −8,23%,
> anterior bruto −13,35%, nos mesmos 368 jogos. Hipótese de disponibilidade 48h;
> não é teste PIT atestado. Estudo encerrado sem retune; multicasas não avaliado.

> Implementação posterior: [preços entre casas e candidato xG](price_strength_2026-09-07/RESULTADO.md),
> com CLI offline `scan/study/demo`, 141 testes aprovados e demonstração sintética.
> [Guia de uso](price_strength_2026-09-07/GUIA.md). Nenhum backtest real, coleta,
> promoção ou alteração de coorte; lucro realizável continua não demonstrado.

> Pesquisa posterior: [modelos e mecanismos de lucro](model_research_2026-09-07/PESQUISA.md).
> Fontes primárias e código público examinados, sem reprodução dos backtests ou
> alteração de candidatos. Pistas para investigação: preço entre casas e xG/GAP.
> Preservar estudos encerrados; nenhuma vantagem econômica nova foi demonstrada.

> Atualização posterior nesta mesma data: [contratos do runtime](runtime_contracts_2026-09-07/RESULTADO.md)
> corrigidos, com 119 testes Python e 46 .NET direcionados aprovados. Redis/Compose
> continua pendente. Leia o primeiro checkpoint do HANDOFF e a reprodução desta
> etapa; o material abaixo preserva o encerramento anterior e seus números.

Este diretório preserva o contexto necessário para continuar o projeto mesmo
sem o histórico da conversa. O pedido final do operador foi salvar tudo no Git,
conferir o prompt contra a sessão e permitir a exclusão do chat. Nenhuma conversa
foi excluída e nenhum push foi solicitado nesta etapa.

## Começar uma nova sessão

Use o repositório operacional:

`C:\Users\Superleo13\projetos\brasileirao-predictor`

Mensagem inicial sugerida:

> Leia e execute `C:\Users\Superleo13\projetos\brasileirao-predictor\docs\continuation\PROMPT_MELHORIA_LUCRO.md`.

Leia o [prompt atual](PROMPT_MELHORIA_LUCRO.md), este guia, o primeiro checkpoint
do [HANDOFF](../../HANDOFF.md) e o [resultado final](review_2026-09-07/RESULTADO.md).
Checkpoints antigos continuam como histórico; não são uma fila de ordens atual.
O antigo `docs/PROMPT_PROXIMA_SESSAO.md` agora aponta para este material.
O arquivo inicial `PROMPT_VALIDACAO_BRASILEIRAO.md` não foi encontrado no caminho
Downloads informado. Não presumir que seu texto tenha sido recuperado: o pedido,
as decisões executadas e suas evidências foram reconstruídos nesta documentação.

## Onde estão os arquivos

| Conteúdo | Local persistente |
| --- | --- |
| Código operacional, testes, contratos, decisões e este guia | Repositório acima, branch `main` |
| Prompt e relatórios agregados da revisão | `docs/continuation/` neste repositório |
| Fontes auxiliares e planos congelados da pesquisa | `docs/continuation/repro_2026-09-07/` |
| Entregas completas, insumos locais, previsões e recibos | `C:\Users\Superleo13\projetos\brasileirao-predictor-sessoes\2026-09-07\` |
| Banco e operação correntes, independentes do chat | `data/` no repositório operacional; não versionados |

O arquivo `BACKUP_MANIFEST.json` na pasta persistente enumera os caminhos, tamanhos
e SHA-256 de 477 arquivos copiados (332.995.520 bytes). Cada cópia foi comparada
com a origem. [backup_receipt.json](backup_receipt.json) registra o hash desse
manifesto. Caches, ambientes, builds e clones descartáveis foram excluídos;
nenhum original foi removido. Essa cópia preserva os dados da sessão e o snapshot
antigo que ela continha; não é um novo backup consistente do banco de produção.
Os arquivos privados foram copiados como bytes, sem avaliar suas coortes.

O Git contém fontes, planos e resumos; os dados locais de provedores, bancos,
ledgers e credenciais continuam fora do Git. Isso preserva a regra existente em
`.gitignore`. Não usar `git add -f` para publicar esses materiais. A cópia local
persistente não é um backup remoto nem protege contra perda deste computador.

### Referências históricas e reprodução

Documentos e fontes congelados podem citar a origem antiga:

`C:\Users\Superleo13\Documents\Codex\2026-09-07\le\`

Para localizar arquivos, substitua somente esse prefixo por:

`C:\Users\Superleo13\projetos\brasileirao-predictor-sessoes\2026-09-07\`

Os sufixos `outputs/...` e `work/...` foram mantidos. O inventário
[versioned_artifacts.json](versioned_artifacts.json) relaciona as cópias públicas
às origens e seus hashes. As fontes foram copiadas sem editar caminhos internos:
isso preserva os hashes científicos. Elas são um arquivo de reprodução, não um
novo runner pronto para executar de qualquer diretório. Antes de reproduzir,
leia os scripts e crie um wrapper separado que aceite os caminhos persistentes;
registre a adaptação e compare previsões/decisões com os resultados congelados.
Não execute em lote os scripts arquivados: alguns fazem aquisição ou configuram
agendas. Para reproduzir estudos concluídos, reutilize os insumos já salvos.

Os clones em `work/brasileirao-predictor`, `work/patch-verification` e
`work/resume-patch-check` e o worktree `work/final_project_review/repo` eram
descartáveis. Não são a produção. O snapshot de validação partiu de
`7b5f8339730134e1df18e28c026752f1d913f183` com overlay das alterações desta sessão;
o commit de encerramento contém essas alterações. Não promover a main mais nova
vista no clone de auditoria por engano.

## O que a sessão estabeleceu

O usuário pediu revisão, execução e avaliação honesta da possibilidade de lucro;
depois pediu um novo prompt para continuar a melhoria. Há autorização para
diagnóstico, implementação reversível e novos estudos separados. Não houve
autorização para apostar dinheiro, comprar dados, ativar capital ou enviar ordens.
As decisões novas não devem reescrever retroativamente protocolos congelados.

O desenho executado usa treino 2021–2024, calibração 2025, primeiro turno de 2026
como teste exploratório e segundo turno inteiro (rodadas 20–38, 190 jogos) como
universo de simulação. Todos os componentes, inclusive Elo, ficaram congelados
após o treino. Atualizar o Elo por 2025 seria uma nova hipótese, e não uma correção
do replay já executado. 2025 e os resultados disponíveis de 2026 já foram vistos:
não chamá-los de holdout intocado em uma nova busca. Turnos oficiais também se
sobrepõem no calendário devido a adiamentos; impor relógios de disponibilidade
ao construir qualquer avaliação cronológica nova.

No corte `2026-09-07T22:43:02Z`, com buffer de 48 horas, havia 58 jogos avaliáveis
no segundo turno e 132 pendentes/indisponíveis. O resultado principal foi:

| Medida | Valor |
| --- | --- |
| Apostas simuladas / acertos / erros | 9 / 4 / 5 |
| Saldo bruto / custo / saldo líquido | −1,05 u / 0,18 u / **−1,23 u** |
| ROI líquido / drawdown máximo | −13,6667% / 3,06 u |
| Cenário ilustrativo de R$ 50 por unidade | −R$ 61,50 |
| Comparador raw, segundo turno | 46 apostas, −19,495 u |
| Principal, primeiro turno | 46 apostas, −14,511 u |

O calibrado 1X2/OU2.5 coincide com a referência de mercado porque o peso aprendido
do modelo foi zero. BTTS calibrado teve Brier e log loss piores que a referência
nos dois turnos. Odds retrospectivas agregadas não demonstram preços executáveis
antes do jogo. Não extrapolar 58 jogos para o turno inteiro ou apresentar esse
resultado como lucro realizado. O antigo resultado de +5 u usava outra regra e
outra amostra; não é o resultado deste novo replay.

Também foram encerradas a reanálise de 12 políticas históricas e a extensão de
51 jogos para descoberta de preços. Nenhuma demonstrou vantagem econômica robusta.
A extensão piorou o MSE em 1,475% frente ao baseline. As análises e as tentativas
negativas estão no backup, em `outputs/REANALISE` e `outputs/EXTENSAO_51`, com suas
fontes em `work/selection_reanalysis` e `work/price_extension_51`. Não repetir a
busca até encontrar um saldo positivo e depois omitir as tentativas anteriores.

## Validação e pendências

Foram corrigidos o escopo do parser de gols OU, o encerramento da árvore de
processos no timeout, a exposição de apiKey em falhas de transporte do EXP001,
os caminhos legados do manifesto e a classificação estática exata de H14 no CI.
A correção anterior do estado mais recente no cutoff do EXP001 também permanece.
Não foram inventadas correções retroativas de preços sem o payload original.

A suíte final passou com 1.082 testes Python; mais 103 testes de pesquisa passaram.
Lint, formatação, Pyright, wheel e build .NET passaram; 18 testes .NET sem Redis
passaram. Cobertura combinada de linhas/branches foi 50,59%, acima do gate 45%,
na execução instrumentada anterior aos quatro testes adicionais do CI. Os 14
arquivos científicos protegidos permaneceram com os mesmos hashes.

**Pendente:** Docker/Redis indisponível. Um teste Python Redis e 13 testes .NET
WorkerRuntime não foram executados, e Compose E2E completo não foi validado.
[VALIDAR_REDIS_ISOLADO.ps1](review_2026-09-07/VALIDAR_REDIS_ISOLADO.ps1) foi conferido
sintaticamente, mas depende de Docker disponível e adaptação dos caminhos de
snapshot. Esse script cobre as integrações Redis; não cobre todo o Compose E2E.

Os testes usaram worktree isolado, banco vazio, ausência de `.env` e credenciais,
bloqueio de rede Python externa e de escritas no repositório operacional. Recriar
essa contenção antes de testes amplos; não rodar a suíte contra o banco vivo.
Os recibos e hashes em [estado_final.json](review_2026-09-07/estado_final.json)
atestam as versões executadas. Documentação de retomada adicionada depois não
representa nova execução desses testes. A reexecução científica reproduziu 760
previsões/decisões, 13.680 decisões históricas e 3.214 relações aritméticas da
extensão. O fingerprint estável é
`b10e06065423c9331121eac460def5da3ff5f2b788edddf581128aba5e77548f`;
o hash antigo de execução incluía duração de otimização e pode variar.

Sete tarefas Windows estão ativas e executam o wrapper no repositório operacional,
sem depender da pasta deste chat. H14/H15 seguem coleta passiva e A1 continua
REHEARSAL_ONLY. Heartbeat com código zero não significa vantagem ou coleta
científica concluída. Não abrir resultados de H14/H15/H9/A1, liquidar coortes,
renovar atestados automaticamente, mudar protocolos ou ativar tarefas desabilitadas
para investigar lucro. Nenhuma frequência foi alterada nesta etapa de preservação.

## Conclusão a transportar

O projeto teve melhorias verificadas de implementação; **lucro e vantagem econômica
continuam não demonstrados**. A próxima sessão deve procurar causas e implementar
poucas hipóteses justificadas, com critérios congelados antes da avaliação e
comparação contra mercado/climatologia. Escolher apostas por probabilidade alta
não basta: preço, calibração, custo, disponibilidade temporal e estabilidade
precisam sustentar a decisão. A resposta final pode continuar sendo negativa;
o objetivo é melhorar e medir, nunca fabricar evidência de lucro.
