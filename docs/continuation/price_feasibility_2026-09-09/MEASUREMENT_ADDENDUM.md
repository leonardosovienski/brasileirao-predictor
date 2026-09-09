# Especificação da medição diagnóstica — antes dos valores

09/09/2026, 18:11 UTC. Nenhum valor numérico novo de odds, label ou desempenho
foi examinado. Somente os nomes de campos do export foram inspecionados:
`odds[1x2]` é vetor H/D/A e o registro não tem casa/clocks de cotação.
As três tentativas diretas de página Brasil, notas e CSV retornaram 503.
Logo, o replay condicional Bet365/Pinnacle fica bloqueado sem mudar de casas.

A medição local da mesma pergunta calculará, em todas as linhas de 2025:

- cobertura numérica de vetores 1X2 completos e razões de abstenção;
- soma implícita S e referência diagnóstica p_i = (1/o_i)/S;
- EV calculado na própria odd, exclusivamente para verificar a identidade
  `p_i * o_i - 1 = 1/S - 1`, nunca para selecionar aposta;
- preço necessário ao break-even `o*_i = (1+c)/p_i`, custo c = 0,02;
- melhoria proporcional requerida `o*_i/o_i - 1 = S*(1+c)-1`;
- a mesma fronteira nos custos já fixados de 0%, 1%, 2%, 3%, 5%, sem otimizar;
- distribuição min/mediana/p90/max e painel mensal, sem labels, seleção ou ROI.

Se S <= 1, preservar e reportar o sinal: não assumir margem positiva por definição.
Valores booleanos, infinitos, odds <= 1, vetores incompletos, identidade duplicada
ou kickoff incompatível não serão silenciosamente aceitos. Ausências permanecem
no universo. Nenhum campo de disponibilidade, bookmaker ou status será fabricado.
O campo kickoff fornecido só define universo/calendário; não autentica captura.

A saída incluirá o resultado do scanner existente sobre os registros legados
sem preencher metadados inexistentes, confirmando a recusa de admissão.
Toda partida ficará abstida por falta de proveniência, ainda que tenha odds.
Nessa trilha abstida: stakes/exposição/custos variáveis/resultado da carteira = 0;
ROI sobre stakes indefinido. Economia de uma estratégia com apostas permanece
não mensurável; custos fixos externos são desconhecidos.

Esta é análise descritiva de preço para decidir qual evidência adquirir a seguir.
Não é nova estratégia, teste de probabilidades verdadeiras ou validação do xG.
Não abrir uma nova frente quando o bloqueio e a medição estiverem documentados.
