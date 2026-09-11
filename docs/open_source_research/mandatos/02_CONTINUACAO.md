Continue a iniciativa do Brasileirão Predictor a partir de OSR-20260911-01.

Esta rodada deve transformar os achados anteriores em melhorias verificáveis de pesquisa e esclarecer, concretamente, o caminho para uma avaliação preditiva admissível. Não reinicie o levantamento global, não refaça o prompt mestre inteiro e não trate a quantidade de referências, testes ou documentos como resultado principal.

O mandato original e suas proteções continuam válidos. As prioridades abaixo orientam esta continuação, sem converter conclusões sintéticas em evidência preditiva ou econômica.

## 1. Objetivo e autorização desta rodada

Autorizo implementar protótipos, adapters, diagnósticos e testes em área isolada de pesquisa, além de executar benchmarks e experimentos mínimos que passem pelos gates aplicáveis.

Essa autorização não permite alterar o runtime operacional, instalar dependências globais, modificar locks compartilhados, substituir componentes de produção ou integrar permanentemente uma solução. Alterações propostas para código operacional devem permanecer como patch revisável não aplicado, salvo autorização específica posterior.

Não faça commit, push ou merge. Não opere apostas, movimente capital, autentique contas para operar, contrate serviços, consuma quotas reservadas ou altere serviços, agendamentos e automações.

Preserve H14/H15/H9/A1, a linhagem BE e quaisquer outras famílias protegidas identificadas nos protocolos vigentes. Não abra resultados, execute avaliadores ou procure desfechos substitutos para contornar restrições. Não execute pytest global, CI global ou descoberta automática de testes.

Uma hipótese bloqueada continua bloqueada enquanto sua causa não for efetivamente resolvida. Isso não deve impedir trabalhos independentes e já autorizados.

## 2. Retome a evidência existente, sem presumir sua confirmação

Leia os artefatos de docs/open_source_research/OSR-20260911-01/, incluindo o registro estruturado, protocolos, resultados e limitações do harness.

Confirme o estado atual do repositório, as alterações locais, as instruções aplicáveis e a relação com a baseline anterior. Não faça reset, stash ou limpeza para obter um estado conveniente.

Diferencie resultados anteriormente relatados, artefatos inspecionados agora e comportamentos efetivamente reproduzidos nesta rodada. Não recertifique toda a pesquisa apenas por reler o relatório.

Revise as limitações de isolamento e timeout documentadas antes de executar código externo. Use somente o ambiente e os controles realmente disponíveis; registre suas garantias e limitações. Se uma execução não puder ser feita com segurança, bloqueie essa execução, não toda a iniciativa.

Preserve a rodada anterior. Abra um novo RUN_ID conforme a convenção do projeto, referenciando a linhagem e registrando os deltas, sem duplicar desnecessariamente o survey.

## 3. Prioridade N01: diagnóstico e suporte adaptativo da distribuição de gols

Reproduza primeiro o defeito de cauda descrito em T01, dentro do escopo sintético permitido.

Depois, implemente um candidato isolado que torne explícita a massa omitida e adapte o suporte mediante uma tolerância definida antes da comparação. Não resolva apenas trocando um limite fixo por outro maior.

O protocolo deve fixar:
- domínio de parâmetros e tratamento de entradas inválidas;
- tolerância de massa e de erro nos mercados;
- limite de suporte/recursos e comportamento quando a tolerância não for atingida;
- cenários, métricas e critérios de aprovação, rejeição ou inconclusão.

Compare baseline e candidato com referências analíticas ou numéricas justificadas. Não trate a grade 0..100 como verdade exata sem verificar a própria cauda. Considere explicitamente a correção DC no cálculo e na interpretação da massa.

Verifique positividade, normalização, simetria quando aplicável, inversão de mando e consistência dos mercados derivados relevantes. Registre massa antes da renormalização, diferenças de probabilidades, suporte utilizado e custo computacional.

Entregue o código de pesquisa, os testes, os resultados e uma decisão sobre candidatura à integração. A conclusão permitida é sobre correção numérica no domínio testado, não sobre melhora de forecasts reais ou alpha.

## 4. Prioridade N02: adapters estritos, retirada de margem e scoring

Aprofunde K03 e K04 apenas no necessário para produzir contratos matemáticos verificáveis.

Construa ou complete uma camada de validação para entradas, saídas e falhas dos métodos de retirada de margem. Cubra entradas não finitas, odds fora do contrato, probabilidades negativas, somas inválidas e falhas de convergência.

Defina explicitamente o tratamento dos diferentes regimes de margem. Compare implementações somente sob convenções compatíveis. Uma falha externa não deve ser convertida silenciosamente em probabilidade válida nem em prova de superioridade geral do código local.

Para scoring, fixe ordem das classes 1X2, convenção e escala do Brier, definição de log loss e tratamento de probabilidades extremas. Use casos analíticos e testes diferenciais adequados.

Separe verificação da fórmula, implementação do diagnóstico de calibração e calibração empiricamente observada. Testar corretamente uma métrica não demonstra que o modelo está calibrado.

Prefira adapters estreitos e dependências de pesquisa isoladas. Não faça substituição ampla de bibliotecas.

## 5. Prioridade N03: testes adversariais e mutation tests de admissibilidade temporal

Produza fixtures sintéticas válidas e inválidas para os contratos efetivamente usados no projeto.

Inclua casos de publicação ou recebimento posterior ao cutoff, revisão retrospectiva, kickoff remarcado, partidas simultâneas, inversão de mando, IDs conflitantes, duplicatas e timestamps ausentes ou inconsistentes.

Diferencie teste adversarial de mutation test: além de fornecer registros inválidos, introduza mutantes controlados que removam ou invertam verificações relevantes e confira se os testes detectam a perda da proteção.

Registre qual regra cada caso exercita, comportamento esperado, resultado observado e limitações. Ausência de timestamp não deve virar known_at inventado.

O resultado deve mostrar quais violações foram detectadas, quais escaparam e quais propriedades continuam sem cobertura. Esses testes verificam contratos e implementação; não certificam a autenticidade histórica de fontes reais.

## 6. Frente de dados: transforme a barreira genérica em um diagnóstico acionável

Em paralelo, aprofunde as fontes finalistas do survey que possam habilitar a próxima comparação. Faça descoberta complementar apenas quando uma lacuna material não tiver alternativa já catalogada.

Priorize dados utilizáveis pelo sistema existente: resultados/calendário, contexto, desempenho histórico e odds contemporâneas ao cutoff. Não duplique features de descanso/contexto já implementadas antes de verificar sua linhagem.

Para cada fonte relevante, documente:
competição e temporada; campos; identidade das partidas; cobertura efetivamente verificada; versão histórica; relógios observados; revisões; acesso; custos/quotas; licença e condições de uso.

Separe cobertura anunciada de cobertura inspecionada. Quando permitido, examine uma amostra mínima fora do perímetro protegido, com origem e versão registradas. Não consulte resultados protegidos para provar cobertura.

Diferencie uso descritivo, replay histórico condicionado e uso temporalmente admissível. Campos desconhecidos permanecem UNKNOWN.

Complete a inspeção de licenças, manutenção, issues, releases e testes das referências finalistas quando isso puder mudar uma decisão de adoção ou validade. Não faça um sweep indiscriminado apenas para aumentar números.

Para cada bloqueio material, informe exatamente o campo, evidência ou autorização ausente e qual ação permitida poderia resolvê-lo. “Precisamos de mais dados” não é entrega suficiente.

N04, coordenadas/xT toy, permanece uma opção habilitadora de menor prioridade nesta rodada. Execute somente se resolver uma questão concreta de contrato ou transferência; não deixe um novo benchmark toy substituir o trabalho de admissibilidade dos dados.

## 7. N05: separar avaliação preditiva de avaliação econômica

Reavalie o gate de N05 usando apenas contratos e metadados cuja consulta seja permitida. Não considere o experimento liberado apenas porque esta é uma nova rodada ou recebeu outro identificador.

Separe duas perguntas:

A. O componente esportivo melhora probabilidades em relação ao market-only contemporâneo?

B. Essa informação permite resultado econômico líquido sob preços, custos, caixa e condições de execução defensáveis?

A pergunta A exige dados, odds, cutoffs, desenho experimental e autorizações adequados. Não exige, por si só, demonstração de aceitação pessoal de apostas.

A pergunta B exige controles econômicos adicionais. Não trate uma resposta favorável a A como resposta a B.

Prepare um protocolo mínimo para comparar model-only, market-only e composição, com informação e cutoffs comparáveis, métodos de retirada de margem explícitos e orçamento de ajuste fixado. Use log loss como candidata a métrica principal, justificando sua escolha; registre Brier, empate e calibração como diagnósticos pertinentes.

Defina antes da execução a unidade amostral, partições, tratamento da dependência, comparação pareada, incerteza e critérios de decisão. Nenhum ajuste pode ser escolhido pelo resultado do teste.

A execução preditiva mínima fica autorizada somente se a coorte for admissível, as permissões aplicáveis estiverem satisfeitas e a revisão de linhagem não identificar reabertura indevida de estudos protegidos ou encerrados. Esta mensagem não substitui permissões específicas exigidas por esses protocolos.

Se o gate não passar, entregue protocolo, contrato mínimo de dados e bloqueios exatos, sem fitting ou consulta de resultados para “ver se vale a pena”. Não fabrique preços, clocks ou uma coorte aparentemente independente para contornar o bloqueio.

## 8. Entrega e decisão final

Use o registro estruturado como fonte das tabelas. Preserve os IDs existentes e atualize prioridades somente quando houver nova evidência ou mudança explícita de dependência.

A entrega deve mostrar, para cada frente:
baseline; mudança testada; referência; resultado; limitação; artefatos; decisão e próximo gate.

Mantenha separados:
ENGINEERING_STATUS
DATA_ADMISSIBILITY
PREDICTIVE_EVIDENCE
ECONOMIC_EVIDENCE

Inclua caminhos reais dos arquivos, comandos executados, versões, entradas, saídas e testes delimitados. Diferencie código entregue, teste executado, protocolo preparado e trabalho bloqueado.

Feche com uma decisão concreta:
o que conservar; o que corrigir em pesquisa; o que merece revisão para integração; quais dados são utilizáveis para qual finalidade; e se N05 está efetivamente elegível.

Não reescreva o relatório inteiro para parecer uma nova descoberta. Não conclua que o sistema prevê melhor porque testes sintéticos passaram, nem que a pesquisa fracassou porque a avaliação econômica segue bloqueada.

Avance sem pedir confirmação para atividades já autorizadas. Quando surgir uma restrição real, pare apenas a ação afetada e continue as demais. Entregue o que foi efetivamente realizado nesta sessão, sem prometer trabalho futuro.