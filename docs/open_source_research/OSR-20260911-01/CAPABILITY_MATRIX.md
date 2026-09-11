# Matriz de capacidades e ranking — OSR-20260911-01

A unidade é a capacidade, não a biblioteca. Doze capacidades comprimem as alternativas; uma referência pode servir a mais de uma. Ranking de **utilidade estimada da pesquisa**, não ranking de apostas. Gates prevalecem sobre score. Intervalos sobrepostos não justificam precisão da ordenação.

## Ranking mestre

| Ordem editorial | ID | Capacidade | VALUE | COST_RISK | PRIORITY | Sensibilidade | Gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | K01 | Massa de cauda e suporte adaptativo | 90.0 | 12.0 | 89.4 | 79.4–93.3 | SYNTHETIC_ELIGIBLE |
| 2 | K03 | Adapter estrito e diferencial de retirada de margem | 85.0 | 15.0 | 85.0 | 75.0–91.5 | SYNTHETIC_ELIGIBLE |
| 3 | K04 | Scoring, empate, calibração e convenções | 85.0 | 19.0 | 83.8 | 73.8–90.2 | SYNTHETIC_ELIGIBLE |
| 4 | K02 | Admissibilidade temporal e identidade com testes adversariais | 86.0 | 32.0 | 80.6 | 65.6–88.2 | SYNTHETIC_ELIGIBLE |
| 5 | K05 | Pagamentos, caixa e exposição por partida | 79.0 | 29.0 | 76.6 | 61.6–87.8 | SYNTHETIC_ELIGIBLE |
| 6 | K08 | Matriz de fontes e recibos por campo/mercado | 85.0 | 46.0 | 75.7 | 55.7–88.7 | METADATA_ELIGIBLE |
| 7 | K10 | Diagnósticos e registro de experimentos | 60.0 | 18.0 | 66.6 | 51.6–79.4 | DOCUMENTATION_ELIGIBLE |
| 8 | K07 | Contexto, elenco e qualidade de chances anteriores | 68.0 | 60.0 | 59.6 | 39.6–78.2 | DATA_CONDITIONAL |
| 9 | K09 | Eventos e tracking: coordenadas, xT/VAEP e pressão | 69.0 | 66.0 | 58.5 | 39.4–78.5 | SYNTHETIC_ONLY_DATA_BLOCKED |
| 10 | K06 | Força dinâmica, pooling e controles de gols | 65.0 | 58.0 | 58.1 | 38.1–78.1 | DATA_CONDITIONAL |
| 11 | K11 | Challengers tabulares e modelos complexos | 44.0 | 64.0 | 41.6 | 21.6–61.6 | DATA_CONDITIONAL |


**K12 permanece UNRANKED.** O perfil econômico exige potencial econômico, transferência e execução que são UNKNOWN; não imputamos zeros nem atribuímos falsa estimativa de lucro. Pode ser pergunta importante e ainda não ser executável.

## Método e rubricas

Scores 0–5: valor 0 sem benefício demonstrável no escopo, 3 benefício material plausível fundamentado, 5 benefício elevado sustentado; custo 0 baixo demonstrado, 3 material, 5 alto. São juízos da rodada, com justificativa por capacidade no registro. Não são efeitos medidos. Evidência externa refere-se ao claim de utilidade do diagnóstico, não ao maior E de um pacote. Casos negativos aumentam a utilidade de detectar erro, não o potencial de sucesso econômico de uma estratégia.

`VALUE_RAW_ENABLER = .30 scientific + .20 validation + .15 external_evidence + .10 architecture + .10 incremental + .10 domain + .05 independent_references`.

`VALUE_RAW_ECONOMIC = .20 economic + .15 scientific + .15 external_evidence + .10 independent_references + .10 Brasileirão_transferability + .10 execution_feasibility + .08 incremental + .07 validation + .05 architecture`.

`COST_RISK_RAW = .25 implementation + .20 methodology + .15 dependency + .15 maintenance + .15 data + .10 operations`.

`VALUE = 20 × VALUE_RAW`; `COST_RISK = 20 × COST_RISK_RAW`; `PRIORITY = .70 × VALUE + .30 × (100 − COST_RISK)`.

Cada dimensão tem estimativa e intervalo truncado em [0,5] no JSON. Para K01/K03/K04 a amplitude é ±0,5; K02/K05/K10 ±0,75; demais ±1. O intervalo de prioridade combina menor valor/maior custo e vice-versa. É análise conservadora de sensibilidade editorial, **não intervalo de confiança estatístico**. Gates e dados desconhecidos não são compensados pelo score.

Sensibilidade adicional a pesos, sem mudar o ranking canônico: participação de VALUE em 60% e 80%, e transferência de cinco pontos de peso entre scientific_value e external_evidence. Não altera autorização, e não testa eficácia dos candidatos.

| Cenário | Cinco primeiros IDs |
| --- | --- |
| mais_custo | K01, K03, K04, K02, K05 |
| mais_valor | K01, K03, K04, K02, K08 |
| mais_evidencia_externa | K01, K03, K04, K02, K05 |
| mais_utilidade_cientifica | K01, K03, K04, K02, K05 |


Opções rápidas sustentadas: K01/K03/K04, pois usam dados sintéticos e dependências pequenas. K06/K07/K09 combinam valor científico plausível com custo maior de dados/método; não são rejeitadas por serem caras, mas a decisão de adoção depende de acesso e ganho incremental. K02/K08 têm dependências científicas que podem justificar executar N03 antes de itens com score nominal maior.

COMPETITOR_PREVALENCE, COMPETITIVE_GAP e DIFFERENTIATION_POTENTIAL permanecem UNKNOWN: não há denominador comparável de competidores auditados. Rubrica futura: prevalência 0 nenhum no universo definido, 3 aproximadamente metade, 5 maioria ampla; gap 0 paridade, 3 capacidade material parcial, 5 diferença crítica comprovada; diferenciação 0 nenhuma, 3 distinta plausível, 5 distinção pertinente demonstrada. Não aplicar sem dados. A classe comparativa é NOT_DIRECTLY_COMPARABLE, e não LEAPFROG por popularidade. Redundância foi eliminada agrupando alternativas (seriam >=4 quando repetem função sem ganho); as capacidades finais têm penalidade 0, sem duplo desconto.

## Comparação factual e mecanismo

| ID / ação | Estado interno | Referências | Claim e mecanismo | Próximo |
| --- | --- | --- | --- | --- |
| K01 / IMPROVE | PARCIAL / C4 | R001, R002 | A distribuição normalizada omite massa mensurável em T01; falta diagnóstico no retorno atual. Adicionar erro de truncamento explícito; custo baixo por usar a mesma família NB/DC. | N01 |
| K02 / VALIDATE | PARCIAL / C2 | R004, R048 | Feature legado corta por data do jogo, enquanto contratos PIT novos têm mais relógios; não confundir caminhos. Mutation tests determinísticos de revisões, ausência de relógio e suspensão, com recibos de exclusão. | N03 |
| K03 / VALIDATE | IMPLEMENTADO / C4 | R001, R010, R011 | T02 concorda no domínio usual e encontra falhas externas nas bordas; manter política local explícita. Conferir finitude, não negatividade, soma, domínio e fallback, sem alegar probabilidades verdadeiras. | N02 |
| K04 / VALIDATE | PARCIAL / C2 | R014, R040, R050 | Brier local soma classes; referência binária usa outro eixo. DM local eleva entradas ao quadrado. Fixar redução, classe, clipping e objetos entregues ao teste; empate exige dados novos para diagnóstico estatístico. | N02 |
| K05 / KEEP | PARCIAL / C4 | R012, R013 | T03 passa para pagamentos atômicos e caixa back; simulador rejeita event_id repetido e não cobre lay/fills. Preservar caminho validado; especificar extensão somente se mercado nominal demandar. | N02 |
| K06 / RESEARCH | EXPERIMENTAL / C1 | R002, R003, R023, R032, R033, R036, R039, R041, R042, R043 | NB/Elo e ajuste dinâmico já existem; trocar família sem dados/controle igual não isola ganho. Comparar baseline simples e atual, treinados só em coorte nova admissível; não portar parâmetros estrangeiros. | N05 |
| K07 / AUGMENT | EXPERIMENTAL / C1 | R024, R029, R034, R038, R058 | Descanso/viagem/técnico e envelopes de escalação já têm código; fatos PIT por jogador não demonstrados. Priorizar calendário/descanso sobre tracking caro; separar contexto, xG observado e expectativa pré-jogo. | N05 |
| K08 / AUGMENT | PARCIAL / C1 | R004, R016, R017, R021, R022, R025, R026, R027, R051, R052, R053, R058 | Histórico de preço e API atual não garantem aceitação, publicação ou ingestão no cutoff. Tabela de elegibilidade por fornecedor/campo antes de coletar; UNKNOWN bloqueia claim dependente. | N03 |
| K09 / RESEARCH | DESCONHECIDO / C0 | R005, R006, R008, R009, R015, R016, R018, R019, R020, R028, R030, R037 | Nenhuma cobertura brasileira admissível foi comprovada. Código externo útil, mas upstream e task não são equivalentes. Um contrato espacial sintético pode eliminar erros antes de comprar/adotar dados; ganho pré-jogo não testado. | N04 |
| K10 / KEEP | PARCIAL / C1 | R007, R031, R049 | Registro em arquivos atende a rodada; novo servidor de tracking ou dashboard não tem necessidade comprovada. Guardar dados, transformações, tentativas e exclusões em manifesto versionado; não criar outro kernel. | N03 |
| K11 / RESEARCH | DESCONHECIDO / C0 | R044, R045, R046, R047, R054, R055, R056, R057 | Não há ganho preditivo comprovado nesta rodada; múltiplos READMEs são alegações. Compressão evita campeonato de algoritmos. Primeiro baseline causal linear ou gols; no máximo um challenger com orçamento igual e tuning dentro do treino. | N05 |
| K12 / RESEARCH | EXPERIMENTAL / C1 | R001, R021, R035, R051 | Código residual existe, mas nenhuma coorte econômica nova admissível foi usada; relação com famílias BE exige revisão. Hipótese: contexto/força acrescenta informação não capturada na odd contemporânea. Persistência e executabilidade UNKNOWN. | N05 |


## Visões por categoria

As tabelas são projeções dos mesmos IDs e scores. Não há cem tarefas ou dez itens artificiais em cada categoria.

### melhorias imediatas

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K01 | Massa de cauda e suporte adaptativo | 89.4 / [79.4, 93.3] | SYNTHETIC_ELIGIBLE |
| K03 | Adapter estrito e diferencial de retirada de margem | 85.0 / [75.0, 91.45] | SYNTHETIC_ELIGIBLE |
| K02 | Admissibilidade temporal e identidade com testes adversariais | 80.6 / [65.6, 88.25] | SYNTHETIC_ELIGIBLE |

### novas análises

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K04 | Scoring, empate, calibração e convenções | 83.8 / [73.8, 90.25] | SYNTHETIC_ELIGIBLE |
| K10 | Diagnósticos e registro de experimentos | 66.6 / [51.6, 79.42] | DOCUMENTATION_ELIGIBLE |
| K07 | Contexto, elenco e qualidade de chances anteriores | 59.6 / [39.6, 78.2] | DATA_CONDITIONAL |
| K09 | Eventos e tracking: coordenadas, xT/VAEP e pressão | 58.5 / [39.4, 78.5] | SYNTHETIC_ONLY_DATA_BLOCKED |
| K06 | Força dinâmica, pooling e controles de gols | 58.1 / [38.1, 78.1] | DATA_CONDITIONAL |

### filtros/ranking

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K03 | Adapter estrito e diferencial de retirada de margem | 85.0 / [75.0, 91.45] | SYNTHETIC_ELIGIBLE |
| K02 | Admissibilidade temporal e identidade com testes adversariais | 80.6 / [65.6, 88.25] | SYNTHETIC_ELIGIBLE |
| K08 | Matriz de fontes e recibos por campo/mercado | 75.7 / [55.7, 88.7] | METADATA_ELIGIBLE |
| K12 | Ganho esportivo incremental além do preço | UNRANKED | BLOCKED_DATA_PROTOCOL |

### fontes/datasets

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K02 | Admissibilidade temporal e identidade com testes adversariais | 80.6 / [65.6, 88.25] | SYNTHETIC_ELIGIBLE |
| K08 | Matriz de fontes e recibos por campo/mercado | 75.7 / [55.7, 88.7] | METADATA_ELIGIBLE |

### ferramentas

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K03 | Adapter estrito e diferencial de retirada de margem | 85.0 / [75.0, 91.45] | SYNTHETIC_ELIGIBLE |
| K04 | Scoring, empate, calibração e convenções | 83.8 / [73.8, 90.25] | SYNTHETIC_ELIGIBLE |
| K10 | Diagnósticos e registro de experimentos | 66.6 / [51.6, 79.42] | DOCUMENTATION_ELIGIBLE |
| K09 | Eventos e tracking: coordenadas, xT/VAEP e pressão | 58.5 / [39.4, 78.5] | SYNTHETIC_ONLY_DATA_BLOCKED |

### famílias de features/estratégias

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K07 | Contexto, elenco e qualidade de chances anteriores | 59.6 / [39.6, 78.2] | DATA_CONDITIONAL |
| K09 | Eventos e tracking: coordenadas, xT/VAEP e pressão | 58.5 / [39.4, 78.5] | SYNTHETIC_ONLY_DATA_BLOCKED |
| K06 | Força dinâmica, pooling e controles de gols | 58.1 / [38.1, 78.1] | DATA_CONDITIONAL |
| K11 | Challengers tabulares e modelos complexos | 41.6 / [21.6, 61.6] | DATA_CONDITIONAL |
| K12 | Ganho esportivo incremental além do preço | UNRANKED | BLOCKED_DATA_PROTOCOL |

### validação

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K01 | Massa de cauda e suporte adaptativo | 89.4 / [79.4, 93.3] | SYNTHETIC_ELIGIBLE |
| K04 | Scoring, empate, calibração e convenções | 83.8 / [73.8, 90.25] | SYNTHETIC_ELIGIBLE |
| K02 | Admissibilidade temporal e identidade com testes adversariais | 80.6 / [65.6, 88.25] | SYNTHETIC_ELIGIBLE |
| K05 | Pagamentos, caixa e exposição por partida | 76.6 / [61.6, 87.78] | SYNTHETIC_ELIGIBLE |

### risco/execução

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K05 | Pagamentos, caixa e exposição por partida | 76.6 / [61.6, 87.78] | SYNTHETIC_ELIGIBLE |

### referências

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K01 | Massa de cauda e suporte adaptativo | 89.4 / [79.4, 93.3] | SYNTHETIC_ELIGIBLE |
| K03 | Adapter estrito e diferencial de retirada de margem | 85.0 / [75.0, 91.45] | SYNTHETIC_ELIGIBLE |
| K06 | Força dinâmica, pooling e controles de gols | 58.1 / [38.1, 78.1] | DATA_CONDITIONAL |
| K11 | Challengers tabulares e modelos complexos | 41.6 / [21.6, 61.6] | DATA_CONDITIONAL |

### composições

| ID | Capacidade | Prioridade / intervalo | Condição |
| --- | --- | --- | --- |
| K05 | Pagamentos, caixa e exposição por partida | 76.6 / [61.6, 87.78] | SYNTHETIC_ELIGIBLE |
| K08 | Matriz de fontes e recibos por campo/mercado | 75.7 / [55.7, 88.7] | METADATA_ELIGIBLE |
| K07 | Contexto, elenco e qualidade de chances anteriores | 59.6 / [39.6, 78.2] | DATA_CONDITIONAL |
| K12 | Ganho esportivo incremental além do preço | UNRANKED | BLOCKED_DATA_PROTOCOL |

## Composições com propósito explícito

1. **K01 + K03 + K04 + K05:** grade com erro explícito → preços coerentes → avaliação com convenção fixa → caixa. Evidência local T01–T03 nas peças; nenhuma validação da composição real. Falha comum: confundir distribuição normalizada com completa e preço teórico com aceito.
2. **K02 + K08 + K07 + K06:** fontes versionadas → contexto anterior admissível → força/gols. Primeiro ablar somente contexto; não mudar fonte, universo e modelo simultaneamente sem contraste de cobertura. Falha comum: transformar data de jogo em data de conhecimento.
3. **K02 + K03 + K04 + K12:** quote no mesmo cutoff → market-only → incremento esportivo. Condicionado a nova coorte e revisão da família BE; nenhum estudo econômico reaberto.
4. **K09 + K10:** padronização espacial → diagnóstico xT/pressão. Habilitador esportivo separado; sem tracking brasileiro não se presume melhoria de previsão pré-jogo.
