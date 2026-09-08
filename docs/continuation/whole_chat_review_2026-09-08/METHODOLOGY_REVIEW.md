# Revisão adversarial científica e de comunicação

Revisão em 08/09/2026 UTC. Escopo: pesquisa de modelos, implementação offline, primeiro teste de 2025, diagnóstico e tentativa de correção. Foram lidos os quatro relatórios finais solicitados e a documentação/metodologia examinada nas etapas anteriores. Reabri fontes primárias selecionadas para conferir alegações centrais; não reproduzi os backtests externos. Nenhum novo backtest, ajuste, banco ou coorte foi acessado nesta revisão. Os relatórios e estudos permanecem intactos.

**Resposta direta: eu manteria os reparos de engenharia e a publicação honesta dos resultados, mas não repetiria a mesma ordem de trabalho.** A verificação de viabilidade e qualidade dos dados deveria preceder a arquitetura completa e, obrigatoriamente, o primeiro replay real. Depois do resultado negativo de 2025, a correção era autorizada como investigação exploratória; ainda assim, ela não recuperou independência estatística nem demonstrou lucro. O maior mérito foi registrar isso sem promover o braço conveniente. O maior erro de processo foi detectar tarde a cobertura suspeita de xG que já estava nos insumos.

**1. A pesquisa sustenta mecanismos plausíveis; não sustenta expectativa de reproduzir o lucro de profissionais.**

O relatório de pesquisa fez distinções importantes e corretas: simulação versus aposta real declarada; retorno bruto versus líquido; odds médias versus máximas; serviços de dados versus lucro com apostas. Publicou casos negativos, problemas de execução e uma inconsistência aritmética de fonte. Não encontrei fabricação de lucro nesse relatório.

A rechecagem de Wilkens confirma os números citados de 567 apostas, +53,85u e 9,5% nas odds médias, com 14,9% nas máximas. Mas o artigo usa uma receita diferente: médias de três partidas por mando, interrupção do histórico entre fases/temporadas, calibração isotônica temporal e otimização de 900 combinações de limiares por classe e objetivo em janelas anteriores. Isso justifica explorar a família xG/Skellam, não valida nossa janela de cinco, decaimento de 90 dias, priors, média entre ataque/defesa ou calibração por duas taxas. A combinação local não foi uma reprodução desse artigo. A atribuição de liquidez a odds médias feita na própria fonte também é uma suposição, não prova de aceitação. [Wilkens, artigo completo, modelagem e tabelas 3–4](https://journals.sagepub.com/doi/10.1177/22150218261416681).

A rechecagem de Kaunitz confirma que os autores declaram 265 apostas reais, stake de US$50 e lucro de US$957,50, junto de retorno declarado de 8,5% que não concilia com esses valores. A ressalva publicada pelo projeto estava correta. O texto também relata odds já alteradas e limitações das contas. Esse caso não é um demonstrativo financeiro externo auditado nem prova de capacidade permanente de execução. [Kaunitz e coautores, páginas 13–15 e tabela 1](https://arxiv.org/pdf/1710.02824).

Clegg e coautores confirmam os 17.458 sinais/apostas simuladas em somente 140 jogos e as diferenças de seleção entre stake fixa e Kelly. O próprio artigo reconhece que o último preço negociado pode não ser executável e que relógios de fontes distintas não se alinham perfeitamente. O relatório fez bem em não transformar Kelly em conserto automático de uma carteira perdedora. [Clegg e coautores, seções 10–11](https://arxiv.org/html/2605.16066v1).

A página da Starlizard descreve dados, modelos e execução, mas não apresenta ROI auditado. Portanto podemos explicar mecanismos econômicos possíveis; não podemos afirmar a partir dela quanto a empresa lucra, qual parte vem do modelo ou se uma arquitetura pública é equivalente. Não encontrar esse demonstrativo não prova que a empresa não lucre. [Starlizard, descrição oficial](https://starlizard.com/). A documentação Betfair confirma que ofertas podem ficar sem correspondência ou apenas parcialmente correspondidas; isso sustenta a distinção entre cotação registrada e aposta executada. [Betfair, correspondência de ofertas](https://support.betfair.com/app/answers/detail/a_id/401/).

O PDF LSE do GAP não pôde ser reaberto pelo navegador desta revisão; não apresento seu número como rechecado agora. Tampouco repeti toda a inspeção dos repositórios externos. A conclusão sobre a pesquisa é uma revisão das alegações centrais e de seu uso, não certificação completa de cada fonte ou reprodução externa.

**O que faria novamente:** fontes primárias, resultados negativos, custos e execução no centro da explicação. **O que mudaria:** uma tabela explícita entre cada mecanismo publicado, os campos de dados que exige e o que realmente existe no projeto, antes de propor a implementação. O retorno de um artigo nunca serviria como taxa esperada para o Brasileirão.

**2. A engenharia foi útil, mas a ordem foi orientada demais pela solução.**

Construir um scanner offline com entrada explícita, timestamps, suspensão, consenso excluindo a ofertante e hashes foi uma resposta legítima ao pedido de implementação. A separação entre pesquisa e operação, os testes sintéticos e a recusa de inventar timestamps foram escolhas que manteria. O relatório limita expressamente a validação a dados sintéticos e preserva a pendência Redis/Compose; não anuncia prontidão geral de produção.

Ainda assim, a recomendação da pesquisa era medir preço e disponibilidade primeiro. A implementação cresceu antes de confirmar que havia observações reais admissíveis para exercitar seu principal mecanismo. No fim, a comparação entre casas não pôde ser avaliada. Isso não torna o código inútil, mas revela custo de oportunidade e limita quanto ele resolveu a pergunta econômica do usuário.

Eu teria iniciado com um inventário pequeno de campos, identidades, cobertura, relógios e exemplos de mensagens realmente disponíveis, sem abrir coortes protegidas. Manteria um protótipo sintético para fixar os contratos, mas só ampliaria a arquitetura depois dessa verificação. Os 141 ou 318 testes respondem a perguntas de comportamento de software; não substituem dados que permitam testar o mecanismo econômico.

**3. Aceitar o histórico de 2021 no primeiro replay foi a principal falha científica evitável.**

Uma temporada inteira com 380 pares xG (0,0) exigia investigação antes de esses registros serem tratados como histórico informativo. Contar não nulo como válido foi uma classificação inadequada. A inspeção de distribuição e cobertura por ano/mando deveria ter precedido o primeiro ajuste, mesmo com schema e números finitos válidos.

Isso não autoriza dizer que todo zero é faltante. O parser atual não prova a origem dos zeros antigos, e xG zero pode ser reportado legitimamente. O conserto posterior foi metodologicamente cuidadoso: distinguir presença de qualidade, tratar pares zero como ambíguos, preservar os valores e não escolher a exclusão pelo placar.

Também foi correto medir o alcance efetivo. Apenas dez previsões de 2025 usavam os IDs suspeitos; seis perderam elegibilidade e quatro tiveram alterações mínimas. Nenhuma entrada da calibração de 2024 dependia desses IDs, e nenhuma seleção no painel comum mudou pela quarentena isolada. Não cabe transformar esse defeito de dados em explicação abrangente do fracasso do modelo.

Eu não repetiria o replay sem essa auditoria prévia. A decisão correta teria sido registrar a origem desconhecida e fixar o tratamento antes da primeira métrica. O primeiro estudo permanece como resultado da receita e dos insumos então usados; não deve ser apagado, substituído silenciosamente ou apresentado como estimativa limpa da eficácia de xG em geral.

**4. O teste condicional foi bem delimitado, mas sua pergunta era mais estreita que “o modelo melhorou?”.**

O adaptador de 48 horas foi uma escolha defensável para um diagnóstico retrospectivo, pois não fabricou disponibilidade observada e não relaxou a CLI estrita. O teste usou o mesmo conjunto e custo para todos os braços, manteve calibração até 2024 e evitou o blend antigo que tinha aprendido em 2025. Esses controles eu manteria.

Ele responde ao desempenho daquela receita sob o atraso presumido e aquelas cotações retrospectivas. Não identifica isoladamente o efeito de xG, atualização temporal ou calibração; não testa disponibilidade histórica, casa, aceitação ou limite. O relatório reconhece essas restrições e distingue corretamente dados históricos reais de apostas efetivamente realizadas.

Os intervalos por 33 semanas são resumos descritivos úteis, mas semanas não são necessariamente blocos independentes: times, janelas móveis e condições da temporada se repetem entre semanas. A reamostragem não inclui a incerteza de escolha da arquitetura nem do ajuste de 2024. O relatório já limita a interpretação e não usa a inclusão de zero como prova de equivalência. Eu acrescentaria explicitamente a possível dependência entre semanas e evitaria dar destaque ao número de reamostragens como se ele resolvesse essas limitações.

**5. O diagnóstico foi mais sólido quando descreveu decisões do que quando sugeriu causas.**

Foi correto examinar vitórias e derrotas, preservar todos os mercados e mostrar os acertos abandonados. A concentração das perdas em visitantes e odds altas é real no conjunto selecionado. A decomposição das mudanças de seleção explica contabilmente a diferença entre as receitas.

Eu usaria formulações como “onde se concentraram as perdas” ou “sobreprevisão observada no conjunto selecionado”. O título “o que explica as perdas” é mais causal do que a evidência. Janela curta, redução à média, média de ataque/defesa e ausência de ajuste por adversário são características verificáveis; seu papel individual na deterioração não foi identificado por esse teste. O próprio texto reconhece isso, o que impede uma conclusão causal indevida, mas o título poderia ser mais preciso.

Também manteria a recusa de criar regras só para mandantes, empates ou under após encontrar recortes positivos. Uma vitória com probabilidade baixa não prova habilidade; uma derrota com probabilidade alta não prova defeito. A fonte metodológica utilizada sustenta avaliar a distribuição e comparar os mesmos eventos, não selecionar retrospectivamente os acertos. [Gneiting e Raftery, regras próprias e comparação de previsões](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf).

**6. A segunda receita não foi um novo holdout nem uma simples correção dos zeros.**

O novo pedido do usuário autorizava tentar corrigir. O plano foi congelado antes do novo ajuste, os pesos foram aprendidos somente em 2024 com entradas raw temporais, e todos os braços foram publicados. Não encontrei uso dos rótulos de 2025 no ajuste dos pesos. Essa é uma separação real e importante.

Mas a escolha de tentar essa combinação ocorreu depois de examinar erros e resultados de 2025. Logo, existe adaptação da hipótese ao ano de avaliação, mesmo sem ajuste numérico nele. Cada novo prompt não transforma o mesmo ano em teste independente. O hash prova quais bytes foram fixados; não prova que a hipótese foi escolhida sem conhecimento prévio.

A receita junta quarentena e substituição da calibração de taxas por blend com mercado. Este último mecanismo já existia em outra linhagem do projeto. Foi permitido como candidato exploratório diferente, mas não constitui descoberta nova de método ou resgate do estudo antigo. A leitura raw evitou o erro adicional de usar probabilidades calibradas nos próprios rótulos de 2024 como entrada para outro ajuste.

Eu não repetiria esse ciclo como fluxo padrão de descoberta de lucro. Como investigação pontual solicitada, ele produziu informação útil e foi encerrado honestamente. Para alegar generalização, outra tentativa sobre o mesmo ano continuaria insuficiente. Esta revisão não propõe novo candidato nem nova busca.

**7. A comunicação financeira final é honesta; a evidência de melhoria continua fraca e heterogênea.**

O novo saldo −23,373u é menos negativo que −65,850u do xG calibrado no painel comum, mas não é lucro. Contra o xG raw, o ganho líquido de 3,224u é inteiramente explicado pela economia de custos de 3,280u, com pequena piora bruta; o ROI piorou. O relatório incorporou esse fato e mostrou perdas evitadas e acertos removidos. Essa transparência eu manteria.

Em 1X2 o peso do xG foi zero: reproduzir o mercado melhora um modelo inferior, mas não demonstra informação adicional. Os mercados binários continuam piores que o mercado e BTTS piora ligeiramente contra o xG calibrado. A conclusão negativa/mista segue os números e o critério declarado. O painel original com abstenções preservadas evita esconder o efeito de excluir seis jogos.

Nenhum número publicado autoriza capital real, taxa de retorno futura ou equivalência com empresas profissionais. Também não demonstra que a atividade seja impossível em geral: apenas que estas receitas e estes dados não demonstraram a vantagem procurada.

**8. “Auditoria independente” precisa de qualificação explícita.**

Eu implementei a segunda aritmética em um subagente da mesma equipe, conhecendo o plano e partes do código original. Não importei os módulos de fit/seleção/liquidação para as contas, e essa separação ajudou a detectar divergências mecânicas. Ela é independência de implementação em parte da auditoria; não é independência institucional, auditoria externa, revisão cega, novo conjunto de dados ou validação científica independente.

Os números de verificações também não são tamanhos de amostra. Milhares de asserts sobre os mesmos eventos não fornecem milhares de observações independentes. Eu escreveria “verificação interna por implementação separada, com controles cruzados de aritmética e proveniência”. O relatório já diz que as contas não atestam disponibilidade/execução, mas deveria deixar clara a relação entre os auditores e a equipe produtora.

**O balanço da revisão.** Manteria isolamento operacional, contratos temporais estritos, fontes primárias, congelamento de cada execução, comparadores fortes, pareamento, custos explícitos, auditoria de acertos e erros e preservação de resultados negativos. Mudaria a sequência para dados e proveniência primeiro; qualificaria melhor “independente” e “explica”; trataria as receitas sucessivas em 2025 como uma única trajetória exploratória adaptativa; e reduziria a distância entre a literatura que motivou o trabalho e o mecanismo específico realmente implementado. O trabalho melhorou software e capacidade de diagnosticar. Não resolveu a demonstração de rentabilidade.
