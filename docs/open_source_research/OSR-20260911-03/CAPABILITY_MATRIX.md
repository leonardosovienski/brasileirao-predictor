# Matriz consolidada por capacidade

As notas/rubricas e o ranking de OSR-01 foram preservados no registro. A ação mudou somente onde há novo consumidor ou dependência esclarecida; não se recalculou score para favorecer o código recém-escrito. UNKNOWN não virou zero.

| ID | Capacidade | Ação | Estado atual | Score herdado |
|---|---|---|---|---|
| K01 | Massa de cauda e suporte adaptativo | IMPROVE | INTEGRATED_RESEARCH_ONLY | {"VALUE": 90.0, "COST_RISK": 12.0, "PRIORITY": 89.4, "interval": [79.4, 93.3], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K02 | Admissibilidade temporal e identidade com testes adversariais | IMPROVE | INTEGRATED_RESEARCH_ONLY | {"VALUE": 86.0, "COST_RISK": 32.0, "PRIORITY": 80.6, "interval": [65.6, 88.25], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K03 | Adapter estrito e diferencial de retirada de margem | KEEP | INTEGRATED_RESEARCH_ONLY | {"VALUE": 85.0, "COST_RISK": 15.0, "PRIORITY": 85.0, "interval": [75.0, 91.45], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K04 | Scoring, empate, calibração e convenções | AUGMENT | INTEGRATED_RESEARCH_ONLY | {"VALUE": 85.0, "COST_RISK": 19.0, "PRIORITY": 83.8, "interval": [73.8, 90.25], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K05 | Pagamentos, caixa e exposição por partida | KEEP | CANDIDATE | {"VALUE": 79.0, "COST_RISK": 29.0, "PRIORITY": 76.6, "interval": [61.6, 87.78], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K06 | Força dinâmica, pooling e controles de gols | RESEARCH | DEFER | {"VALUE": 65.0, "COST_RISK": 58.0, "PRIORITY": 58.1, "interval": [38.1, 78.1], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K07 | Contexto, elenco e qualidade de chances anteriores | AUGMENT | DEFER | {"VALUE": 68.0, "COST_RISK": 60.0, "PRIORITY": 59.6, "interval": [39.6, 78.2], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K08 | Matriz de fontes e recibos por campo/mercado | AUGMENT | BLOCKED_DATA | {"VALUE": 85.0, "COST_RISK": 46.0, "PRIORITY": 75.7, "interval": [55.7, 88.7], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K09 | Eventos e tracking: coordenadas, xT/VAEP e pressão | RESEARCH | DEFER | {"VALUE": 69.0, "COST_RISK": 66.0, "PRIORITY": 58.5, "interval": [39.4, 78.5], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K10 | Diagnósticos e registro de experimentos | IMPROVE | INTEGRATED_RESEARCH_ONLY | {"VALUE": 60.0, "COST_RISK": 18.0, "PRIORITY": 66.6, "interval": [51.6, 79.42], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K11 | Challengers tabulares e modelos complexos | RESEARCH | DEFER | {"VALUE": 44.0, "COST_RISK": 64.0, "PRIORITY": 41.6, "interval": [21.6, 61.6], "meaning": "estimativa editorial de utilidade; intervalo de sensibilidade, não IC estatístico"} |
| K12 | Ganho esportivo incremental além do preço | RESEARCH | BLOCKED_PERMISSION | null |

## Cobertura das frentes obrigatórias

| Frente | IDs | Referências | Comparação | Escopo da evidência |
|---|---|---|---|---|
| Dados/ingestão | K08 | R004/R021/R022/R051/R052 | Providers e mapa PUB presentes; clocks/versões não comprovados para nova coorte. | Documentação atual focal + mapa herdado; sem API. |
| Robustez da ingestão | K08/K10 | R004 | Cache/retry externo não substitui persistência imutável própria; manter esta. | Fonte/testes soccerdata inspecionados; writer nativo exercitado. |
| Identidade/modelo de dados | K02 | R006/R048 | Contratos próprios ricos; agrupamento 1X2 completado no consumidor. | Teste atual T1; kloppy/Pandera herdados, sem reexecução. |
| Contexto pré-jogo | K07 | R024/R029/R034/R038/R058 | Descanso, viagem, superfície e técnico já declarados; dados PIT faltam. | contextual.py 1–60 atual; restante herdado. DEFER novos dados. |
| Qualidade de desempenho | K07/K09 | R005/R009/R016/R029/R059 | xG e features existem parcialmente; eventos/vídeos têm finalidade diferente. | Survey herdado + produto público atual; sem amostra brasileira admitida. |
| Ratings/força | K06 | R002/R003/R023/R032 | Elo/NB existentes; parâmetro estrangeiro não transfere evidência. | Chamador/fit inspecionado; sem treinamento. |
| Pipeline de features | K07/K10 | R004/R048/R049 | Declarações PIT e writers existentes favorecem completar interfaces. | Não criar feature store; contracts/contextual e writer inspecionados. |
| Modelos probabilísticos | K01/K06/K11 | R001/R002/R003/R041–R046 | NB/DC preservado; otimização mantém distribuição. | T3 atual; comparação preditiva não executada. |
| Incerteza/avaliação | K04 | R014/R040/R050 | Convenções e painel pareado explícitos; calibração real não medida. | T1/T2 atuais; restantes referências herdadas. |
| Mercados/preços | K01/K03 | R001/R010/R011 | De-vig estrito aproveitado; condicionamento requer seu próprio limite. | T1/T3 atuais; sem preço aceito. |
| Elegibilidade/filtros/ranking | K02/K03 | R048/R059 | Recusas por regra/partida, política fixa e completo 1X2. | T1/T2; ranking de aposta não necessário ou autorizado. |
| Simulação/caixa/risco | K05 | R012/R013 | Pagamentos back/caixa adequados no domínio previamente testado. | Ensaios 01 inspecionados, não rerodados. Lay/fills não certificados. |
| Interfaces de pesquisa | K10 | R004/R049 | Interface write_artifacts preservada; consumidor estreito funcional. | T2 atual; não substitui outros pipelines. |
| Gestão de experimentos | K10 | R049 | Comparação com mesma política/universo e hashes. | T2 atual; MLflow C2 focal, sem execução externa. |
| Observabilidade/análise | K10 | R007/R049/R059 | Relatório por fixture, exclusões e mudanças; ligação à evidência. | use.py executado; sem atribuição causal automática. |
| Fluxo do pesquisador | K10 | R004/R049/R059 | Um comando repetível cria runs, compara e demonstra cauda. | 4.71s nesta execução completa; tempo manual anterior não medido. |

C3/C4 atuais pertencem aos alvos executados nesta rodada. Níveis anteriores continuam históricos. Todos os marcos atuais são de engenharia LOCAL; não há E6-H/E6-P ou replicação econômica. Códigos que usam SciPy compartilham backend numérico; independência de bibliotecas não implica independência de dados/autores. NO_VERIFIED_ADVANTAGE para superioridade preditiva ou econômica geral.
