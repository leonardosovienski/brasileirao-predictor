# DECISION_RECORD — extensão histórica de preço com regra congelada

- ACTION: coletar no máximo 51 históricos Pinnacle e avaliar o coeficiente já congelado, sem novos ajustes.
- WHY_NOW: o usuário perguntou se era necessário esperar o próximo fim de semana; há jogos históricos adicionais admissíveis, dentro da autorização vigente para executar a pesquisa.
- ALTERNATIVES_CONSIDERED: esperar partidas futuras; alterar regras; repetir as falhas anteriores. Esta extensão usa todos os 51 IDs admissíveis pelos metadados, sem reposição.
- EVIDENCE_TO_BE_REVEALED: preços anteriores ao jogo, previsão de preço T−10min a partir de T−1h/T−6h, erro contra persistência e prêmio implícito secundário. Nenhum placar ou lucro.
- HYPOTHESIS_FAMILY: DISCOVERY-B-PIN-EXT51-20260907, extensão exploratória da mesma família B.
- MARKET_TYPE: 1X2 pré-jogo, Pinnacle.
- SEARCH_HISTORY: resultado anterior já conhecido (3,35% em nove testes, frágil); 51 jogos distintos intercalados no mesmo período. Não é réplica futura nem confirmação cega. O estudo anterior permanece encerrado.
- CONFIG_HASH: SHA-256 plan.json `c02666646fdbe39dee9ab0b614a2077d8d3dca073a2b9ff5c88af4475990d9fd`.
- DATASET_HASH: SHA-256 selection.json `5da96f38349b1b7535cf11109e84071dc1ae0b351b0cf986c4d3b5822c7cca6a`; históricos terão hashes por resposta.
- PREREQUISITE_GATES: decisão T−1h estritamente após último alvo de treino (2026-04-19T21:20:00+00:00); excluir 30 IDs anteriores; Jan–Jun admissível; parsers testados; fonte original por hash; quota com reserva20; nenhum gasto.
- EXPECTED_INFORMATION_GAIN: falsificar ou fortalecer descritivamente o sinal de reversão congelado e verificar se ele chega a selecionar preços acima do prêmio implícito de2%, preservando a diferença entre proxy e lucro real.
- STOPPING_RULE: uma coleta, uma avaliação; máximo51 pedidos únicos sem repetição/substituição, pausas7s após resposta e30s após429, parar após3consecutivos. Sem mudar parâmetros depois dos resultados. Publicar todos os estados, inclusive insuficiência. Não registrar trial nem habilitar capital.
