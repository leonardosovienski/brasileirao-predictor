# RI-20260909 — protocolo da pergunta econômica e orçamento

Registrado antes de calcular novo desempenho. Base ac22c56c3318623e07a722f34d44dc6cd877ea37. Históricos PF/DC/ER e estudos de 2025/Jan–Jun 2026 já foram vistos; reprodução é conferência, nunca nova validação independente.

## Perguntas consideradas

1. Principal: os dados recebidos e os validadores atuais sustentam uma comparação causal, independente e economicamente interpretável de oferta Bet365 com referência Pinnacle, ou ainda permitem falsos positivos de identidade/estado/contabilidade?
   - Mecanismo: discrepância entre casas distintas, oferta excluída da referência proporcional. Requisito anterior a ajustar modelos: saber se os preços comparados descrevem o evento, estado e instante pretendidos.
   - Dados: universo congelado 177 timelines Jan–Jun/2026; CSV público exclusivamente 2025; catálogos e três capturas DC já recebidos; contratos oficiais públicos. Nenhum desfecho de 2026.
   - Incerteza decisiva: admissão correta e recuperação possível de clocks/condições de execução. Teste mínimo: integridade/semântica dos arquivos, adversariais de admissão e conta independente do caminho simulado. Risco: confundir disponibilidade histórica com timestamp de alteração, fonte regional com genérica, backtest condicional com execução.
2. Candidata que não fica ativa: novo modelo xG/calibrador para substituir a referência. Precisa de features PIT, preços e execução; não remove as dependências acima e não justifica nova busca de variantes nesta rodada. Conferir implementação/modelos existentes por engenharia e causalidade, sem ajustar por novo desempenho.

## Método congelado

- Histórico: mesmos 177 fixtures Jan–Jun/2026, Pinnacle e bet365 genérica (regionalidade não comprovada), 1X2 FT, linha nula, corte kickoff−60 minutos. Último estado antes do corte, sem ressuscitar suspensão. A idade da alteração será diagnóstico separado; não prova idade de observação nem torna preço executável.
- 2025: universo completo de 380 jogos, sem excluir jogos por preço ausente. Reproduzir somente a conta DC já conhecida com as escolhas congeladas, verificando fonte e protocolo. Não produzir novo candidato ou otimizar filtros. Closing não possui instante decisório demonstrado.
- Piloto: três capturas de um único fixture; uma unidade independente. Conferir bytes/recibos, identidade do catálogo, flags de pais e filhos, clocks disponíveis. Não usar labels/picks de 2026. Corrigir validações contraditórias sem trocar fixture, horário, casa ou regra da captura futura.
- Referência proporcional Pinnacle com S>1, oferta fora da referência; mesma política anterior q*odd−1−0,02, maior EV líquido em (0;0,15], empate lexical, uma seleção por jogo, somente como cenário. Custos de sensibilidade 0/1/2/3/5% apenas se necessários a explicar decisão, sem seleção do melhor saldo.
- Apostas históricas simuladas: stake 1u, banca 100u, reserva diária conjunta, débito de stake e custo na decisão; devolução inclui principal, lucro subtrai stake e custo. Labels só 2025, resultados ausentes/conflitantes ficam pendentes com principal preso. Mercados suportados no replay: 1X2 vitória/derrota; não declarar void/asiáticos/lay implementados.
- Comparador: abstenção, mantendo universo completo e custos fixos desconhecidos. Separar picks condicionais, observações admissíveis e execução comprovada. Não atribuir zero aos custos pessoais, capacidade, moeda, aceite, slippage, imposto, infraestrutura ou manutenção desconhecidos.
- Conclusão econômica: novo lucro executável não mensurável sem admissão, capacidade e custos. Somente avançar para protocolo de validação futura se os dados justificarem; uma captura não valida rentabilidade. Evidência negativa vale apenas no universo e nas hipóteses definidos.

## Aquisição, isolamento e parada

Reutilizar arquivos íntegros. Até 12 GETs públicos diretos de documentação/contratos ou alternativas de dados relevantes, preservando raw e recibos; sem chamadas autenticadas de odds, consumo de quota reservada, compra ou conta. Downloads de dependências oficiais e consultas públicas de Git/CI são separados da quota de dados e documentados. Nenhuma captura nova fora do protocolo DC. Consulta pública não autoriza contornar bloqueios; uma tentativa por URL nesta rodada, salvo reparo comprovado de transporte.

Orçamento da investigação econômica: até 90 minutos de análise/execução específica após este registro; a revisão e correções técnicas necessárias têm escopo próprio, sem encerrar tarefas independentes úteis por bloqueio do preço. Parar o experimento quando a premissa for refutada no escopo, a evidência permitir decisão, o orçamento se esgotar ou restar dependência externa sem alternativa autorizada. Sem ampliar variantes para fabricar resultado favorável.

Ensaios em ambiente novo e diretórios novos, sem credenciais/rede/bancos operacionais. SQLite exclusivamente sintético em pasta RI quando necessário aos testes. Dependências compartilhadas da coleta protegida não serão alteradas; bugs nessas áreas serão isolados ou registrados com limite de resolução imposto pelo mandato.
