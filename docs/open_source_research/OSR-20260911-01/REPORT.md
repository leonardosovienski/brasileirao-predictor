# Brasileirão Predictor — pesquisa e benchmark OSR-20260911-01

**Decisão principal:** conservar a arquitetura e os componentes que passaram nos controles; priorizar diagnóstico de cauda e admissibilidade temporal antes de trocar modelos ou adicionar bibliotecas. O levantamento reúne **58 referências**, **15 revisões focais de código**, **12 capacidades** e **3 ensaios sintéticos**. Não é homologação operacional, demonstração de previsão melhor ou lucro.

| Eixo | Conclusão desta rodada |
| --- | --- |
| ENGINEERING_STATUS | Três ensaios controlados concluídos; defeito de diagnóstico de cauda e limites das referências identificados. |
| DATA_ADMISSIBILITY | Somente fixtures sintéticas admitidas à execução. Nova avaliação com dados reais não estabelecida. |
| PREDICTIVE_EVIDENCE | Não avaliada: nenhum fitting, holdout ou previsão real comparada. |
| ECONOMIC_EVIDENCE | Não avaliada: nenhum PnL real, aposta, API de odds ou estudo protegido executado. |


Beneficiário fixado em `d9584af6deeec701cf8989349f22ab7e4b398249` (`main`). Canonical: `docs/open_source_research/OSR-20260911-01/`. [Baseline e cobertura](BASELINE.md) · [Survey e fontes](SURVEY.md) · [Matriz e ranking](CAPABILITY_MATRIX.md) · [Protocolos/resultados](EXPERIMENTS.md) · [Decisões](DECISIONS.md) · [Registro único](registry.json).

## Achados que mudam decisões

1. **Cauda não é garantida por soma 1.** A grade NB/DC 0..12 normalizada omitiu 0,0000261%, 0,4153% e 14,2039% da massa nos três cenários sintéticos predefinidos. No stress maior, 1X2 mudou até 2,3326 pontos percentuais frente à grade 0..100. Isso justifica diagnóstico/adaptação de suporte; não estima o erro dos forecasts reais. [T01](EXPERIMENTS.md).
2. **Referência externa também falha.** Dez dos doze pares Shin/power concordaram dentro de 4,63e-13; dois falharam no solver externo. Um dataclass externo aceitou probabilidade negativa. O local foi mais robusto nesses casos específicos. Decisão: adapter estreito e validação, sem substituição ampla. [T02](EXPERIMENTS.md).
3. **Pagamentos e caixa passaram no domínio testado.** 450 comparações atômicas tiveram erro zero; caixa 100 não financiou duas posições simultâneas de 60. Lay, comissão de exchange, fills e multi-market por partida não foram certificados. [T03](EXPERIMENTS.md).
4. **O próximo gargalo de pesquisa é evidência temporal e de execução.** Features legadas usam data anterior; contratos PIT novos têm mais relógios; autenticidade e cobertura reais não foram verificadas. Essa é limitação de admissibilidade conhecida, não diagnóstico causal da maior fonte de erro preditivo. [Baseline](BASELINE.md).

## Ranking de pesquisa

| ID | Capacidade | Prioridade estimada | Intervalo de sensibilidade |
| --- | --- | --- | --- |
| K01 | Massa de cauda e suporte adaptativo | 89.4 | [79.4, 93.3] |
| K03 | Adapter estrito e diferencial de retirada de margem | 85.0 | [75.0, 91.45] |
| K04 | Scoring, empate, calibração e convenções | 83.8 | [73.8, 90.25] |
| K02 | Admissibilidade temporal e identidade com testes adversariais | 80.6 | [65.6, 88.25] |
| K05 | Pagamentos, caixa e exposição por partida | 76.6 | [61.6, 87.78] |


O score segue o perfil habilitador do mandato e seus pesos; os intervalos são juízos de sensibilidade, não IC. Diferenças pequenas não significam superioridade demonstrada. K12, ganho incremental além das odds, está UNRANKED por falta de dados econômicos e de execução. [Pesos, notas e dez visões por categoria](CAPABILITY_MATRIX.md).

## Respostas às doze perguntas do mandato

**1. O que realmente faz?** Código de Elo, NB/DC, features históricas, mercados derivados, de-vig, contratos PIT e replay de caixa foi inspecionado. Apenas cálculos sintéticos de grade/margem/pagamentos/caixa foram executados. Integração Python/Redis/.NET, operação real, bases privadas e estudos protegidos não foram executados. `predictor-core/ops` declarados não equivalem a uso operacional certificado.

**2. O que a busca global acrescentou?** goalmodel/footBayes fornecem contrastes de gols e regularização; scoringrules e shin ajudam a verificar convenções; kloppy/socceraction/floodlight/databallpy oferecem padronização, ações e sincronização; flumine explicita requisitos de execução. Cada referência tem nível de inspeção e versão em [SURVEY](SURVEY.md). Não são competidores diretos equivalentes.

**3. O que pode melhorar mais o existente?** K01, K03 e K04 reduzem erros de matemática/comparação com baixo custo estimado; K02/K08 determinam se uma comparação futura pode ser válida. Descanso/contexto já têm código e merecem prova de fonte, não implementação duplicada. Ganho é esperado e ainda não medido para previsão.

**4. O que depende de dados ausentes?** xT/VAEP, pressão e sincronização exigem eventos/tracking; disponibilidade de elenco exige notícias/escalações publicadas antes do cutoff. Não foi comprovada cobertura brasileira admissível nas fontes abertas consultadas. Permanecem possíveis os testes de coordenadas toy, cauda, scoring, clocks e caixa.

**5. Onde está o problema principal?** Há um problema de cauda reproduzido e uma barreira factual de temporalidade/aceitação. Não é possível hierarquizar probabilidades, empate, preço, seleção e execução como causas de desempenho sem avaliação real admissível. Forçar recall de empate não resolve essa incerteza.

**6. O que se transfere?** Identidades matemáticas, validação de schema, orientação espacial e engenharia de replay transferem com ajuste de contrato. Parâmetros de força, xG, calibração, distribuições de gols/empates e filtros econômicos exigem validação brasileira. A [CBF documenta mudança de calendário em 2026](https://www.cbf.com.br/a-cbf/noticias/informes-cbf/a/cbf-anuncia-novo-calendario-do-futebol-profissional-masculino), motivo concreto para versionar contexto, sem presumir efeito estatístico ou usar resultados da temporada.

**7. O esportivo acrescenta ao preço?** UNKNOWN. Nenhuma comparação nova model-only / market-only / composição foi autorizada pelos dados desta rodada. Estudos externos e código residual não respondem por este sistema. N05 define o contraste condicionado e a revisão de linhagem BE necessária.

**8. Quais mercados?** 1X2, BTTS, DNB, totais inteiros/meios e AH têm caminho matemático que sustenta validação adicional. Períodos, cartões, escanteios e jogadores precisam alvos/regras/dados próprios; não justificam operar agora. Lay e arbitragem aparente com melhor preço retrospectivo, caixa reutilizado ou quote stale não recebem conclusão econômica.

**9. Quais referências verificam contas?** CDF NB e cenários analíticos verificam grade/pagamentos/caixa; penaltyblog compara margem; shin/implied/scoringrules são próximos contrastes de convenções. flumine inspira requisitos, mas seu SDK relacionado não é segunda replicação econômica. Regras nominais de casas ainda precisam revisão antes de simular aceitação real.

**10. Quais vantagens e reusos?** Duas bordas de solver mais robustas localmente e caixa/pagamentos coerentes nos testes. Não há vantagem preditiva/econômica verificada. Reusar adapters e contratos pontuais; ausência de tracking, mais algoritmos ou dashboard não é gap obrigatório. Nenhuma estimativa de código desperdiçado foi feita.

**11. Que composições e rejeições?** Priorizar grade→preço→scoring→caixa e dados PIT→contexto→força; comparar incremento além de odds somente em coorte nova. Rejeitar troca integral de runtime, known_at inventado, closing como preço anterior, dependência crítica arquivada e novo campeonato de modelos sem dados. Eventos e Bayesian pooling permanecem condicionados, não refutados.

**12. Quais próximos cinco?** N01 cauda adaptativa; N02 adapters e convenções matemáticas; N03 mutation tests PIT; N04 coordenadas/xT toy; N05 incremento esportivo contra market-only, bloqueado por coorte/permissões/dados. Cada um tem pergunta, teste mínimo, pré-requisitos, critério e gate em [EXPERIMENTS](EXPERIMENTS.md). Não foram disparados trabalhos futuros.

## Limites e preservação

Produção, locks, bases, serviços, automações e protocolos foram preservados; nenhum commit/push/merge. H14/H15/H9/A1 e BE não foram reavaliados ou consultados por fontes substitutas. Não houve API de apostas, compra ou capital. O recibo de CI antigo foi lido como documento, não certificado como execução atual.

A rodada é **parcial frente ao mandato amplo**: falta sweep integral de issues/releases/testes externos, cobertura brasileira por campo/temporada, revisão completa de licenças de dados, custos/regras por casa e avaliação preditiva/econômica admissível. O harness teve limitações de isolamento e um desvio de timeout documentados; não se certifica isolamento de sistema operacional. Os resultados entregues sustentam decisões de engenharia, com esses limites, e não uma conclusão de rentabilidade.
