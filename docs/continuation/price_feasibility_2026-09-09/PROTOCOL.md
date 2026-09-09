# Rodada PF-20260909 — validade e economia do preço 1X2

Registrado em 09/09/2026, após reconhecimento e antes de abrir novos preços
ou resultados. Base: main f00304574044ab9d18aa3603abc538fbb3102c64.

## Pergunta principal e escolha

Existe oferta 1X2 de uma casa identificada que exceda uma referência independente,
simultaneamente disponível, por valor suficiente para sobreviver a custos?
Mecanismo: diferenças de preço entre casas, usando normalização proporcional
somente da casa de referência. A oferta nunca integra sua própria referência.

Dados necessários: identidade, período FT/90 minutos, linha nula, três seleções,
casa, estado ativo, clocks de observação/disponibilidade/recebimento, kickoff,
histórico de revisões e condições de execução. O preço necessário satisfaz
`p * odd > 1 + c` para custo fixo c, antes de fricções não especificadas.

Evidência conhecida: os replays xG de 2025 já foram explorados e perderam dinheiro;
o blend perdeu menos unidades sobretudo por menor exposição. Não são holdouts.
O scanner existente exclui a própria casa e bloqueia estados vencidos/suspensos.
A principal incerteza agora é a existência de preços admissíveis, não o modelo.

Teste mínimo: auditar a proveniência dos insumos históricos já usados e tentar
uma fonte pública independente. Se faltar informação temporal ou casa, não
adaptar inventando campos. A incerteza de execução permanece mesmo com clocks.
Risco principal de falso positivo: fechar o mercado retrospectivamente, comparar
casas em instantes diferentes, tratar máxima agregada como uma oferta real.
Dependências: arquivo migrado, acesso público gratuito e scanner puro existente.

Modelagem adicional perde prioridade. Nenhuma segunda hipótese fica ativa.
Uma análise condicional dos preços, definida abaixo, é parte da mesma pergunta
e só justifica o custo de uma futura aquisição/observação; não prova execução.

## Universo e regras fixadas

- Brasileirão Série A, temporada 2025 inteira, somente 1X2 FT, sem linha.
- Decisão executável desejada: 60 minutos antes do início, considerando apenas
  o último estado recebido até o corte. Idade máxima 120 s e skew máximo 30 s.
- Fonte local: exclusivamente o export histórico do estudo encerrado
  `price_strength_evaluation_2026-09-07/inputs/history.json`; selecionar 2025
  antes de qualquer cálculo. Não consultar bancos, ledgers ou coortes.
- Tentativa pública: Football-Data, página Brasil, dicionário e CSV oficial.
  Examinar apenas 2025, excluir desfechos até terminar a auditoria de admissão.
- Se houver colunas individuais Bet365 e Pinnacle: oferta Bet365 e referência
  Pinnacle, usando exatamente o conjunto de preços descrito pela fonte.
  Não inverter casas, escolher abertura/fechamento pelo saldo nem usar Max/Avg
  como bookmaker. Se esse par não existir, encerrar essa análise condicional.
- Referência: q proporcional Pinnacle, soma implícita estritamente maior que 1.
- Seleção: maior EV líquido entre home/draw/away; desempate lexical. No máximo
  uma aposta por partida, EV líquido > 0 e <= 15%. Nenhum ajuste posterior.
- Custo de cenário principal: 0,02 unidade por unidade apostada; comissão zero
  apenas como hipótese explícita do cenário sportsbook, não custo conhecido.
  Curva descritiva de sensibilidade fixa: 0%, 1%, 2%, 3%, 5%; manter as escolhas
  do cenário de 2% para separar custos de seleção. Sem selecionar variante.
- Stake simulado: 1 u por aposta; banca de cenário 100 u; sem aportes.
- Sem evidência PIT: abster-se na leitura executável e marcar o eventual replay
  `CONDITIONAL_NON_EXECUTABLE`. Não criar snapshots normalizados fictícios.
- Recusas, limites, liquidez, slippage, impostos, custo de dados, infraestrutura
  e manutenção desconhecidos não viram zero na conclusão executável.
- Liquidação condicional 1X2: vitória retorna odd vezes stake, derrota zero;
  principal devolvido não é lucro. Void/push/desfecho conflitante ou pendente
  fica não liquidado, sem inventar resultado. Mercados asiáticos/lay excluídos.
- Para carteira condicional, se houver horário sem fuso comprovado, usar apenas
  sessões por data da fonte: reservar todas as stakes do dia antes de liquidar,
  sem inventar hora UTC; a exposição assim calculada é cenário, não medição real.
- Comparador principal: abstenção (0 stakes/0 resultado). Proibir comparação
  econômica com xG de outro universo. Relatar todos os jogos, inclusive sem odds.
- Resultado positivo será exploratório e exigirá nova validação prospectiva;
  resultado negativo encerra apenas esse par/regra/temporada/cenário.
- Se houver apostas condicionais: P&L/ROI, cobertura, exposição por sessão,
  concentração, calibração das seleções, blocos temporais e bootstrap por semana
  (2.000 réplicas, semente 20260909); semanas, não snapshots, são a unidade.

## Isolamento, orçamento e parada

Trabalhar sozinho. Preservar bundle/ZIP originais. Somente extração por allowlist
com SHA verificado; nunca extrair credenciais nem importar agendas. Pesquisa
em C:/BRASILEIRAO/work/price-feasibility-2026-09-09; nenhum serviço iniciado.
Não consultar H14/H15/H9/A1, inclusive resultados, métricas, claims ou snapshots.
Não renovar atestados. Não alterar dependências compartilhadas da operação.

Orçamento: uma rodada de até 75 minutos a partir de 18:10 UTC, um export local,
até seis requisições públicas pontuais de dados/documentação (sem autenticação),
zero chamadas de API com chave, zero recursos pagos/reservados e um replay
condicional se o contrato das colunas permitir. Instalação local de ferramentas
livres para testes não é aquisição de dados. Não iniciar coleta recorrente.

Parar a investigação principal quando: (a) a admissão permitir avançar para
validação nova; (b) a premissa for refutada no escopo; (c) orçamento esgotar;
(d) faltar informação externa irrecuperável dentro dos recursos autorizados.
Concluir documentação e verificações proporcionais sem abrir nova frente.
Nenhum saldo, hash, diagnóstico ou teste desta rodada libera capital.
