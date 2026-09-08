# Revisão metodológica e qualidade do estado final

**Os cálculos recentes sustentam a conclusão de que o projeto ainda não demonstrou lucro realizável. Não encontrei vazamento de resultados de 2026 para o ajuste ou a calibração do novo replay. A principal limitação preditiva permanece: o candidato congelado não supera o mercado; em ambas marcam ele é consistentemente pior nesta amostra.**

Esta revisão usou código, planos e artefatos já derivados. Não consultou ledgers de H14/H15/H9/A1, não coletou dados novos, não alterou experimentos congelados e não procurou parâmetros para melhorar os resultados.

## O que está comprovado e o que permanece limitado

| Aspecto | Parecer | Evidência e consequência |
|---|---|---|
| Separação numérica de treino/calibração/teste | Correta para o replay declarado | Um ajuste em 1.520 jogos de 2021–2024; 380 previsões de 2025 com o mesmo estado; pesos aprendidos só em 2025; nenhuma atualização pelos resultados dos dois turnos de 2026. |
| Convergência do ajuste | Verificada | Uma chamada L-BFGS-B, sucesso e nenhum aviso. Convergência do otimizador não implica qualidade preditiva ou lucro. |
| Calibração | Reconciliada independentemente | 374 vetores válidos em cada mercado; pesos do modelo: 0 em 1X2, 0 em OU2,5, 0,8952001252556239 em ambas marcam. Numeradores, denominadores e pesos conferidos por fórmula separada. |
| Estado fixo | Conforme a regra desta execução | Elo de 28 clubes e parâmetros ficaram congelados; geração de previsões verifica hash e rejeita refit pendente. Mirassol e Remo recebem o rating inicial de 1.500. |
| Paridade com o serving | Parcial | Usa as mesmas funções de distribuição e estatísticas de gols, mas o estado congelado no fim de 2024 não reproduz os cron jobs que atualizam o serving. O resultado não é uma medição direta da operação atual com forças atualizadas. |
| Disponibilidade histórica dos dados | Não demonstrada ponto a ponto | Odds agregadas não têm comprovação suficiente de casa e horário de oferta. O buffer de 48 horas e a concordância de placares delimitam o replay, mas não reconstroem toda a informação historicamente disponível antes de cada decisão. |
| Independência científica do teste | Não existe como teste cego | O histórico já foi explorado e os planos foram congelados em setembro de 2026. A arquitetura/configuração atual foi escolhida retrospectivamente. Não houve otimização sobre os placares de 2026 nesta execução, mas isso não apaga decisões e buscas anteriores. |
| Resultado monetário | Contrafactual, não executado | A liquidação e os custos foram auditados. Sem comprovação de oferta e aceitação das odds, não se pode chamar o saldo de lucro realizável. |
| Segundo turno completo | Ainda não medido | 58 jogos concluídos de 190; os 132 restantes não entraram no retorno. O resultado disponível não prevê o que ocorrerá no restante do turno. |
| Ordem entre teste e paper por turno | Turnos oficiais se sobrepõem no calendário | O segundo turno começou em 25/07/2026, mas Flamengo–Mirassol, da rodada 4, ocorreu em 02/09/2026. Não se pode afirmar que todo o primeiro turno foi avaliado antes de começar o segundo. |

O ponto temporal do ajuste está explícito: último jogo usado em 08/12/2024 às 19h UTC; horizonte do ajuste em 01/01/2025. `ServingStackEvaluator._fit` aplica o decaimento de Elo até esse horizonte e não até setembro de 2026. O gerador congela o estado completo dessa execução antes da calibração. Isso é coerente com o desenho escolhido, mas deixa o retrato dos clubes antigo. A deterioração observada é compatível com essa limitação; esta revisão não demonstrou que atualizar Elo resolveria o problema.

Os turnos são definidos por rodada oficial, não por cortes de data. O primeiro jogo do segundo turno foi em 25/07/2026 às 21h30 UTC. O jogo Flamengo–Mirassol, rodada 4, ID 16890992, foi em 02/09/2026 às 22h30 UTC: um jogo do primeiro turno ocorreu depois do início do segundo. Como o candidato já estava fixo com dados até 2025 e não houve decisão de ajuste baseada no primeiro turno, isso não contamina o ajuste nem muda os pagamentos calculados. Contudo, invalida interpretar o replay como uma sequência operacional em que primeiro se aprova o teste completo e só depois começa o paper.

O modelo usado é NegBin + Dixon–Coles, com grade de 12 gols. O ensemble de xG está desativado, `xg_params` e `dynamic_states` são nulos e não houve fallback de xG. As probabilidades de OU2,5 e ambas marcam vêm dos metadados da mesma grade que gera 1X2, e não de uma Poisson reconstruída apenas com médias de gols. A arquitetura fornece esses mercados ligados a placar; não foi validada aqui para cartões, escanteios ou eventos de jogadores.

## Diagnóstico novo, sem reajuste

Calculei Brier e log-loss para os quatro previsores nos mesmos jogos de cada mercado. A climatologia contém apenas os 1.520 jogos de 2021–2024: probabilidades casa/empate/fora de 46,05%/27,63%/26,32%, over 2,5 de 43,82% e ambas marcam de 48,95%.

Todos os 190 jogos do primeiro turno e os 58 concluídos do segundo têm os três mercados completos e válidos neste artefato. Assim, estas comparações não misturam amostras diferentes. O Brier de 1X2 soma as três classes; o Brier binário usa a classe positiva, portanto os valores entre mercados não têm a mesma escala.

| Mercado e turno | Brier bruto | Brier calibrado | Brier mercado | Brier climatologia |
|---|---:|---:|---:|---:|
| 1X2 — primeiro | 0,614227 | 0,591774 | 0,591774 | 0,631233 |
| 1X2 — segundo disponível | 0,721883 | 0,662413 | 0,662413 | 0,665309 |
| OU2,5 — primeiro | 0,256290 | 0,250913 | 0,250913 | 0,254475 |
| OU2,5 — segundo disponível | 0,253776 | 0,252870 | 0,252870 | 0,251692 |
| Ambas marcam — primeiro | 0,256458 | 0,255308 | 0,247462 | 0,251773 |
| Ambas marcam — segundo disponível | 0,259979 | 0,258882 | 0,251366 | 0,252289 |

O modelo bruto tem Brier e log-loss médios maiores que o mercado nos seis painéis. Isso descreve os dados; não significa que todas as diferenças sejam estatisticamente distinguíveis de zero.

Em 1X2 e OU2,5, o calibrado coincide com o mercado por construção: peso do modelo igual a zero. Sua melhora sobre o modelo bruto não é evidência de que o projeto descobriu informação adicional. Como `q_i=(1/odd_i)/sum(1/odds)` e a soma exigida é pelo menos 1, `q_i` não supera `1/odd_i`. Esses dois mercados não podem passar o filtro de edge positivo desta versão. Zero apostas nesses mercados é consequência matemática da calibração, não defeito do seletor.

O achado mais claro é ambas marcam. O Brier do calibrado menos o mercado é **+0,0078465 no primeiro turno**, com IC95 descritivo **[+0,0043793; +0,0114720]**; no segundo, **+0,0075159**, IC **[+0,0037565; +0,0136691]**. O log-loss também é maior nos dois turnos. A calibração reduz um pouco o erro do modelo bruto, mas ainda preserva grande peso em uma estimativa que perdeu para o mercado. As nove apostas do segundo turno são todas em “ambas marcam: não”, sem diversificação efetiva de mercados.

Os intervalos usam 2.000 reamostragens pareadas por rodada, com seed fixa. O primeiro turno tem 19 rodadas e o segundo apenas 7. Eles são condicionais aos modelos e pesos já estimados, não incluem incerteza do treino/calibração e não corrigem as numerosas comparações e buscas anteriores. As rodadas também podem permanecer correlacionadas entre si. Portanto são diagnósticos, não uma licença para promover ou ajustar uma estratégia.

## Como os estudos recentes se relacionam

1. **Reanálise de seleção, 12 políticas:** confiança ≥60% perdeu 7,34%; confiança ≥70% teve +4,82% em apenas 20 apostas e perdeu no cenário adverso; a correção residual teve +2,21% em 19 apostas e também não resistiu ao estresse. São sinais pequenos entre múltiplas políticas pesquisadas, não demonstrações de uma solução lucrativa. A melhora preditiva contra climatologia não substitui o confronto com preço de mercado.

2. **Preço futuro, nove jogos:** a melhora de 3,35% surgiu em uma ramificação adaptativa após insuficiência da cobertura entre casas. A amostra era pequena e a vantagem podia mudar de sinal retirando um jogo. Esse resultado foi corretamente apresentado como pista.

3. **Extensão de 51 IDs:** 50 foram válidos, sem reajuste do coeficiente. O erro foi 1,47% maior que o da persistência e nenhum evento passou o prêmio implícito de 2%. A pista anterior não se repetiu. Os jogos são distintos, mas se intercalam no mesmo período do teste anterior, logo a extensão não é replicação temporal independente. Esses estudos de preço não utilizaram resultados de partidas nem demonstraram lucro de apostas.

4. **Novo replay por turnos:** principal calibrado no primeiro turno perdeu 14,511 unidades; no trecho disponível do segundo, 1,23 unidade em nove apostas. O bruto teve +0,710 unidade no primeiro turno e −19,495 no segundo disponível. Cada braço já estava previsto e não foi promovido após a leitura dos resultados. A redução da perda do calibrado no segundo turno é uma observação da amostra e da menor exposição; não prova proteção geral nem rentabilidade.

Não é válido selecionar apenas o +4,82%, o +3,35% de previsão de preço ou o +0,710 unidade do bruto e ignorar as extensões e os demais resultados. Também não é válido transformar a ausência de lucro nestas hipóteses em prova de que toda oportunidade é impossível. O que foi demonstrado é mais específico: **estas versões e estes dados não justificam liberar apostas reais**.

## É necessário repetir com Elo atualizado até 2025?

**Não como correção do replay existente. O estado estático é uma restrição válida do desenho escolhido, não uma falha mecânica encontrada nesta revisão.** O plano declara expressamente treino em 2021–2024 e todo o estado, incluindo Elo, congelado depois disso. A execução cumpriu essa regra. A correção necessária é limitar a interpretação: o estudo mede um candidato estático e não a operação continuamente atualizada.

Usar os placares de 2025 para atualizar Elo altera um estado aprendido do modelo, mesmo mantendo os parâmetros da distribuição de gols iguais. Não seria apenas trocar uma informação de exibição. Isso mudaria o protocolo depois de observar os resultados de 2026 e deveria aparecer como um novo candidato exploratório, preservando o resultado anterior. A autorização ampla do usuário permite novos estudos, mas não os transforma retroativamente em correções ou confirmações.

Há ainda duas limitações específicas. Primeiro, os pesos atuais foram calibrados sobre previsões de 2025 produzidas pelo Elo congelado em 2024. Aplicá-los a previsões geradas com outro estado muda o previsor a que a calibração se refere; não se pode presumir a mesma qualidade. Segundo, atualizar Elo uma única vez até o fim de 2025 ainda não reproduz um cron que incorpora novos jogos durante 2026 e pode recalibrar outros componentes. Portanto esse replay adicional continuaria com paridade parcial.

A recomendação ao encerrar esta revisão é **preservar os números, manter a ressalva explícita de paridade e não tratar a atualização de Elo como conserto que promete lucro**. Não há erro de cálculo demonstrado que obrigue uma nova avaliação econômica agora. Uma eventual investigação futura de paridade precisaria especificar toda a atualização temporal e a calibração correspondentes antes de ser executada. Mesmo uma melhora nesse novo diagnóstico não resolveria a falta de comprovação histórica da oferta e execução das odds.

## Verificação e arquivos

O novo programa `diagnostics_quality.py` não importa o runner econômico, não reajusta modelos e não usa banco, rede ou coortes. Verifica IDs, candidato, probabilidades, odds, placares e denominadores entre os artefatos derivados, fixa método e hashes antes do cálculo e publica todos os painéis. Seus 14 testes sintéticos passaram; Ruff passou. Os métodos e números completos estão em `diagnostics_quality_plan.json`, `diagnostics_quality_results.json`, `diagnostics_quality_event_losses.json` e `DIAGNOSTICO_QUALIDADE.md`.

Referências auditadas: `brasileirao_predictor/serving_evaluator.py` (`predict_step` e `_fit`); `work/new_split_backtest/runner.py` (ajuste único, `fit_calibrator`, persistência do candidato e previsões de 2026); planos/resultados em `outputs/REANALISE`, `outputs/EXTENSAO_51` e `outputs/BACKTEST_NOVO_2026`. Nenhum desses artefatos congelados foi alterado nesta revisão.
