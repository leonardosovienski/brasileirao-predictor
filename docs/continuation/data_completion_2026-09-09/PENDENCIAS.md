# Pendências verificadas — DC-20260909

Atualizado em 09/09/2026. Completude de arquivos não equivale à admissibilidade
econômica. [Resultado](RESULTADO.md), [continuidade](CONTINUIDADE.md) e
[estado atual](../../ESTADO_ATUAL.md). O registro estruturado está em
[evidencias/completude.json](evidencias/completude.json).

| Requisito do mandato | Situação real | Próximo passo ou limite |
| --- | --- | --- |
| Arquivos do universo histórico declarado | **Concluído: 177/177**, hashes válidos | Preservar arquivos, manifesto inicial e reparo de transporte; não repetir download |
| Fonte pública de preços por casa | **Recuperada**: CSV oficial, 380 jogos de 2025, 158 pares numéricos | Referência Pinnacle comprometida conforme aviso da própria fonte; não homologar closing como execução |
| Identidade de casas/mercado/seleção | **Parcial**: Pinnacle, Bet365 e Bet365 Brasil distinguidas; mercado 101 1X2 FT | Catálogo de clones não prova sozinho independência econômica; manter casa ofertante fora da referência |
| Informação disponível no passado | **Ausente para execução**: timelines não demonstram receipt da época nem calendário PIT | Não há reparo retrospectivo que crie uma observação nunca capturada; usar observação prospectiva |
| Par atual ativo | **Não obtido**: oferta Bet365 Brasil inativa nas três capturas | Uma captura definida antes de T−60 em 11/09; rejeitar novamente se inativo |
| Relógios da coleta nova | **Obtidos no piloto**, fora de T−60 | Preservar request/receipt/HTTP Date e revisões na próxima captura; receipt não equivale a publicação da casa |
| Calendário na decisão | **Observado prospectivamente**, fixture congelado | Rejeitar incompatibilidade de kickoff/status na captura; não deslocar corte depois |
| Limite/capacidade da oferta | **Desconhecido**: Bet365 Brasil limit=null; referência com 450 sem moeda provada | Procurar evidência de limite aplicável; não preencher com zero, infinito ou limite de outra casa |
| Aceite, slippage e preenchimento | **Não demonstrados** | Feed não é recibo de aposta; nenhuma autenticação de casa ou execução financeira permitida |
| Custos de dados desta rodada | **Verificados**: cinco chamadas de quota gratuita; nenhuma compra | Conta final 67/250, reserva 20 intacta; reconfirmar antes da única chamada futura |
| Custo econômico total | **Desconhecido**: cenário 2% não é custo real | Regras fiscais, comissão, deterioração, recusa, manutenção e capacidade exigem evidência aplicável |
| Liquidação/contabilidade de cenário | **Implementada e conferida** para 1X2 FT do recorte | 32 seleções condicionais, −9,24u; referência comprometida impede interpretação econômica |
| Validação independente futura | **Ainda não existe** | Registrar protocolo e tamanho/unidade de amostra antes de medir desempenho; um fixture não basta |
| Engenharia proporcional | **138 testes aprovados**, Ruff e tipagem dos três módulos; conferência Fraction | Repetir somente diante de alteração/falha; aplicação operacional completa não foi instalada |
| Arquivos/documentação local | **Consolidados em C:/BRASILEIRAO** para o material recebido e produzido | Não atesta dados nunca enviados ou posteriores à captura de migração |

O histórico antigo indisponível causalmente não será chamado de resolvido por
ter sido baixado hoje. Um preço atual ativo também não completa automaticamente
capacidade, custos ou validação. A busca prossegue conforme o orçamento e a
continuidade documentados, sem compra, criação de conta ou alteração de coortes.

Critério para dizer que a cadeia econômica está apta: dados admissíveis no
instante da decisão, referência justificável, oferta e capacidade verificáveis,
custos aplicáveis, liquidação reconciliada e validação prospectiva suficiente.
Esses critérios ainda não foram cumpridos; **não há promessa de lucro**.
