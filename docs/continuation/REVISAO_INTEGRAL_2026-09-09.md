# Mandato complementar — revisão integral e resolução do projeto

## Pedido do usuário

Trabalhe em `C:/BRASILEIRAO/brasileirao-predictor`. Mantenha código, dados, pesquisa, documentação, recibos e entregas do projeto em `C:/BRASILEIRAO`. Trabalhe sozinho, sem coordenar outros agentes, conforme o mandato original.

Execute uma revisão completa do projeto: do que existe, do que ele diz fazer, do que pressupõe ser verdade, da lógica, da matemática, da arquitetura, dos dados disponíveis e ausentes, da implementação e da possibilidade de atingir seu objetivo econômico. Comece conferindo o que já temos, se está correto e se as escolhas continuam justificadas. Depois corrija, obtenha os dados recuperáveis, implemente e teste o que faltar.

Não se limite às pendências da última sessão. Uma lista anterior pode estar incompleta; um componente pode estar errado, ser desnecessário ou depender de uma premissa sem evidência. Confronte também afirmações de assistentes anteriores. Documentação, testes aprovados, hashes e versões declaradas não são, isoladamente, prova de funcionamento ou validade econômica.

Este documento registra o trabalho solicitado para o novo chat. **A revisão integral ainda não foi executada.** O checkpoint abaixo é contexto datado, não aprovação antecipada.

## Leitura inicial e precedência

Leia integralmente `C:/BRASILEIRAO/INSTRUCOES/MANDATO_RECEBIDO_2026-09-09.txt`. Este complemento amplia o reconhecimento para a conferência integral solicitada e muda a próxima sessão de continuação pontual para revisão e resolução. Mantém o objetivo econômico, a integridade da pesquisa e as restrições originais.

Consulte inicialmente estes caminhos do repositório, expandindo a leitura conforme o inventário e as dependências reais:

- `README.md`, instruções `AGENTS.md` aplicáveis e início de `HANDOFF.md`.
- `docs/ESTADO_ATUAL.md`, `docs/continuation/RETOMADA.md`, `docs/DATA_MAP.md` e `docs/INDICE_DOCUMENTACAO.md`.
- `docs/continuation/MANDATO_LUCRO_2026-09-09.md` e contratos relevantes.
- `docs/continuation/execution_readiness_2026-09-09/RESULTADO.md` e `REPRODUZIR.md`.
- `docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md`, `PENDENCIAS.md`, protocolos e resultado.
- `C:/BRASILEIRAO/LEIA_PRIMEIRO.md` e recibos relevantes de `C:/BRASILEIRAO/AUDITORIA`.

Determine HEAD, branch, remotes, worktrees, alterações locais e estado das rotinas antes de editar. Não faça reset para um SHA histórico. Confira os efeitos de comandos desconhecidos antes de executá-los. Separe código registrado, dependências declaradas, ambiente instalado, dados presentes e operação efetivamente ativa.

## 1. Conferir o existente antes de completar lacunas

Faça um inventário rastreável de todos os subsistemas e das afirmações materiais. Revise documentação e implementação com profundidade suficiente para verificar seus contratos, seguindo os caminhos de execução e suas dependências; não se limite a nomes de arquivos, palavras-chave ou contagem de testes.

Crie uma matriz de alegações com: identificador, afirmação, origem/data, evidência necessária, evidência encontrada, contraexemplo ou limitação, estado da verificação, impacto e ação. Classifique como confirmado no escopo, parcialmente confirmado, refutado, não verificado ou bloqueado. Registre contradições entre documentos, código, testes, configurações e comportamento observado. Ausência de evidência não confirma uma alegação.

Cubra ao menos:

- Objetivo, mercados e usuários previstos; o que é promessa, hipótese, demonstração ou capacidade implementada.
- Coleta, normalização, identidade de jogos/equipes, calendário, aliases, armazenamento, proveniência, revisões e disponibilidade temporal.
- Features, atualização de estados, modelos, calibração, referência de mercado, odds, seleção e abstenção.
- Execução simulada, limites, simultaneidade, exposição, liquidação, contabilidade e métricas.
- APIs, contratos entre componentes, persistência, tarefas, configuração, instalação, empacotamento, integração e recuperação após falhas.
- Testes, exclusões de cobertura/tipagem, fixtures sintéticas, CI histórica, verificações locais e demonstração do caminho completo.
- Documentos, reprodução, retomada, cópias, backups e portabilidade dos caminhos.

Explicite o que está ativo, utilizável, experimental, obsoleto, desconectado ou não instalado. Para material protegido, limite a conferência aos metadados e contratos permitidos; registre essa fronteira de cobertura em vez de abrir resultados.

## 2. Rever lógica, matemática e arquitetura

Reconstrua e confira o fluxo: dado admissível → informação conhecida no instante da decisão → modelo ou referência → preço observado → seleção ou abstenção → execução simulada → liquidação → reconciliação financeira. Identifique onde funciona, onde há apenas interface ou mock e onde faltam entradas verificáveis.

Confira fórmulas, unidades, arredondamentos, probabilidades, margem, independência da referência, alinhamento dos universos, vazamento temporal e separação entre desenvolvimento e validação. Normalizar proporcionalmente as mesmas odds da oferta não cria vantagem quando a soma das probabilidades implícitas excede um. Valide esse e outros pressupostos no código efetivo.

Verifique publicação, observação, recebimento, decisão e início real; atrasos, adiamentos, simultaneidade e revisões; estado aprendido dos modelos/calibradores; e se alguma feature usa informação indisponível naquela decisão. Timestamp da última alteração não prova disponibilidade contínua. Hash comprova integridade dos bytes, não aceitação de aposta.

Examine a necessidade de cada componente para responder à pergunta econômica. Reavalie modelos, comparação entre casas, Python/.NET, Redis, Compose, serviços, bancos e dependências por correção, custo, complexidade, observabilidade e reprodução. Pode simplificar, corrigir ou substituir dentro da autorização existente. Não preserve uma escolha só porque existe, nem reescreva sem demonstrar o problema e verificar a alternativa.

Compare alternativas plausíveis quando isso mudar uma decisão relevante. Registre por que manter, corrigir, substituir ou retirar cada parte questionada. Justifique a escolha diante dos requisitos e evidências; não prometa provar a melhor arquitetura entre todas as possíveis.

## 3. Conferir dados e resolver o que falta

Construa um mapa por conjunto, campo e finalidade: fonte/versão, localização, período/universo, quantidade, cobertura, duplicações, ausências, consistência, identidade, granularidade, revisões, acesso e admissibilidade temporal. Distinga arquivo presente, dado legível, dado semanticamente correto e dado suficiente para a conclusão pretendida.

Para cada requisito, indique se o dado existe e foi validado, existe mas é inadequado, está parcial, pode ser recuperado, exige coleta futura, depende de informação externa indisponível ou não é necessário ao caminho escolhido. Mostre denominadores de cobertura e motivos de rejeição. Não trate 177 arquivos ou 380 jogos como prova de completude de todos os dados do projeto.

Priorize lacunas que invalidam a medição ou decisão econômica. Corrija primeiro dados, parsers ou premissas errados já presentes quando necessário à aquisição. Busque fontes primárias e documentação oficial, verifique sua semântica e registre URL, data, resposta, versão e limitações. Faça aquisições públicas autorizadas, preservando originais e recibos, sem repetir lotes íntegros sem motivo.

Confirme plano, custo, quota, limites e reserva antes de APIs limitadas. Não compre serviços, crie contas, contorne restrições ou exponha credenciais. Separe aquisição autorizada com credenciais do processo de pesquisa/auditoria, que recebe apenas artefatos sem segredos.

Não invente preços disponíveis, liquidez, aceitação, limites pessoais, custos, timestamps ou fontes. Não preencha desconhecidos com zero. Para dado irrecuperável, tente alternativas legítimas compatíveis com o requisito, documente as tentativas e delimite a conclusão impedida. Coleta futura não pode ser substituída por reconstrução com conhecimento posterior.

Busque os dados necessários ao caminho justificado; não acumule dados sem finalidade nem exija todos os campos e mercados concebíveis. Se a revisão mudar o caminho, atualize e justifique seus requisitos antes de avaliar desempenho.

## 4. Corrigir, executar e validar

Mantenha um registro único de achados/lacunas com prioridade, causa, dependências, correção, evidência de fechamento e pendência residual. Documentar um problema ou marcá-lo como concluído não equivale a resolvê-lo.

Implemente as correções recuperáveis e necessárias. Para bugs materiais, obtenha reprodução e regressão que falhe antes e passe depois. Faça checks proporcionais, incluindo integração e reprodução do fluxo real quando entradas admissíveis permitirem. Use ambiente, bancos, filas, arquivos e configurações isolados. Não rode a suíte indiscriminadamente se puder disparar avaliações protegidas, gravar no banco operacional ou consumir APIs.

Verifique instalação/build e dependências do caminho escolhido quando necessários à prontidão alegada. Os testes delimitados de uma rodada não aprovam toda a aplicação; CI de outro commit ou máquina não comprova o estado local. Não relaxe checks para obter aprovação. Separe entradas sintéticas, cenários condicionais e evidência real.

Depois de conferir o existente, escolha até três perguntas econômicas relevantes, uma principal e no máximo uma alternativa ativa, conforme o mandato original. Antes de novo desempenho, registre hipótese, universo, instante da decisão, fontes, método, seleção, abstenção, stake, custos, execução, liquidação, comparadores, orçamento e critérios de parada. Dados já explorados não viram validação independente; não ajuste regras retrospectivamente até aparecer lucro.

Reconcilie banca, stakes, capital preso, responsabilidade, retornos incluindo principal, custos e resultado líquido. Trate os contratos de liquidação efetivamente suportados; não declare suporte a void, push, parciais, asiáticos ou lay sem implementação e verificação. Separe margem embutida, comissão, tributos, slippage, recusas, limites e custos de dados/infraestrutura/manutenção, sem dupla contagem.

Mantenha partidas sem preço, rejeições, não concluídas e abstenções no universo. Compare universos compatíveis e decomponha melhora em preço, seleção, exposição e custo. Examine incerteza, dependência entre apostas/snapshots e concentração temporal. Menos prejuízo por menor exposição não demonstra vantagem.

Continue das descobertas para a resolução. Não encerre apenas com plano, lista de problemas, revisão cosmética ou novos testes se houver trabalho necessário e autorizado. Um impedimento de uma frente não impede trabalho independente justificado. Respeite os critérios de parada de cada experimento; não prolongue busca de variantes para fabricar resultado positivo.

## 5. Fronteiras preservadas

Preserve H14/H15/H9/A1 integralmente: observações, resultados, estados, agendas, claims, travas, avaliadores, artefatos e dependências compartilhadas capazes de alterar a coleta. Não leia resultados intermediários, faça joins com desfechos, calcule métricas dessas coortes, liquide resultados, execute/reinicie avaliadores, renove atestados, altere observadores/agendas ou as use como holdout. Consulte somente metadados, contratos e documentação explicitamente permitidos. Novo namespace não autoriza dados protegidos.

Não envie apostas, movimente dinheiro, faça depósitos, autentique casas de apostas, crie contas, contrate serviços ou habilite permissões financeiras. Toda execução financeira permanece simulada. Prontidão técnica não libera capital.

Preserve negativos, variantes rejeitadas, protocolos, resultados e artefatos históricos. Atualize guias atuais e acrescente correções datadas, sem reescrever resultados congelados. Não exponha `.env`, chaves ou dados privados na pesquisa, logs, relatórios ou commits. Não faça force-push, exclusão destrutiva ou reset de trabalho existente.

## 6. Checkpoint datado — conferir novamente

Estado observado em 09/09/2026, antes deste handoff documental: `main`, HEAD `60c95aa6b1b6b87f00da3ac5b59d67f0bf9bb369`, checkout limpo. É a base técnica ER, não necessariamente o HEAD quando o novo chat começar. Recibo anterior: `C:/BRASILEIRAO/AUDITORIA/EXECUTION_READINESS_2026-09-09.json`. Recibo deste handoff: `C:/BRASILEIRAO/AUDITORIA/HANDOFF_REVISAO_INTEGRAL_2026-09-09.json`.

- Migração: 12.423 entradas mais manifesto, com SHA/CRC registrados. Cobre material recebido; não comprova arquivos nunca entregues ou posteriores à captura do computador antigo. Dependências do sistema e o aplicativo Codex não estão contidos na pasta.
- DC: 177 históricos, CSV com 380 jogos de 2025 e três capturas de um único evento. Esses números não demonstram admissão econômica. Zero pares admitidos para execução no checkpoint.
- Closing 2025: cenário condicional de 32 apostas, −9,24u e fonte Pinnacle com aviso de desatualização. Não é validação de lucro executável; não retune filtros após observar o saldo. Históricos explorados não viram holdout novo.
- ER: cinco falhas corrigidas nos helpers de captura/auditoria; 153 testes delimitados, com 15 novos. Não aprova a aplicação completa. Ambiente mínimo Python instalado; .NET/Redis/Compose e aplicação operacional completa não foram validados nesta máquina por essas rodadas.
- `bookmakerIsActive=false` no agregador informa principalmente falta de coleta ativa da casa/jogo; não prova suspensão da aposta na casa. Limite reportado não prova limite pessoal; moeda da conta de API não prova moeda do limite da casa.
- Capacidade, custos reais e validação futura continuam sem fechamento. Condições públicas não substituem informação pessoal de execução ou apuração tributária. Lucro executável não demonstrado.

Existe um acompanhamento na tarefa anterior do Codex `01a08756-2962-7c43-9773-c790cc81329d`, id `completar-dados-do-brasileir-o`, diariamente às 19:57 de São Paulo. Definição ativa do aplicativo: `C:/Users/leona/.codex/automations/completar-dados-do-brasileir-o/automation.toml`. A cópia `C:/BRASILEIRAO/AUDITORIA/automacao_dados_2026-09-09.toml` é documental. Não crie outro acompanhamento por abrir este chat.

Antes de mexer nos helpers ou artefatos de captura, confira relógio atual, configuração ativa, eventual execução concorrente, marcador de tentativa, recibos e hashes. Não altere arquivos enquanto a outra tarefa os usa. Não repita aquisição por troca de chat, nem force execução fora do protocolo. Agendas protegidas continuam intocadas.

A captura independente congelada usa fixture `id1000032566887012`, Pinnacle / `bet365.bet.br`, 1X2 FT. Kickoff observado: 12/09/2026 00:00 UTC. Decisão: 11/09/2026 23:00 UTC (20:00 em São Paulo). Janela de entrada: 22:55 até antes de 22:59:15 UTC; alvo 22:58:30 UTC. Plano gratuito verificado, reserva mínima de 20, no máximo uma chamada de odds, sem retry. Leia protocolo e continuidade; este resumo não substitui seus contratos. Horário decorrido não autoriza mudar o corte.

Helpers ativos: `C:/BRASILEIRAO/work/data-completion-2026-09-09/followup_capture.py` e `audit_followup.py`. Versões testadas ER também no subdiretório `reproducao` da documentação DC. Auditoria em processo separado, sem credenciais. Agendamento depende de computador ligado e aplicativo funcionando; sem garantia de pontualidade. Se a janela passou, verifique o ocorrido e preserve falhas/ausência de captura.

Backups DC e ER são históricos distintos. ER atualizou helpers do backup DC; não restaure versão antiga sobre a corrigida. Confira recibos/hashes antes de restaurar. Não abra bancos recebidos indiscriminadamente: delimite primeiro leituras permitidas sem conteúdo protegido.

## 7. Entregas e significado de pronto

Salve a revisão e seus artefatos em diretórios próprios sob `C:/BRASILEIRAO`, com referências nos guias atuais. Entregue:

1. Inventário real e matriz de alegações, incluindo escopo não verificado e limites da revisão.
2. Mapa de dados existentes, válidos, inadequados e faltantes; fontes consultadas, dados obtidos e lacunas residuais.
3. Avaliação da lógica/arquitetura, alternativas relevantes, decisões e justificativas.
4. Registro de problemas encontrados e resolvidos, evidência antes/depois e correções implementadas.
5. Reprodução, testes e integração proporcionais: ambiente, comandos, resultados e limitações reais.
6. Resultado econômico ou bloqueio demonstrado, nos 14 itens do mandato original, sem confundir hipótese com lucro validado.
7. Documentação atual coerente: README, estado, retomada, mapa, índice e próximo prompt; históricos preservados; caminhos, hashes, diff, commit e backups verificáveis quando aplicável.

Separe **engenharia funcional no escopo testado**, **dados/medição admissíveis** e **evidência econômica suficiente para nova validação**. Nenhuma implica automaticamente as outras. Não diga “tudo pronto” com requisitos críticos pendentes, testes ausentes do caminho alegado ou apenas cenários condicionais.

Para pendência irrecuperável com recursos autorizados, identifique requisito, tentativas, dependência externa e efeito na conclusão. Não invente fechamento nem peça autorização novamente para ações cobertas. Se precisar continuar em outra sessão, deixe checkpoint fiel e lista priorizada, sem apresentar revisão incompleta como encerrada.

Comece verificando o estado real. Confira primeiro o existente e as premissas do caminho escolhido; então resolva o que a evidência mostrar que falta.
