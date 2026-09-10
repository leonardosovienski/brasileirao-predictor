# Mapa vigente ARI

O [mapa LGC](../ledger_consistency_2026-09-10/MAPA_SISTEMA.md) e seu mapa CLO referenciado continuam válidos para os demais subsistemas. ARI atualiza o modelo residual experimental, sem implantação.

| Componente | Estado e decisão | Evidência/limite |
| --- | --- | --- |
| MarketResidualModel | Corrigir carregamento, cópia, estado, convergência, intervalo e exportação | 24 regressões antes/depois; aproximação Hessiana não autentica treino nem calibração econômica. |
| MultinomialMarketResidualModel | Corrigir truncamento de labels, pré-processamento transacional, convergência e estado | Classes 0/1/2 mantidas, objetivo e L2 inalterados, gradiente conferido. |
| economic_decision | Consumidor do contrato ResidualPrediction preservado | Testes sintéticos correlatos passam; sempre shadow/capital false. |
| residual_walkforward | Consumidor exploratório, preservado | Dois testes sintéticos passam. Não é replay financeiro: roi é média de retornos por seleção em unidade fixa; stake da decisão não é aplicada como carteira com banca. Dados/IDs/status/revisões precisam de protocolo próprio. |
| residual_gate | Exploração preservada, fora do caminho econômico ativo | Leitura semântica: input admite bool/não finitos; pnl médio chamado ROI depende de stake fixa; DSR fornecido pelo chamador e dependência PSR não resolvida. Não autentica promoção; não executado nesta etapa. |
| calibration_gate | Gate A10 histórico, preservado | Leitura semântica: coerção float/não finitos podem alterar juízo; relatório é declaração, não prova de procedência. Estudo congelado não foi recalculado; não usar como homologação econômica. |

Os scripts históricos que usam esses componentes não foram executados sobre dados reais. Alterar avaliação congelada não é necessário para testar o consumidor puro; erros remanescentes não foram ocultados nem classificados como validados. O registro CPL-P25 mantém a continuação da cobertura global.
