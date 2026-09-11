# Releitura e decisão sobre a entrega — PUB-20260910

Foram relidas todas as 134 mensagens visíveis recuperadas do registro desta tarefa até o checkpoint inicial da publicação, incluindo os pedidos do usuário, as respostas e os informes de execução. O recibo identifica quantidade, corte temporal e hash. A interface de consulta da tarefa devolvia sete turnos sem itens; o registro local exato supriu essa limitação. Ferramentas, raciocínio interno, instruções de sistema e blocos técnicos da interface não fazem parte do histórico visível arquivado.

Também foram relidos integralmente o prompt consolidado e o mandato original. Ambos estão em `archive/instructions`. A cobertura semântica anterior de 399 arquivos permitidos e a limitação de 59 arquivos protegidos foram confrontadas com os inventários e recibos RES. Esta publicação não transforma a revisão anterior em afirmação de ausência universal de bugs nem declara leitura empírica de coortes proibidas.

| Decisão reavaliada | Decisão atual e motivo | Evidência / consequência |
| --- | --- | --- |
| Correções temporais, identidade, revisões, preços, caixa, importação e liquidação diagnóstica | Manter. Os casos de falha e regressão são materiais; remover as correções reintroduziria uso antecipado de informação ou divergência de registro. | Suítes RES, contratos e novo runner portátil. |
| Controles de admissão e gates científicos | Manter. Número de linhas não equivale a eventos independentes; lucro hipotético não comprova execução. | RES/RCA, testes de dependência e rejeição de dados incompletos. |
| Feed comercial e entradas de modelo | Manter contratos explícitos e demonstração separada. Não inventar endpoint, Elo, posições, aceite ou capital. | Testes completos .NET e ensaios sintéticos. |
| Busca econômica BE | Preservar protocolo, negativos e cenário favorável hipotético; não repetir busca para obter saldo desejado. | Resultado BE congelado, custos/falhas de preenchimento e resultado negativo do modelo fixo. |
| Afirmação de que tudo estava pronto ou salvo no GitHub | Corrigir. `ec493c8` estava somente no checkout e em backups; remoto main ainda era `ac22c56`. | Publicação explícita, comparação de HEAD/tree e clone/pull novos com recibos. |
| Reprodução dependente de scripts absolutos no work local | Melhorar. Preservar os roteiros originais e acrescentar runner portátil com escopo revisado. | `tools/publication_validation`, probes reais de I/O e instalação da cadeia fixada no Linux. |
| Executar indiscriminadamente a CI global | Não executar sob o mandato atual. A descoberta global inclui avaliadores protegidos e leitura de registries reais. | Workflow sintético separado; `ci.yml` e seus pisos permanecem. A integração main registra `[skip ci]`; isso não é CI global aprovada. |
| Atualizar todos os Markdown históricos como se fossem estado corrente | Corrigir a navegação, preservando fotografias datadas e seus hashes. | Guias correntes apontam para PUB; índice completo classifica arquivos atuais e históricos. |
| Copiar todos os dados para GitHub público | Preservar o contrato de publicação já existente. Dados privados, coortes e raws com restrição de redistribuição permanecem locais. | Inventário de recuperação e backups; clone Git recupera código/documentos/evidências publicáveis, não toda a máquina. |
| Apagar a conversa antes de guardar sua continuidade | Guardar primeiro o conteúdo visível, mandatos, registros, roteiros e próximos passos. | `archive/chat`, `archive/local-helpers`, `PROXIMO_PROMPT.md` e recibo de recuperação. Nenhuma tarefa foi apagada. |

Os erros de roteiro e tentativas malsucedidas anteriores continuam preservados. Os recibos do pacote RES distinguem instalação com dependências reutilizadas de instalação independente; a nova validação Linux instala a cadeia de `uv.lock` do zero no runner. As proteções de operação, capital e coortes permanecem específicas, mesmo diante dos pedidos gerais para corrigir tudo.

A organização local já separava código, trabalho, dados preservados, instruções, entregas, backups e auditoria. Mantê-la evita quebrar caminhos de coletas e recibos existentes. A atualização consiste em índices e guias correntes; não move bancos, históricos ou tarefas ativas.
