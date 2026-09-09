# DC-20260909 — obtenção e admissão dos dados faltantes

Registrado em 09/09/2026 após o pedido explícito para continuar buscando dados,
antes de abrir novos preços ou desempenho. Base local: main
5dec2521bab581d5dda104d954f4cc6274b74702. PF-20260909 permanece encerrado.

## Pergunta principal

É possível obter oferta Bet365 e referência Pinnacle de 1X2 FT do Brasileirão,
com identidade e estado temporal verificáveis, para medir diferença de preço
após fricções e decidir se uma validação econômica pode avançar?

Mecanismo: discrepância entre casas distintas; oferta excluída da referência.
O gargalo continua sendo procedência, disponibilidade e execução. Não há
segunda estratégia nem ajuste de xG. Evidência conhecida: resultados negativos
de xG em 2025, export agregado PF sem clocks, estudos exploratórios encerrados
de timelines Jan–Jun/2026 (30 eventos + extensão de 51). Esses dados já vistos
não são validação independente. Não zerar a contagem histórica de busca.

## Ordem e universo

1. Auditar documentação e hashes dos arquivos desses dois estudos encerrados.
2. Reaproveitar sua lista canônica de 177 fixtures de Jan–Jun/2026; nunca ler
   bancos, resultados ou arquivos H14/H15/H9/A1. Jan–Jun é janela exploratória
   permitida conforme contratos e ADMISSIBILITY.md de 07/09; não é holdout.
3. Verificar documentação pública das fontes. OddsPapi v4 é candidata primária
   por já ter fornecido timelines no projeto; The Odds API, Football-Data,
   Betfair histórico e outras fontes públicas são alternativas de aquisição,
   não novas estratégias escolhidas após desempenho.
4. Consultar credencial existente apenas em processo de aquisição separado,
   sem imprimi-la, gravá-la ou expor .env ao processo de pesquisa. Consulta
   GET account somente após confirmar publicamente ser não tarifada.
5. Se o acesso/cota permitir, obter no máximo uma timeline por fixture e par
   fixo, reutilizando respostas completas já existentes. Manter faltantes,
   erros e estados suspensos. Nenhum filtro active=true. Sem substituir jogos.

Decisão desejada: kickoff menos 60 min, idade máxima 120 s, skew máximo 30 s.
Mercado 101/1X2, FT, linha nula; sides home/draw/away. Somente o último estado
por seleção anterior ao corte. Estados inativos e conflitos invalidam a seleção;
não procurar uma odd antiga ativa após suspensão. O horário createdAt de uma
timeline retrospectiva não equivale a recebimento histórico pelo pesquisador.
Nunca preencher available_at/received_at retrospectivos por conveniência.
O kickoff retrospectivo também requer evidência de calendário PIT para replay.

## Medição e decisão

Medir primeiro cobertura do universo, integridade de identidade, timestamps,
estados, limites e completude por casa. Rejeitar preços não admissíveis antes
de qualquer avaliação de lucro. Preservar payload, requisição sanitizada,
horário real de recebimento e SHA-256. Hash não autentica execução.

Se houver pares de estados temporais completos, medir somente diagnóstico de
preço condicional: q proporcional Pinnacle, S>1; Bet365 fora da referência;
q*odd-1-c, c=2% por unidade, maior EV positivo <=15%, desempate lexical,
uma seleção por jogo. Custos de sensibilidade fixos 0/1/2/3/5%, sem otimização.
Comparador abstenção. Relatar picks condicionais separadamente de apostas:
não converter diagnóstico em fill. Comissão, imposto, liquidez, limites reais,
slippage, rejeições, infraestrutura e manutenção desconhecidos ficam nulos.
Sem evidência suficiente de execução e labels admissíveis, não produzir ROI.
Não consultar desfechos apenas para obter um número econômico aparente.

Se a aquisição revelar fonte prospectiva utilizável, registrar o plano de
observação independente ANTES da primeira captura e verificar recursos,
calendário e separação das coortes. Uma nova captura não recupera clocks de
2025/2026 e não constitui validação futura suficiente instantaneamente.

## Isolamento, recursos e parada

Trabalhar sozinho. Arquivos novos em C:/BRASILEIRAO/work/data-completion-2026-09-09;
artefatos documentais em docs/continuation/data_completion_2026-09-09. Preservar
integralmente arquivos migrados, estudos anteriores, contratos e agendas.
Nenhum serviço, tarefa protegida, avaliador, Redis ou SQLite será executado.

Orçamento desta rodada: até 150 minutos de investigação principal, até 40
requisições públicas diretas de documentação/dados, até 177 históricos gratuitos
únicos, até 6 consultas não tarifadas de conta. Zero compras, novas contas,
login de bookmaker ou apostas. Zero chamadas tarifadas sem plano, custo e
reserva atuais demonstrados. Histórico gratuito também deve respeitar quota
disponível e cooldown: mínimo 7 s após resposta; parar a fonte em 401/403/cota
esgotada, ou após 3 falhas de transporte/5xx consecutivas, sem contornar bloqueio.
Repetir uma fonte pública que falhou na rodada anterior é nova tentativa
documentada, não prova de inexistência de dados se voltar a falhar.

Encerrar a frente ao obter evidência que permita avançar, refutar a premissa
no escopo, esgotar orçamento ou demonstrar bloqueio externo sem ação útil
autorizada. Concluir as alternativas úteis previstas e a documentação antes
da entrega. Não declarar tudo OK enquanto qualquer gate obrigatório faltar.
