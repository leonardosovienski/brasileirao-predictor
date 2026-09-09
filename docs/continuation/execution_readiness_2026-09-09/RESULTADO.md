# ER-20260909 — rotina corrigida e condições documentadas

**Cinco falhas corrigidas, 153 testes aprovados e cinco fontes públicas
preservadas. A captura futura está preparada; lucro executável continua
não demonstrado.** Base main `7f18d543891cb3e68bb82c0a0d9fb58f9a8f12c0`.

## O que mudou na decisão

Corrigiu-se uma interpretação anterior: a
[documentação OddsPapi](https://oddspapi.io/us/docs/get-odds) explica que
`bookmakerIsActive` indica principalmente a coleta do agregador para a casa
naquele fixture. O valor false nas três capturas impede admitir aquele feed;
não demonstra que a própria casa suspendeu a aposta. `suspended`,
`marketActive` e `active` têm papéis separados. O próximo teste continua a
verificar coleta ativa, estados, calendário e recebimento antes do corte.

Os registros anteriores conservam seus bytes e resultados. A expressão anterior
“oferta inativa” deve ser entendida, no piloto, como falta de comprovação de
coleta ativa no agregador. Não é evidência de inexistência de oportunidade.

## Condições recuperadas em fontes públicas

O [guia do fornecedor](https://oddspapi.io/blog/betting-limits-api-stake-sizing/)
explica `limit` como stake máximo reportado para uma seleção de sportsbook,
expresso na moeda da conta de origem. Isso esclarece o campo, mas não identifica
a moeda do registro brasileiro nem converte a moeda da assinatura da API na
moeda da aposta. Os limites nulos da oferta permanecem desconhecidos; o número
450 da referência não vira capacidade pessoal ou capacidade da Bet365.

A [ajuda oficial Bet365 Brasil](https://help.bet365.bet.br/s/pt-br/sports/min-max-stake)
lista R$ 0,50 como referência mínima da tabela em BRL e informa que o mínimo
pode variar com as odds. O máximo depende da aposta e pode ser informado no
cupom, inclusive com análise de valor adicional. A página pública não fornece
o máximo aplicável ao usuário e à seleção desta pesquisa. Não houve login,
acesso a cupom, envio de aposta ou tentativa de obter aceite.

O [serviço atual da Receita](https://www.gov.br/pt-br/servicos/apurar-imposto-sobre-premios-de-apostas-na-loteria-de-quota-fixa-e-em-fantasy-sport)
descreve apuração anual com ComprovaBet e alíquota de 15% sobre o excedente ao
limite de isenção. A [tabela de 2026](https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/2026)
lista essa alíquota para o rendimento específico. É uma regra tributária geral
documentada, não imposto linear de 2% por stake. Sem base anual pessoal,
enquadramento e dados aplicáveis completos, o valor efetivo permanece nulo.
Nenhuma informação pessoal fiscal foi consultada ou estimada.

Essas condições constam de [execution_contract.json](evidencias/execution_contract.json).
Parâmetros hipotéticos do closing anterior não foram substituídos nem
reestimados depois do saldo conhecido.

## Falhas demonstradas e corrigidas

O ensaio inicial teve **cinco falhas e sete sucessos**. As falhas mostraram:

1. JSON inválido da resposta era descartado antes de ser preservado.
2. Falha de configuração/credencial encerrava a rotina sem recibo diagnóstico.
3. Ausência de kickoff derrubava a auditoria em vez de produzir rejeição.
4. Uma pasta deixada por execução parcial impedia a auditoria seguinte.
5. O recibo não exigia a origem e os parâmetros exatos da consulta congelada.

As correções preservam o corpo de preços antes do parse, registram falhas
sanitizadas, rejeitam entradas incompletas e publicam a auditoria por arquivo
temporário seguido de substituição. A pasta parcial pode ser retomada; o
resultado final existente continua preservado. HTTP 429 não provoca retry.
O recibo precisa corresponder ao endpoint, fixture, casas, formato e status
esperados. Hash continua sendo verificação de integridade, não de autenticidade
ou aceite de uma aposta.

O ensaio final tem **15 testes novos**, incluindo cotas, plano pago, janela,
idempotência, erro HTTP, resposta inválida, origem, timezone e adiamento.
Com os 138 testes anteriores: **153 aprovados**. Ruff e Pyright dos dois
executores alterados passaram. As respostas de HTTP e a chave dos ensaios são
sintéticas; nenhuma chave real ou API de odds foi usada nesses testes.

Uma captura real já existente do piloto também percorreu o auditor corrigido
em processo separado com suas datas e payload preservados. Foi rejeitada para
T−60, como deveria. Não foi contada como nova observação. O isolamento bloqueou
rede, SQLite, subprocessos e entradas privadas/operacionais. O teste de
aquisição simulada não executa transação financeira.

## Situação econômica e próximo passo

| Item do mandato | Resultado desta etapa |
| --- | --- |
| Pergunta e prioridade | Recuperar condições de execução e remover falhas da observação que alimentará a medição econômica |
| Hipótese/mecanismo | Diferença entre Pinnacle e Bet365 Brasil; oferta fora da referência, sem nova variante |
| Experimento | Ensaios de aquisição/auditoria, regressões antes/depois e conferência de um payload real já observado |
| Dados/fontes | Cinco páginas oficiais/primárias com HTTP 200, relógios e SHA-256; nenhuma nova odd ou label |
| Disponibilidade temporal | Nenhum clock histórico foi fabricado; corte e calendário prospectivos permanecem congelados |
| Resultado econômico/parcial | Falhas da rotina removidas e contratos esclarecidos; zero nova evidência de lucro |
| Custos | Cinco GETs públicos; zero consulta autenticada, consumo da quota de odds ou contratação nesta etapa |
| Riscos | Feed pode permanecer sem coleta ativa, chegar tarde, omitir limite ou divergir da oferta efetiva |
| Limitações | Limite específico, moeda de origem, aceite, custo total e validação futura ainda não demonstrados |
| Testes | 153 testes, Ruff, Pyright explícito de dois executores, auditoria isolada do payload anterior |
| Estado da evidência | Prontidão técnica melhorada; cadeia econômica incompleta |
| Decisão | Manter a única captura programada, sem ampliar casas, horários, quotas ou filtros |
| Informação decisiva | Par coletado ativamente antes do corte, depois capacidade/custos aplicáveis e amostra prospectiva suficiente |

**Qual descoberta mais mudou a decisão?** A distinção entre coleta do agregador
e disponibilidade real da casa, somada às cinco falhas reproduzidas na rotina.

**Qual hipótese perdeu prioridade?** Tentar obter o limite pessoal a partir de
uma tabela pública ou substituir condições reais por uma porcentagem fixa.
O mecanismo econômico continua sem validação; não foi refutado por esses ensaios.

**Qual informação agora decide o próximo passo?** A observação prevista para
11/09 antes das 20:00 de São Paulo e a comprovação das condições de execução.
Uma única captura ainda não é amostra de validação suficiente.

[Reprodução, arquivos e recibos](REPRODUZIR.md). Tudo desta etapa fica em
`C:/BRASILEIRAO`. H14/H15/H9/A1, serviços, contratos protegidos e agendas
permanecem intactos. A aplicação operacional completa não foi instalada ou
testada. O acompanhamento existente continua; não foi criada segunda automação.
