# N05 — preparado, execução bloqueada

Este documento apresenta o conteúdo de [N05_PROTOCOL.json](N05_PROTOCOL.json). Não houve fitting nem consulta de desfechos para decidir se vale executar.

**id**: N05-A-PREPARED-01

**status**: PREPARED_NOT_EXECUTABLE

**actual_seasons**: UNKNOWN_PENDING_AUTHORIZED_MANIFEST

**question_A**: Incremento probabilístico sobre market-only contemporâneo; aceite pessoal de aposta não é requisito.

**question_B**: Economia líquida requer execução/custos/caixa além de A.

**unit**: Uma partida; mesmas linhas elegíveis para todas as previsões pareadas; universo e razões de exclusão preservados.

**partition**: História causal de seis anos para Elo; janela de quatro anos para fit de gols; uma temporada inteira validação e temporada seguinte teste, ambas a definir por manifesto autorizado antes de acesso a desfechos.

**model**: HEAD/config da baseline congelados, sem xG ou novas features. Fit antes de validação e antes de teste; parâmetros de gols fixos dentro de cada partição; atualização Elo causal apenas com resultados comprovadamente disponíveis. Não afirmar equivalência a execução operacional sem revisar adapter de estudo.

**budget**: Dois fits, cada um até duas tentativas do otimizador existente: máximo quatro tentativas. Mistura w em 0,0.1,...,1, selecionada somente na validação por log loss; empate escolhe menor w. Sem outra busca/calibrador.

**predictions**: market-only q; model-only p; composição (1-w)q+w*p. Grade incumbente 12 com diagnóstico de cauda: se massa omitida >1e-6, domínio não certificado ou falha, abstenção registrada antes de scoring. Não substituir silenciosamente pelo protótipo de domínio menor.

**market**: FT 1X2 completo, três seleções da mesma casa nominal e vintage; proporcional como método primário, FAIR explícito; underround excluído por regra congelada. Shin/power sensibilidades apenas no mesmo painel, sem escolher vencedor.

**cutoff**: T−60 min do kickoff congelado e conhecido 24 h antes; alterações posteriores do kickoff implicam abstenção. Snapshot com receipt <= decisão e idade <=5 min; sem inventar receipt retroativo.

**metric**: Log loss natural média, principal por ser scoring próprio que avalia a distribuição completa; clip 1e-12 apenas na avaliação, contar ocorrências. Brier soma das três classes (0..2), empate e bins fixos de calibração como diagnósticos, sem ajuste.

**paired**: Diferenças por partida: loss_model-loss_market e loss_blend-loss_market; mesmas linhas e índices de reamostragem.

**uncertainty**: Bootstrap por blocos móveis de calendário de 28 dias, preservando jogos simultâneos e dias sem jogo; 4000 réplicas, seed 20260911. IC bilateral 95% e limite superior unilateral 97.5% para cada uma das duas comparações prespecificadas (Bonferroni). Sensibilidades de 14/56 dias, sem selecionar significância. Dependência além do bloco permanece limitação.

**decision**: Para cada comparação: média <= -0.005 nats e limite superior ajustado <0. Valor prático prespecificado, não universal. Falha não prova equivalência. Sem parada opcional nem escolha pelo teste.

**minimum**: >=300 partidas comuns, >=80% do universo alvo congelado e >=224 dias de calendário no teste; limites operacionais, não cálculo de poder. Se falhar: insuficiente, sem trocar coorte após resultados.

**execution_gate**: Manifesto com temporadas, IDs e hashes reais; não preencher por conveniência.; Autorização específica e revisão documentada de interseções BE/H14/H15/H9/A1 e demais protegidos.; Evidência de cobertura, licença, identidade, clocks/revisões dos preços e histórico de treino.; Adapter de estudo revisado antes de fitting; regra de abstenção e universo congelados.

**gate_result**: BLOCKED: não existe coorte aprovada ou auditoria temporal demonstrada nesta rodada. Pergunta A conceitualmente sobrepõe comparação BE; trocar biblioteca/distribuição/ano não cria independência.

Contrato de campos: [N05_DATA_CONTRACT.json](N05_DATA_CONTRACT.json). A autorização genérica desta rodada não substitui permissões específicas das linhagens protegidas. A primeira ação permitida é revisar um manifesto e provas documentais, sem abrir resultados. Não foi criada uma coorte fictícia.
