# DECISION_RECORD — análise exploratória Pinnacle após diagnóstico de cobertura

- **ACTION:** realizar uma análise secundária de previsão de preço só Pinnacle, usando os mesmos 30 IDs, cutoffs, preços já adquiridos, split20/10 e purge temporal do experimento anterior; três previsores já especificados, sem feature Bet365.
- **WHY_NOW:** o painel primário exigindo duas casas ficou com4treino/3teste e permanece INSUFFICIENT_DATA. A cobertura Pinnacle tem13treino/9teste. Nenhum modelo B foi ajustado nem comparado antes desta decisão; apenas cobertura e movimento agregado dos preços foram examinados.
- **ALTERNATIVES_CONSIDERED:** afrouxar validade de preços Bet365, substituir jogos, comprar dados ou declarar a questão de previsão de uma única casa bloqueada pela cobertura de outra. Mantemos a análise anterior e abrimos uma ramificação exploratória explicitamente adaptativa.
- **EVIDENCE_TO_BE_REVEALED:** erros de previsão dos preços Pinnacle em9eventos de teste históricos, separados cronologicamente de13eventos de treino; nenhum placar ou resultado de partida.
- **HYPOTHESIS_FAMILY:** DISCOVERY-B-PIN-20260907, mesma família B; não é confirmação independente nem reinício da contagem de busca.
- **MARKET_TYPE:** 1X2 pré-jogo.
- **SEARCH_HISTORY:** inclui o protocolo B anterior insuficiente e toda a busca legada. A mudança de painel foi motivada por cobertura observada e será declarada em toda interpretação.
- **CONFIG_HASH:** SHA-256 de pinnacle_only_plan.json: `cae4db67c9c71916be52192415564554c2f5d9b2d13163c19259bea1f2201057`, registrado antes de calcular métricas.
- **DATASET_HASH:** seleção30 SHA-256 `447a8ccd2e3cb895de23c4bbc68f27c9b95407ce47db250018f48536121a45db`; hashes das22timelines no manifesto de aquisição; hash do relatório-fonte registrado na saída.
- **PREREQUISITE_GATES:** mesma janelaJan–Jun2026 explicitamente observada/exploratória e separada dascoortes; mesmos parsers/cutoffs testados; min10treino/min5teste; preços válidos PinT6/T1/T10; purge de alvo de treino indisponível na primeira decisão de teste.
- **EXPECTED_INFORMATION_GAIN:** determinar se movimento anterior de Pinnacle melhora o preço futuro em comparação com persistência, sem exigir cobertura de outra casa.
- **STOPPING_RULE:** uma execução; publicar persistência, momentum unitário e ridge comalpha1e-4. Parar após essa comparação, qualquer que seja o resultado. Nenhuma alteração posterior de fórmula/amostra, nenhuma requisição adicional, nenhuma promoção científica ou de capital.
