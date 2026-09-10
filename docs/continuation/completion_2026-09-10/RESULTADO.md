# CPL-20260910 — correções, dados e validação delimitada

Foram corrigidos e testados contratos de previsão, temporalidade, preços, contabilidade e infraestrutura. **O projeto não foi entregue lucrando. A revisão semântica integral ainda não está demonstrada.** O mandato continua aberto; esta entrega fixa código e evidências para prosseguir sem perder trabalho ou transformar um checkpoint em conclusão global.

Os [registros centrais](REGISTROS.md) ligam cada alegação à falha, ação, teste e limite. A base foi main/456b9025cfa3a596e754088ec3001fbeb5fcc7de. Trabalho solo, em C:/BRASILEIRAO. Nenhuma aposta, ordem, autenticação de conta de apostas, API limitada ou consulta de resultados das coortes nesta rodada. H14/H15/H9/A1 e dependências compartilhadas identificadas foram preservadas; ver evidence/boundary-check.json.

## Validação e três estados

- Técnica: **pronto no escopo dos contratos corrigidos; sistema global não pronto**.196 testes Python passaram:192 integrados,3 do inicializador e1 adicional de schema legado.27 testes com Redis real passaram.119 casos .NET únicos passaram em execuções separadas: o último lote completo teve118 passagens e1 falha de inicialização; o caso restante passou isoladamente depois da instrumentação. A causa da falha intermitente continua desconhecida. Não reportar119/119 numa única execução final.
- Dados: **parciais/insuficientes para lucro executável**. Sete GETs públicos documentais nesta rodada; cinco respostas200, das quais uma era Page Not Found. Duas falhas na API-Football, a segunda403. Nenhum preço novo recuperado, nenhum label novo acessado. Raw documental, URLs, horários, bytes e hashes preservados.
- Economia: **não mensurável para execução real**. BE conserva um candidato de preços condicionado, sem casa/horário/fill comprovados. Não houve nova performance, mudança de stake ou ajuste para obter saldo favorável.

Ruff/formato e Pyright verificam o conjunto alterado; build, instalação de wheel, CLI, manifesto e recuperação Git constam dos recibos finais. Falhas anteriores e recusas das barreiras de isolamento permanecem na entrega. Testes tentaram caminhos legados de SQLite e leitura de cache: o runner recusou antes do acesso; isso não foi acesso operacional nem prova de que o legado fosse isolado por si só.

Inventário450 arquivos:78 com leitura semântica registrada nesta continuação,314 com análise estática/pontual e58 sob contrato protegido. Essa discriminação corrige a alegação anterior de revisão completa. A profundidade por arquivo está no inventário; ainda não representa semântica integral de todos os arquivos. Módulo serving_evaluator contém classe H9 junto de código legado e foi reclassificado como misto protegido; nenhum avaliador/coorte foi executado.

## Rodada econômica:14 itens

1. **Pergunta:** o envelope BE pode virar observação nominal, simultânea e utilizável sem confundir recibo com execução?
2. **Prioridade:** procedência do preço e preenchimento mudam mais a decisão que outro modelo ajustado aos mesmos anos.
3. **Hipótese/mecanismo:** carteira dos três resultados pode ter sobra se todas as pernas estiverem realmente disponíveis nas condições usadas. A simultaneidade/aceitação não está demonstrada.
4. **Experimento:** investigação documental e implementação de contratos, limitada previamente a12 GETs públicos;7 realizados. Não houve teste novo de retornos. A conta BE ficou congelada.
5. **Dados/fontes:** CSV e177 históricos já íntegros não foram repetidos. Fontes primárias The Odds API e Sportmonks recuperadas; API-Football documental bloqueada. Ver [mapa](MAPA_DADOS.md).
6. **Disponibilidade temporal:** received/observed/published/changed/decision separados. Publicação desconhecida é null. Nova leitura nunca comprova disponibilidade passada. O decoder conserva vazio/inválido e abstém.
7. **Resultado:** nenhuma nova oferta nominal recuperada;0 apostas e0 exposição nesta rodada. Resultado BE permanece histórico:226 carteiras hipotéticas,+4,6376u; modelo de gols−99,60u. Não são resultados CPL nem garantia futura.
8. **Custos:**0 chamadas autenticadas/limitadas. Custos pessoais, capacidade, moeda e infraestrutura atribuível desconhecidos; PnL líquido total e ROI executável não mensuráveis. Não assumir zero para esses custos.
9. **Riscos:** preenchimento parcial, revisão/suspensão, identidade incorreta, relógios incompletos, múltiplas tentativas, concentração e uso retrospectivo de máximos. As sensibilidades BE são hipóteses preservadas, não taxas observadas.
10. **Limitações:** sem histórico nominal simultâneo, limite pessoal ou aceite; módulos legados e Compose/feed comercial não homologados; cobertura semântica geral ainda parcial; coortes protegidas fora da execução.
11. **Testes:** regressões sintéticas antes/depois, contratos de fonte, cortes UTC, cálculo de probabilidades, banca por ID, leitura RO, logs, .NET/Redis, build/CLI e cópia/restauração. Testes de software não substituem evidência de mercado.
12. **Estado da evidência:** suficiente para confiar somente nos contratos demonstrados; insuficiente para admitir operação ou rentabilidade. Hipótese de suficiência da infraestrutura refutada; oportunidade comercial ainda não mensurável.
13. **Decisão:** manter candidato BE para investigação de preço nominal; modelo de gols reprovado permanece sem prioridade; nenhum novo tuning, capital ou observador. Não modificar captura DC para acomodar o candidato de três pernas.
14. **Próxima informação decisiva:** preços identificados simultâneos, seus estados/revisões e condições verificáveis para preencher as três pernas, seguidos de protocolo futuro separado. A captura DC de11/09 23:00UTC testa somente a dupla congelada e não valida essa carteira.

A descoberta que mais muda a decisão é que havia falhas concretas capazes de alterar odds/probabilidades/contabilidade e de exagerar a confiança exibida. Corrigi-las torna a decisão mais fiel aos dados; não cria, por si, uma oferta rentável. A hipótese que perdeu prioridade continua sendo recuperar lucro retunando o modelo de gols já reprovado.

## Continuação necessária

Prosseguir pelos itens abertos CPL-P21–26 e pelo [próximo prompt](PROXIMO_PROMPT.md). Não repetir testes já aprovados sem mudança ou falha concreta. Não modificar dependências protegidas para fechar checklist. Não declarar o mandato integralmente concluído enquanto a cobertura não estiver demonstrada e houver trabalho necessário viável.

Código integrado, hashes e backups: C:/BRASILEIRAO/AUDITORIA/CONTINUACAO_INTEGRAL_2026-09-10.json. A restauração da entrega de código/evidência não é restauração operacional de bancos/coortes protegidos.
