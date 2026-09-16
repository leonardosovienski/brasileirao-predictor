# MISSÃO

Use a instalação real do CAIN para **estudar, testar, comparar e gerar hipóteses sobre o Brasileirão**, produzindo uma rodada científica auditável e executável.

O objetivo desta rodada não é apenas documentar o sistema. É chegar, sempre que os dados e protocolos permitirem, a:

**conhecimento → recuperação pelo CAIN → raciocínio → hipótese → protocolo → experimento → resultado → conclusão permitida**

Trabalhe diretamente em:

* CAIN: `C:\CAIN\projeto`
* Domínio Brasileirão: `C:\BRASILEIRAO\brasileirao-predictor`
* Materiais históricos: `C:\Users\leona\Documents\Codex\2026-09-15\lea\outputs`

Leia primeiro as instruções locais e respeite-as quando forem mais específicas que este prompt.

---

# 1. REGRA FUNDAMENTAL: USE O CAIN REAL

Toda resposta, análise ou proposta atribuída ao CAIN deve ter sido efetivamente produzida pela instalação identificada do CAIN.

Para cada interação relevante com o CAIN registre, quando tecnicamente disponível:

* comando, API ou mecanismo utilizado;
* versão/commit do CAIN;
* modelo utilizado;
* configuração do modelo;
* parâmetros relevantes;
* coleção consultada;
* consulta enviada;
* documentos ou chunks recuperados;
* identificadores das fontes;
* saída original do CAIN;
* erros ou warnings;
* análise posterior feita pelo agente executor.

Mantenha explicitamente separadas:

### SAÍDA DO CAIN

Conteúdo efetivamente produzido pelo sistema.

### ANÁLISE DO EXECUTOR

Avaliação, crítica ou interpretação realizada pelo agente que está conduzindo esta tarefa.

Nunca escreva que:

> “o CAIN concluiu...”

se essa conclusão tiver sido produzida apenas pelo agente executor.

Se o CAIN não conseguir executar determinada etapa, registre a limitação em vez de simular sua resposta.

---

# 2. PRINCÍPIO EPISTÊMICO

Durante toda a execução mantenha separadas estas categorias:

1. O que existe no filesystem.
2. O que foi formalmente admitido no CAIN.
3. O que o CAIN consegue efetivamente recuperar.
4. O que o CAIN raciocina a partir do conteúdo recuperado.
5. O que o executor conclui ao auditar a resposta do CAIN.
6. O que os experimentos permitem concluir cientificamente.

Nunca trate essas categorias como equivalentes.

Em particular:

* arquivo em disco ≠ conhecimento admitido;
* conhecimento admitido ≠ conhecimento recuperável;
* recuperação ≠ compreensão;
* resposta coerente ≠ resposta correta;
* raciocínio correto ≠ validação científica;
* teste de software ≠ teste de hipótese;
* reconstrução retrospectiva ≠ previsão original;
* associação estatística ≠ causalidade.

---

# 3. ESCOPO DESTA RODADA

Esta execução deve privilegiar progresso experimental.

A ordem de prioridade é:

1. confirmar que o CAIN funciona;
2. confirmar o conhecimento relevante disponível;
3. reconstruir as hipóteses necessárias;
4. testar a compreensão do CAIN;
5. executar pelo menos um experimento existente elegível;
6. gerar novas hipóteses com o CAIN;
7. executar o primeiro teste exploratório de uma proposta nova, se houver uma elegível;
8. somente depois aprofundar benchmarking ou auditorias secundárias.

Não transforme a tarefa em auditoria ilimitada.

---

# 4. ORÇAMENTO DA RODADA

Antes de iniciar análises extensas, registre um orçamento operacional.

Defina limites explícitos para:

* chamadas ao LLM;
* experimentos;
* tuning;
* pesquisa externa;
* volume de documentos revisados;
* recursos computacionais.

Se o projeto já definir limites, use-os.

Caso contrário, adote limites conservadores e registre-os antes da execução.

Quando o orçamento estiver próximo do limite, priorize:

1. experimento local elegível;
2. preservação de evidências;
3. handoff reproduzível;
4. auditorias adicionais;
5. pesquisa externa.

Pesquisa externa nunca deve impedir o primeiro experimento local viável.

Não use serviços pagos sem autorização explícita.

---

# 5. AUTONOMIA

Você está autorizado a:

* ler código, documentos, dados e histórico Git;
* executar comandos;
* executar testes;
* corrigir defeitos necessários à execução;
* criar testes de regressão;
* executar análises exploratórias;
* executar simulações;
* executar experimentos autorizados;
* preparar/admitir documentos pelo fluxo normal do CAIN;
* gerar artefatos de auditoria;
* pesquisar projetos externos quando houver acesso.

Não pare apenas em um plano.

Não peça confirmação para operações normais, reversíveis e claramente autorizadas.

---

# 6. PRESERVAÇÃO

Não:

* apague evidências históricas;
* sobrescreva registros canônicos;
* descarte modificações existentes;
* execute `git reset --hard`;
* execute limpeza Git destrutiva;
* modifique previsões antigas;
* invente resultados;
* invente probabilidades;
* invente timestamps;
* invente modelos;
* invente documentos;
* omita resultados negativos;
* publique código;
* faça `git push`;
* faça apostas;
* movimente dinheiro.

Antes de modificar código ou conhecimento, identifique o estado anterior e mantenha recuperação/rastreabilidade.

---

# 7. ISOLAMENTO DO DOMÍNIO

As admissões de conhecimento realizadas nesta execução devem ficar restritas à coleção, namespace ou mecanismo equivalente correspondente ao **Brasileirão**.

Não misture documentos de outros domínios na coleção do Brasileirão.

Não apague, altere ou prejudique outras coleções já existentes no CAIN.

Referências metodológicas externas são permitidas, desde que identificadas como:

`REFERÊNCIA METODOLÓGICA EXTERNA`

e não tratadas como evidência histórica do Brasileirão.

---

# 8. INSPEÇÃO INICIAL

Primeiro determine o estado real dos projetos.

Leia instruções locais relevantes, incluindo quando existirem:

* `AGENTS.md`
* `README*`
* `CONTRIBUTING*`
* documentação de arquitetura;
* contratos;
* schemas;
* documentação dos dados;
* documentação experimental;
* instruções de testes.

Registre:

* timestamp;
* diretório;
* branch;
* HEAD;
* `git status`;
* alterações preexistentes;
* runtime;
* dependências;
* estado da instalação;
* serviços necessários;
* testes básicos;
* mecanismo disponível para executar o CAIN.

Não atribua a esta rodada alterações que já existiam.

---

# 9. FONTES PRIORITÁRIAS

Analise prioritariamente:

* `CAIN_O_QUE_TEM.md`
* `CAIN_O_QUE_FALTA.md`
* `CAIN_ENTREGA_RECONSTRUCAO.md`
* `CAIN_RECIBO_ADMISSAO.json`
* `DADOS_HISTORICOS_E_PROTOCOLO_V2.md`
* `PROTOCOLO_SUCESSOR_V2.json`
* `BUSCA_COMMITS_GITHUB.md`

Siga referências adicionais apenas quando necessárias para:

* resolver contradições;
* verificar uma hipótese;
* identificar provenance;
* executar um experimento;
* validar uma afirmação importante.

Não releia indiscriminadamente todo o repositório.

---

# 10. REUTILIZE AUDITORIAS EXISTENTES

Antes de repetir uma auditoria, verifique se há resultado anterior:

* verificável;
* rastreável;
* compatível com o estado atual do repositório.

Se nada relevante mudou desde uma auditoria válida, reutilize-a.

Atualize apenas:

* elementos modificados;
* evidências novas;
* pontos anteriormente inconclusivos;
* dependências necessárias ao experimento atual.

Não repita buscas registradas em `BUSCA_COMMITS_GITHUB.md` sem pelo menos uma destas condições:

* nova fonte;
* novo commit;
* novo repositório;
* mudança externa verificável;
* nova estratégia com justificativa concreta.

---

# 11. AUDITORIA DO CONHECIMENTO DO CAIN

Determine empiricamente:

* o que foi admitido;
* o que está indexado;
* o que é recuperável;
* o que não é recuperável;
* o que está duplicado;
* o que está contraditório;
* o que existe apenas no filesystem.

Compare com os registros canônicos do projeto.

Para documentos relevantes registre:

* caminho;
* origem;
* versão;
* hash, preferencialmente SHA-256;
* status de admissão;
* ID no CAIN;
* coleção;
* limitações.

Quando material necessário estiver ausente do CAIN mas disponível e autorizado:

1. determine sua origem;
2. calcule hash;
3. registre limites;
4. admita pelo fluxo normal;
5. preserve admissões anteriores;
6. teste recuperação depois da admissão.

O sucesso da ingestão não comprova recuperação.

---

# 12. RETIFICAÇÕES

Quando uma informação histórica estiver errada ou incompleta, não sobrescreva silenciosamente.

Use, quando suportado:

* nova versão;
* retificação;
* supersessão;
* relação explícita entre registros;
* mecanismo equivalente.

Preserve a versão anterior.

---

# 13. INVENTÁRIO DAS HIPÓTESES

Reconstrua as hipóteses relevantes a partir das fontes reais.

Não procure somente IDs conhecidos.

Considere também:

* experimentos;
* relatórios;
* manifests;
* configs;
* código;
* notebooks;
* contratos;
* branches;
* commits;
* resultados;
* referências cruzadas.

Diferencie rigorosamente:

* hipótese;
* versão da hipótese;
* experimento;
* versão do experimento;
* braço;
* modelo;
* configuração;
* previsão;
* resultado;
* alegação.

Nunca una identidades apenas pela semelhança do nome.

Para cada hipótese registre:

* ID canônico;
* aliases;
* versão;
* pergunta;
* mecanismo;
* previsão falsificável;
* população;
* período;
* dados;
* disponibilidade temporal;
* variáveis;
* modelos;
* baseline;
* métricas;
* protocolo;
* experimentos;
* resultados;
* fontes;
* limitações;
* contradições;
* dependências;
* próximo teste potencialmente decisivo.

Se não puder determinar algo:

`NÃO DETERMINADO`

Não preencha lacunas por inferência silenciosa.

---

# 14. CLASSIFICAÇÃO EM TRÊS EIXOS

Não misture ciclo de vida, maturidade da evidência e conclusão experimental.

Para cada hipótese registre três dimensões independentes.

## A. ESTADO DO CICLO DE VIDA

Exemplos:

* ativa;
* substituída;
* abandonada;
* arquivada;
* candidata;
* não determinado.

## B. MATURIDADE DA EVIDÊNCIA

Exemplos:

* proposta;
* ainda não testada;
* exploratória;
* replicada internamente;
* validação independente disponível;
* bloqueada por dados;
* bloqueada por protocolo.

## C. CONCLUSÃO NO CONTEXTO TESTADO

Exemplos:

* apoiada;
* refutada;
* inconclusiva;
* não aplicável;
* ainda não testada.

Uma hipótese pode, por exemplo, ser simultaneamente:

* `ciclo_de_vida = substituída`
* `maturidade = exploratória`
* `conclusão = inconclusiva`

Não force essas dimensões a uma única categoria.

---

# 15. ESTADO CANÔNICO VS. ANÁLISE ATUAL

Preserve separadamente:

`estado_canonico`

e

`avaliacao_desta_execucao`

Se sua análise divergir do registro histórico, documente a divergência.

Não altere retroativamente o estado histórico apenas porque a análise atual chegou a outra interpretação.

---

# 16. QUALIDADE DA EVIDÊNCIA

Para todo resultado quantitativo relevante, considere quando disponível:

* efeito observado;
* direção;
* magnitude;
* incerteza;
* intervalo;
* tamanho de amostra;
* métrica;
* baseline;
* período;
* população;
* desenho experimental.

Não interprete automaticamente:

`p > α`

como:

“não existe efeito”.

Não interprete ausência de significância como equivalência.

Não transforme:

* resultado in-sample em out-of-sample;
* exploração em validação;
* correlação em causalidade;
* testes de engenharia em evidência científica.

---

# 17. AVALIAÇÃO REAL DO CAIN

Avalie se o CAIN consegue trabalhar com o conhecimento, não apenas repeti-lo.

Use perguntas que exijam:

* recuperação de fontes;
* integração entre documentos;
* comparação entre versões;
* identificação de contradições;
* distinção entre hipótese e experimento;
* reconhecimento de dados ausentes;
* interpretação temporal;
* comparação com baseline;
* reconhecimento de limites científicos;
* explicação de por que determinada conclusão não pode ser feita;
* proposta de teste falsificável.

Registre a resposta original do CAIN.

---

# 18. DESENVOLVIMENTO VS. AVALIAÇÃO RESERVADA

Divida os casos usados para avaliar o CAIN em:

## CONJUNTO DE DESENVOLVIMENTO

Pode ser utilizado para:

* diagnosticar erros;
* ajustar prompts;
* corrigir retrieval;
* corrigir código;
* criar testes de regressão.

## CONJUNTO RESERVADO

Não pode ser utilizado para:

* ajustar prompts;
* alterar código motivado pela resposta do caso;
* escolher documentos;
* configurar retrieval;
* fazer tuning.

Crie ou selecione os casos reservados antes de observar suas respostas.

Registre toda exposição.

Se um caso reservado for utilizado para desenvolvimento por qualquer motivo, marque:

`EXPOSTO`

e transfira-o para desenvolvimento.

Ele não poderá mais ser apresentado como avaliação reservada.

Não reutilize perguntas conhecidas como demonstração de generalização.

---

# 19. QUATRO CAMADAS DA AVALIAÇÃO

Avalie separadamente:

### 1. Recuperação

Encontrou a fonte correta?

### 2. Fidelidade

Representou corretamente o conteúdo da fonte?

### 3. Raciocínio

A conclusão decorre das evidências fornecidas?

### 4. Correção científica

A interpretação respeita:

* temporalidade;
* desenho experimental;
* incerteza;
* baseline;
* confundimento;
* generalização;
* causalidade?

Uma resposta pode passar em recuperação e falhar em raciocínio.

Registre isso explicitamente.

---

# 20. NÃO ACEITE FALSA COMPREENSÃO

Não considere como evidência de compreensão:

* resposta hardcoded;
* lookup específico da pergunta;
* tabela determinística construída para o teste;
* string matching trivial;
* template contendo previamente a conclusão.

Sempre que possível, use:

* paráfrases;
* casos negativos;
* evidências conflitantes;
* perguntas novas;
* casos reservados.

---

# 21. CORREÇÃO DE FALHAS

Se encontrar falha corrigível:

1. reproduza o erro;
2. preserve a resposta incorreta;
3. crie teste de regressão;
4. aplique a menor correção razoável;
5. repita o teste;
6. execute testes relacionados.

Depois, avalie separadamente casos reservados ainda não expostos.

Regressão corrigida demonstra correção daquele caso conhecido.

Não a apresente como evidência suficiente de generalização.

---

# 22. SELECIONAR UM EXPERIMENTO EXISTENTE

Após a auditoria mínima necessária, procure imediatamente uma hipótese existente testável.

Prefira uma cujo teste:

* use dados existentes;
* não consuma coorte protegida;
* tenha provenance suficiente;
* permita controle temporal;
* tenha baseline;
* tenha métrica;
* possa ser reproduzida;
* caiba no orçamento.

Não espere terminar toda a pesquisa externa para começar.

---

# 23. PRÉ-REGISTRO OPERACIONAL

Antes de observar o resultado do novo experimento, registre:

* ID;
* pergunta;
* hipótese;
* previsão;
* mecanismo;
* população;
* período;
* dados;
* provenance;
* disponibilidade temporal;
* baseline;
* métrica primária;
* métricas secundárias;
* critério de decisão;
* exploração;
* treino;
* validação;
* teste;
* controle temporal;
* múltiplas comparações;
* seed;
* orçamento;
* condição de parada.

Mudanças feitas depois de observar resultados devem ser marcadas:

`PÓS-HOC`

---

# 24. VAZAMENTO TEMPORAL

Para cada variável pergunte:

> Essa informação estaria realmente disponível no instante em que a previsão teria sido produzida?

Verifique especialmente:

* classificações atualizadas posteriormente;
* estatísticas contendo partidas futuras;
* dados corrigidos retrospectivamente;
* preprocessamento ajustado no dataset inteiro;
* features selecionadas usando teste;
* agregações além do cutoff;
* odds capturadas depois do momento previsto;
* qualquer target leakage.

Documente a auditoria.

---

# 25. COORTES PROTEGIDAS

Descubra nos protocolos e recibos quais coortes são protegidas.

Uma coorte protegida não pode ser usada para:

* exploração;
* seleção de modelo;
* escolha de features;
* tuning;
* escolha de hipótese;
* análise repetida.

A avaliação única de uma coorte protegida depende de protocolo e autorização específicos.

Se houver dúvida, não consuma a coorte.

Continue usando material exploratório.

---

# 26. EXECUÇÃO DO EXPERIMENTO

Execute o experimento elegível.

Preserve:

* comandos;
* config;
* código;
* versão;
* hashes;
* dados;
* seeds;
* stdout;
* stderr;
* exit code;
* métricas;
* gráficos;
* falhas;
* runs negativos;
* tuning realizado.

Não selecione apenas o melhor resultado.

Dados previamente examinados continuam exploratórios.

---

# 27. CONDIÇÃO DE IMPOSSIBILIDADE

Se nenhuma hipótese existente puder ser testada legitimamente nesta rodada:

não:

* relaxe os critérios;
* consuma coorte protegida;
* fabrique dados;
* trate exploração contaminada como validação.

Em vez disso produza:

`BLOQUEIO_DE_EXPERIMENTO`

contendo:

* hipóteses avaliadas;
* por que cada uma foi considerada inelegível;
* evidências do bloqueio;
* requisito mínimo para desbloqueá-la;
* menor próxima ação possível.

A rodada pode ser encerrada legitimamente sem experimento se a impossibilidade estiver demonstrada.

---

# 28. NOVAS HIPÓTESES PRODUZIDAS PELO CAIN

Depois de compreender as hipóteses existentes, peça ao **CAIN real** para gerar até cinco:

* novas hipóteses;
* refinamentos;
* testes discriminantes.

Preserve o prompt enviado e a resposta original.

Para cada proposta exija:

* origem da ideia;
* evidências recuperadas;
* relação com hipóteses existentes;
* mecanismo;
* previsão falsificável;
* população;
* dados;
* disponibilidade real;
* disponibilidade temporal;
* baseline;
* teste mínimo;
* confundidores;
* risco de vazamento;
* múltiplas comparações;
* custo;
* resultado que a refutaria.

Depois o executor deve auditar essas propostas.

Não trate automaticamente a proposta do CAIN como boa ou nova.

---

# 29. DETECÇÃO DE DUPLICIDADE

Compare propostas novas com:

* hipóteses;
* versões;
* experimentos;
* braços;
* aliases;
* propostas abandonadas;
* resultados negativos anteriores.

Semelhança de nome não prova duplicação.

Nome diferente não prova novidade.

Registre a justificativa.

---

# 30. PRIMEIRO TESTE DE UMA NOVA HIPÓTESE

Se existir uma proposta:

* realmente distinta;
* falsificável;
* com dados existentes;
* sem coorte protegida;
* dentro do orçamento;

selecione uma e preregistre seu primeiro teste.

Execute o teste como:

`EXPLORATÓRIO`

Não promova a hipótese automaticamente.

Resultado positivo gera necessidade de validação independente.

Resultado negativo também deve ser preservado.

---

# 31. SE NÃO HOUVER NOVA HIPÓTESE TESTÁVEL

Use a mesma regra de impossibilidade.

Documente:

* propostas avaliadas;
* bloqueios;
* dados necessários;
* menor próximo passo.

Não crie um experimento artificial apenas para cumprir a entrega.

---

# 32. PESQUISA EXTERNA

A pesquisa externa é secundária ao primeiro teste local.

Quando houver acesso à internet, procure apenas o suficiente para encontrar:

### Previsão esportiva

* football prediction;
* probabilistic forecasting;
* rating systems;
* xG;
* calibration;
* temporal validation;
* backtesting.

### Sistemas científicos

* scientific agents;
* hypothesis generation;
* evidence graphs;
* experiment tracking;
* provenance;
* RAG científico;
* falsification workflows.

Para cada fonte útil registre:

* projeto;
* URL;
* commit/tag quando relevante;
* data;
* método útil;
* diferença em relação ao CAIN;
* aplicação possível;
* limitações.

Não trate resultados externos como validação das hipóteses do Brasileirão.

Não copie código sem avaliar licença.

Interrompa a pesquisa quando deixar de produzir novidade operacional relevante.

---

# 33. LIMITES HISTÓRICOS CONHECIDOS

Verifique nos recibos atuais o estado destes pontos históricos:

* duas probabilidades H15 reconstruídas retrospectivamente;
* quatro probabilidades H15 não recuperadas;
* seis probabilidades H14 não recuperadas;
* dois relatórios originais ausentes;
* lacunas de disponibilidade temporal;
* lacunas de identidade de modelos.

Esses itens são pontos de partida para verificação, não autorização para completar valores ausentes.

Se nada novo for encontrado, preserve as limitações.

Se houver nova evidência, registre:

* fonte;
* hash;
* provenance;
* relação com o registro anterior;
* motivo pelo qual altera o inventário.

---

# 34. PROTOCOLO SUCESSOR

Não presuma que um protocolo está ativo simplesmente porque existe documentação sobre ele.

Diferencie:

* especificado;
* implementado;
* registrado;
* ativado;
* coleta iniciada;
* avaliação autorizada.

A coorte protegida só pode ser usada quando as condições exigidas pelo próprio protocolo estiverem demonstradas.

---

# 35. RASTREABILIDADE

Toda afirmação importante deve apontar para evidência.

Prefira:

* `arquivo:linha`;
* JSON Pointer;
* ID de recibo;
* ID de experimento;
* hash;
* commit;
* ID/chunk recuperado pelo CAIN;
* URL + versão + data para fontes externas.

Use explicitamente:

`EVIDÊNCIA INSUFICIENTE`

quando necessário.

Identifique claramente:

`FATO DOCUMENTADO`

`SAÍDA DO CAIN`

`INFERÊNCIA DO CAIN`

`ANÁLISE DO EXECUTOR`

`RESULTADO EXPERIMENTAL`

---

# 36. ENTREGAS

Produza artefatos equivalentes a:

* `00_EXECUTION_LOG.md`
* `01_ENVIRONMENT.md`
* `02_KNOWLEDGE_AUDIT.md`
* `03_HYPOTHESES_INVENTORY.md`
* `03_HYPOTHESES_INVENTORY.json`
* `04_EVIDENCE_MATRIX.md`
* `04_EVIDENCE_MATRIX.json`
* `05_CAIN_DEV_EVAL.md`
* `06_CAIN_HELDOUT_EVAL.md`
* `07_EXISTING_HYPOTHESIS_EXPERIMENT.md`
* `08_EXTERNAL_RESEARCH.md`
* `09_CAIN_NEW_HYPOTHESES.md`
* `10_NEW_HYPOTHESIS_EXPLORATION.md`
* `11_HANDOFF.md`
* manifesto de hashes.

Adapte os nomes se o projeto já possuir convenção equivalente.

Não duplique desnecessariamente estruturas canônicas existentes.

---

# 37. MATRIZ DE HIPÓTESES

A matriz final deve permitir visualizar, para cada hipótese:

| Campo               | Conteúdo                           |
| ------------------- | ---------------------------------- |
| ID                  | identidade canônica                |
| versão              | versão analisada                   |
| ciclo de vida       | ativa/substituída/etc.             |
| maturidade          | proposta/exploratória/etc.         |
| conclusão           | apoiada/refutada/inconclusiva/etc. |
| estado canônico     | registro histórico                 |
| avaliação atual     | interpretação desta execução       |
| evidência principal | fonte                              |
| baseline            | comparação                         |
| efeito              | magnitude/direção                  |
| incerteza           | quando disponível                  |
| validade temporal   | situação                           |
| principal limitação | problema                           |
| próximo teste       | teste discriminante                |

Não use células vazias para informação desconhecida.

Use `NÃO DETERMINADO`.

---

# 38. HANDOFF

O handoff deve permitir que outro agente continue sem repetir esta rodada.

Inclua:

### Estado inicial

Git, ambiente, instalação, serviços e dados.

### Evidências consultadas

Com caminhos e versões.

### CAIN utilizado

Versão, modelo, configuração e mecanismo de execução.

### Conhecimento

O que estava admitido, foi admitido e foi recuperado.

### Alterações

Arquivos criados/modificados e justificativa.

### Testes de software

Sucessos, falhas e regressões.

### Avaliação do CAIN

Desenvolvimento e reservado separados.

### Experimentos científicos

Protocolos, comandos, dados e resultados.

### Resultados negativos

Inclua explicitamente.

### Bloqueios

Com evidências.

### Próxima ação mínima

O menor passo concreto capaz de avançar cada bloqueio importante.

---

# 39. RESUMO FINAL OBRIGATÓRIO

Termine separando:

## DOCUMENTADO

O que já constava das evidências.

## IMPLEMENTADO

Código ou infraestrutura alterados nesta execução.

## TESTADO

O que realmente foi executado.

## ADMITIDO

Novo conhecimento formalmente admitido no CAIN.

## RECUPERADO PELO CAIN

Conhecimento cuja recuperação foi observada empiricamente.

## PRODUZIDO PELO CAIN

Raciocínios ou propostas realmente gerados pelo CAIN.

## ANALISADO PELO EXECUTOR

Críticas ou interpretações feitas fora do CAIN.

## CIENTIFICAMENTE VALIDADO

Somente o que o desenho experimental sustenta.

## EXPLORATÓRIO

Resultados que ainda não possuem validação independente.

## BLOQUEADO

O que não pôde ser testado e por quê.

## NÃO DETERMINADO

Informação para a qual não existe evidência suficiente.

---

# 40. CRITÉRIO DE CONCLUSÃO DA RODADA

Não considere a tarefa concluída apenas porque:

* os documentos foram lidos;
* o inventário foi criado;
* o CAIN respondeu alguma coisa;
* testes de software passaram;
* houve resultado estatisticamente interessante;
* pesquisa externa foi realizada.

Uma rodada normal deve tentar alcançar:

**CAIN real → evidência recuperada → raciocínio registrado → avaliação → experimento elegível → resultado auditável**

e, quando possível:

**evidências → CAIN real → nova hipótese → auditoria da hipótese → primeiro teste exploratório**

Se experimentos forem legitimamente impossíveis, a execução termina com prova do bloqueio e a menor ação necessária para desbloqueá-los.

Não enfraqueça critérios científicos para fazer a execução parecer completa.

---

# 41. REGRA DE PROGRESSO

Não permaneça indefinidamente na auditoria.

Assim que houver evidência suficiente para identificar:

* uma hipótese;
* dados elegíveis;
* baseline;
* protocolo seguro;

avance para o primeiro experimento.

Auditorias adicionais podem continuar depois.

A pergunta operacional durante toda a execução deve ser:

> Qual é a menor próxima ação que aumenta de forma verificável nosso conhecimento sobre uma hipótese sem contaminar uma avaliação futura?

Execute essa ação.

# AJUSTES FINAIS DE ESCOPO E AVALIAÇÃO

Inclua todas as hipóteses conhecidas no inventário, com cobertura explícita. Aprofunde primeiro as necessárias ao experimento escolhido; registre as demais como ainda não analisadas nesta rodada.

Antes da avaliação reservada, fixe a versão do código, modelo, prompts, recuperação e critérios de pontuação. Mantenha perguntas e gabaritos fora da coleção consultada pelo CAIN. Não ajuste o sistema entre casos dessa avaliação. Registre se quem ajustou o sistema teve acesso prévio aos casos; não alegue avaliação cega quando isso não ocorreu.

Bloqueios são campos próprios: bloqueios, motivo e requisito_para_desbloqueio. Não use bloqueada por dados/protocolo como nível de maturidade; uma hipótese pode ser exploratória e estar bloqueada simultaneamente.

Comece agora.