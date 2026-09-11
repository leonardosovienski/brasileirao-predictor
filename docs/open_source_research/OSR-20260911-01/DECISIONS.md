# Decisões — OSR-20260911-01

Esta rodada recomenda mudanças, mas não integra código. Ação e estado são separados: VALIDATE pode terminar com falha de referência; RESEARCH pode estar bloqueado sem hipótese refutada. Gates continuam superiores ao ranking.

| ID | Ação | Estado da rodada | Decisão e condição |
| --- | --- | --- | --- |
| K01 | IMPROVE | BENCHMARKED_ENGINEERING | Adicionar erro de truncamento explícito; custo baixo por usar a mesma família NB/DC. Gate: SYNTHETIC_ELIGIBLE. Próximo N01 |
| K02 | VALIDATE | RESEARCH | Mutation tests determinísticos de revisões, ausência de relógio e suspensão, com recibos de exclusão. Gate: SYNTHETIC_ELIGIBLE. Próximo N03 |
| K03 | VALIDATE | BENCHMARKED_ENGINEERING | Conferir finitude, não negatividade, soma, domínio e fallback, sem alegar probabilidades verdadeiras. Gate: SYNTHETIC_ELIGIBLE. Próximo N02 |
| K04 | VALIDATE | RESEARCH | Fixar redução, classe, clipping e objetos entregues ao teste; empate exige dados novos para diagnóstico estatístico. Gate: SYNTHETIC_ELIGIBLE. Próximo N02 |
| K05 | KEEP | BENCHMARKED_ENGINEERING | Preservar caminho validado; especificar extensão somente se mercado nominal demandar. Gate: SYNTHETIC_ELIGIBLE. Próximo N02 |
| K06 | RESEARCH | RESEARCH | Comparar baseline simples e atual, treinados só em coorte nova admissível; não portar parâmetros estrangeiros. Gate: DATA_CONDITIONAL. Próximo N05 |
| K07 | AUGMENT | RESEARCH | Priorizar calendário/descanso sobre tracking caro; separar contexto, xG observado e expectativa pré-jogo. Gate: DATA_CONDITIONAL. Próximo N05 |
| K08 | AUGMENT | RESEARCH | Tabela de elegibilidade por fornecedor/campo antes de coletar; UNKNOWN bloqueia claim dependente. Gate: METADATA_ELIGIBLE. Próximo N03 |
| K09 | RESEARCH | RESEARCH | Um contrato espacial sintético pode eliminar erros antes de comprar/adotar dados; ganho pré-jogo não testado. Gate: SYNTHETIC_ONLY_DATA_BLOCKED. Próximo N04 |
| K10 | KEEP | RESEARCH | Guardar dados, transformações, tentativas e exclusões em manifesto versionado; não criar outro kernel. Gate: DOCUMENTATION_ELIGIBLE. Próximo N03 |
| K11 | RESEARCH | RESEARCH | Primeiro baseline causal linear ou gols; no máximo um challenger com orçamento igual e tuning dentro do treino. Gate: DATA_CONDITIONAL. Próximo N05 |
| K12 | RESEARCH | RESEARCH | Hipótese: contexto/força acrescenta informação não capturada na odd contemporânea. Persistência e executabilidade UNKNOWN. Gate: BLOCKED_DATA_PROTOCOL. Próximo N05 |


## Decisões concretas

- **Priorizar K01/N01:** diagnóstico de cauda tem problema reproduzido e teste barato. Não mudar a família do modelo para resolver truncamento de suporte.
- **Manter K03 e K05 nos domínios testados:** o local já lida com stress de margem e caixa. Bibliotecas externas entram como contraste com checks próprios, não como troca automática.
- **Completar K02/K08 antes de comparar eficácia:** clocks e identidade são condição de admissibilidade. Código que exige um timestamp declarado não demonstra que ele veio de fonte observada.
- **Aprofundar K04 com convenção fixa:** Brier multiclasses, empate e DM não podem ser comparados por nome de função. A estatística de empate real exige labels novos permitidos.
- **Adiar adoção de eventos/tracking:** K09 tem utilidade esportiva plausível; validar coordenadas sintéticas primeiro. socceraction 1.5.3 não pode ser colocado no lock atual sem quebrar seu intervalo Python.
- **Não abrir novo concurso de redes/boosting:** K11 agrupa alternativas redundantes. Um challenger só depois de baseline causal, orçamento igual e nova coorte admissível.
- **K12 sem score econômico:** seleção de oportunidade exige preço contemporâneo nominal, custo, caixa e aceitação. Não se inferiu ganho incremental do modelo esportivo sobre odds.

## O que rejeitamos nesta rodada

REJECT: substituição ampla do runtime por pacote externo; nova dependência crítica worldfootballR arquivada; assumir xG brasileiro de fonte que não comprovou cobertura; promover closing/máxima anônima a preço aceito; preencher `known_at` artificial; repetir estudos BE sob outro nome; instalar tracking ou MLflow sem necessidade; operar live/lay sem contrato; usar popularidade, hit rate, concordância de engine ou PnL sintético como alpha.

Essas decisões rejeitam **ações ou inferências**, não provam que todo método associado é inútil. Modelos bayesianos, xT/VAEP, eventos, mercado residual e contexto continuam hipóteses condicionadas. Nenhuma capitalização foi autorizada.

## Vantagens verificadas e limites

T02 mostra duas entradas em que a função local retorna enquanto a referência externa falha; T03 mostra coerência de pagamentos/caixa no fixture. São vantagens delimitadas de robustez em casos específicos, não superioridade geral. A inspeção também encontrou contratos locais de relógio e identidade, mas sem provar autenticidade dos dados.

**NO_VERIFIED_ADVANTAGE preditiva/econômica.** Não há percentual de código substituível ou trabalho desperdiçado: não foi construído denominador para isso. Reutilização recomendada é adapter de validação, contrato espacial e referência metodológica; não outro kernel Python/Redis/.NET.

## Frentes cobertas e lacunas

| Frente do mandato | Cobertura nesta rodada | Pendente material |
| --- | --- | --- |
| Dados | K02/K08; 14 contratos de fonte; índices/documentação | cobertura por temporada/campo; custos/licenças e snapshots reais |
| Contexto | K07; código de descanso/viagem/técnico e CBF | arbitragem, clima previsto, gramado e boletins históricos não auditados |
| Desempenho | K09/K07; xT, VAEP, xG, pressão, sincronização | npxG/bola parada/posse/redes completos e dados brasileiros |
| Ratings e modelos | K06/K11; NB/DC/Elo, pooling/Pi, boosting em triagem | ajustes, calibração e transferência de parâmetros não executados |
| Filtros/ranking | K02/K03/K12; temporalidade, frescor e domínio | coverage-risk, decisões e exclusões reais não medidas |
| Mercados | K01/K05; 1X2/BTTS/DNB/totais/AH | períodos, team totals especializados, cartões/escanteios/jogadores sem contratos próprios |
| Odds | K03/K08; de-vig sintético e alerta de feed | aceitação, custos, liquidez, entidades e regras nominais |
| Incerteza/avaliação | K04; convenções e proposta pareada | IC, calibração empates, multiplicidade com dados reais |
| Economia/risco | K05/K12; caixa simbólico e gates | PnL real, yield, drawdown, capital e fills não avaliados |
| Ciência/ferramentas | registro/hash/protocolo, K09/K10 | sweep integral issues/releases e independente revisão humana |


O resultado é uma primeira rodada **utilizável, de cobertura parcial explicitada**. Os testes permitidos foram concluídos; não há promessa de trabalho assíncrono. Estudos condicionados e integração precisam de seus próximos gates.
