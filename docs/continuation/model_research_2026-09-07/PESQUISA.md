# Modelos comparáveis e de onde poderia vir o lucro

Pesquisa de fontes primárias em 07/09/2026, São Paulo (08/09 UTC). Foram examinados artigos, documentação oficial e código público. Não reproduzi os backtests externos. Nenhuma hipótese do projeto foi reajustada ou promovida.

**Há resultados positivos publicados, mas predominam simulações. O mecanismo recorrente combina uma estimativa útil de probabilidade com um preço favorável e disponível. Ter um modelo sofisticado ou acertar muitos vencedores, isoladamente, não demonstra lucro.**

## Casos comparáveis

### 1. GAP — modelo diretamente voltado a over/under 2,5

Wheatcroft (2020) constrói ratings dinâmicos de ataque/defesa, por mando, usando chutes e escanteios. Uma regressão logística os combina com informação das odds para prever OU2,5. O artigo relata cerca de **0,8% por aposta** supondo acesso às maiores cotações BetBrain; com preços médios, as estratégias perderam, inclusive Kelly. É um resultado retrospectivo. A lição para o Brasileirão é investigar volume ofensivo e preço de execução juntos; a margem observada é pequena e sua sobrevivência aos custos precisa ser demonstrada. [Artigo aceito, LSE](https://researchonline.lse.ac.uk/103712/1/Predict_total_goals_LSE.pdf), [publicação](https://www.sciencedirect.com/science/article/pii/S0169207019302559).

### 2. xG + Skellam + calibração

Wilkens (2026) transforma xG recente em probabilidades de vitória/empate/derrota e aplica calibração isotônica com janelas anteriores. Relata **567 apostas simuladas, +53,85u e ROI 9,5%** nas odds médias; os mesmos sinais renderiam **14,9%** nas melhores odds. O braço visitante perdeu 16,6%. O autor reconhece custos, slippage, limites e liquidez não modelados, classificando os retornos como limite superior; a instabilidade temporal permanece. A hipótese útil é que chances criadas e calibração podem ajudar, mas não basta copiar os parâmetros da Bundesliga. [Artigo completo, tabelas 3–4 e discussão](https://journals.sagepub.com/doi/10.1177/22150218261416681).

### 3. Probabilidade pelo consenso; aposta na casa divergente

Kaunitz, Zhong e Kreiner (2017) usam informação agregada das casas para localizar cotações favoráveis. Relatam **265 apostas reais e US$957,50 de lucro**, de abril a setembro de 2016, e encerramento após limitações das contas. Há uma discrepância: os 8,5% declarados não reconciliam com 265 apostas constantes de US$50; essa divisão dá 7,23%. O estudo também observou preços do painel já alterados na casa. É experiência real declarada, sem auditoria independente nesta pesquisa, amostra curta e execução limitada. [Preprint, texto e tabela 1](https://arxiv.org/pdf/1710.02824).

### 4. Modelo ao vivo ancorado no preço pré-jogo

Clegg, Song e Cartlidge (2026) ajustam um modelo Weibull às odds iniciais e incorporam eventos durante a partida. Relatam **4,5% com Kelly em 17.458 apostas simuladas sobre 140 jogos**, descontando 2% do lucro líquido por jogo. O braço de stake fixa perdeu **3,4%**. As duas estratégias também diferem na seleção, portanto isso não demonstra que Kelly transforma a mesma carteira perdedora em vencedora. O preço é uma aproximação baseada na última negociação dois minutos depois; não há comprovação de preenchimento. As milhares de apostas compartilham só 140 resultados de partidas. É pista preliminar, dependente de dados e execução ao vivo. [Preprint, seções 3 e 10](https://arxiv.org/html/2605.16066v1).

### 5. Casos negativos que ajudam a explicar nosso resultado

Pitcan (2026), preprint recente, compara Dixon–Coles e mercado na Serie A: **2.660 jogos**, sete temporadas de teste. O mercado apresenta RPS 0,1905 contra 0,1972 do modelo e recebe todo o peso na combinação. A variante de chutes também não agrega informação ao mercado. Isso é próximo do nosso peso zero em 1X2/OU, mas mede informação preditiva, não ROI. [Texto completo](https://arxiv.org/html/2608.11505v1).

Winkelmann e coautores (2024) examinam 25.564 jogos de cinco ligas. Anomalias aparecem em recortes, mas não persistem sistematicamente; simulações mostram que resultados parecidos podem surgir sem ineficiência explorável. É motivo para preservar também as tentativas negativas. [Journal of Sports Economics](https://journals.sagepub.com/doi/abs/10.1177/15270025231204997).

Outro exemplo de leitura cuidadosa: Mendes-Neves e coautores (2025) combinam Elo e distribuições de quantidade/qualidade de chutes. A tabela 3 mostra **retorno de 1,1%**, ou **6,7 pontos percentuais acima** de um baseline de −5,6%; não é ROI de 6,7%. A outra estratégia perde 0,8%. [Artigo, tabela 3](https://arxiv.org/html/2501.05873v1).

## O que os projetos abertos ensinam

O [penaltyblog](https://penaltyblog.readthedocs.io/en/master/models/overview.html) implementa Poisson, Dixon–Coles, binomial negativa, Weibull/copula e alternativas bayesianas. É uma referência para comparação e incerteza; a documentação examinada não demonstra lucro auditado da biblioteca. Nosso projeto já utiliza uma família de modelos comparável.

O [value-bet-model](https://github.com/mperi1208/value-bet-model) declara +4,86% em 20.676 apostas retrospectivas usando odds máximas contra uma referência Pinnacle sem margem. Seu próprio [AUDIT.md](https://raw.githubusercontent.com/mperi1208/value-bet-model/main/AUDIT.md) registra que, corrigidos vazamento na calibração e seleção posterior de ligas, o ML anterior perdeu 6,7% nas odds médias. Os +4,86% pertencem a outra estratégia e não comprovam execução. A leitura do [código](https://raw.githubusercontent.com/mperi1208/value-bet-model/main/src/value_bet_sharp.py) identificou liquidação sem fricções e bootstrap por aposta; minha inferência é que o intervalo publicado não incorpora explicitamente dependência entre apostas do mesmo jogo ou a exploração anterior. O painel histórico máximo exige acesso a várias casas.

O [value-betting-scanner](https://github.com/zakariae-boui/value-betting-scanner) declara +10,8% em 224 apostas de **paper**, sem dinheiro real. No [CSV público](https://raw.githubusercontent.com/zakariae-boui/value-betting-scanner/main/paper_bets.csv), os registros 211 e 218 têm captura às 20h21 UTC, após o início registrado às 19h, e duas seleções da mesma partida. O histórico não representa integralmente a regra atual de uma aposta pré-jogo por evento. Seu [cálculo de CLV](https://raw.githubusercontent.com/zakariae-boui/value-betting-scanner/main/ledger.py) usa odd de fechamento com margem; o outro projeto usa probabilidade de fechamento sem margem. Seus percentuais de CLV não são diretamente comparáveis. Esses achados limitam a evidência; não estabelecem intenção de enganar.

## Como o mecanismo econômico funciona

Se a probabilidade real fosse 50%, uma unidade em odd 1,90 teria expectativa bruta de **−0,05u**; em odd 2,10, **+0,05u**. Com o custo adicional de 0,02u do nosso replay, seriam −0,07u e +0,03u. A mesma previsão pode ser ruim ou boa economicamente conforme o preço. Esse é um exemplo aritmético, não estimativa para uma partida.

Existem três fontes conceituais de vantagem: informação ainda ausente do preço; interpretação melhor da informação existente; ou acesso a um preço favorável em relação a uma boa referência. Toda hipótese depende de disponibilidade e custos. Na [documentação Betfair](https://support.betfair.com/app/answers/detail/a_id/401/), ordens podem ser parcialmente correspondidas ou não encontrar contraparte. A [Smarkets](https://help.smarkets.com/hc/en-gb/articles/212654665-Smarkets-commission-FAQ) publica modelos de comissão distintos conforme a categoria. Nosso custo fixo de 2% por aposta não representa automaticamente a tarifa de uma exchange.

A [Starlizard](https://starlizard.com/) descreve dados, modelagem e execução em tempo real, mas sua página não publica ROI auditado. Já a [Sportradar, relatório anual 2025](https://investors.sportradar.com/static-files/ba7e554b-0673-4ecd-985e-c7fa77098bf3), documenta receita com dados, odds e serviços a operadores. Ganhar vendendo tecnologia é um negócio diferente de demonstrar lucro apostando com ela.

Um problema atual de dados merece atenção: a própria [Football-Data](https://football-data.co.uk/data.php) informa que suas cotações Pinnacle estão sistematicamente desatualizadas desde 23/07/2025. Isso se refere à distribuição desse provedor, não a todos os feeds Pinnacle. Não atribuo esse problema automaticamente aos dados Sofascore do projeto. Comparar preços com horários incompatíveis pode fabricar uma oportunidade aparente.

## Aplicação ao brasileirao-predictor

No replay preservado, a calibração deu peso zero ao modelo em 1X2/OU e BTTS continuou pior que o mercado. Usar a probabilidade sem margem derivada **da mesma cotação** não cria edge positivo quando o mercado tem margem positiva: se `q_i=(1/odd_i)/S` e `S>=1`, então `q_i*odd_i<=1`.

Usar uma referência independente e comparar com outra casa é uma hipótese distinta: `q_referencia*odd_ofertada-1-custo`. Ela pode ser positiva mesmo sem vencer o consenso na previsão do placar; só terá valor se a referência for adequada e o preço estiver disponível. Isso não reabre automaticamente a pesquisa encerrada de prever movimento futuro de odds.

Minha priorização, como inferência da pesquisa:

1. **Primeiro, medir preço e disponibilidade.** Casa, mercado/linha, horário de observação, estado ativo, atraso, preço de referência e preço ofertado precisam ser comparáveis. Registrar rejeições e preços desaparecidos. CLV sem margem pode ajudar como diagnóstico, junto com resultado líquido; não é verdade certificada nem lucro.
2. **Depois, um candidato simples de forças dinâmicas com xG ou GAP.** Comparar com mercado e modelo atual, com atualização cronológica explicitamente definida e calibração correspondente. Atualizar o Elo do replay congelado criaria outro candidato; não é conserto retroativo.
3. **Informação de escalação só se acrescentar algo ao preço disponível.** Uma mudança no time pode ter sido precificada antes de chegar ao nosso feed. A melhoria do pipeline permite transportar a informação corretamente; não prova que ela chega a tempo ou possui valor.
4. **Adiar um sistema ao vivo até haver dados e execução mensuráveis.** O estudo de 140 jogos não justifica assumir que um serviço local com odds agregadas reproduziria seu resultado.

Antes de avaliar nova hipótese: fixar mecanismo, amostra admissível, horários, comparadores, custo, critérios de seleção e parada. Usar dados futuros ou investigação explicitamente exploratória, isolada; 2025 e 2026 já vistos não viram holdout novo. Não escolher os recortes positivos dos artigos como filtros do nosso próximo teste.

Nesta etapa houve apenas pesquisa e leitura de código público. Nenhum modelo externo foi instalado/executado, nenhuma coleta operacional ou agenda foi alterada, e não houve aposta, conta, compra ou promoção de candidato. O resultado econômico anterior permanece preservado.
