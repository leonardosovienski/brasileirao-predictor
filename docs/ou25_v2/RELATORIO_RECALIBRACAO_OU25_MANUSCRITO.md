# Recalibração OU2.5 orientada pelo manuscrito

Data: 2026-08-27

## Veredito

**NO-GO. O projeto não foi “calibrado” para apostar; foi calibrado para não
emitir recomendação econômica com a evidência atual.** Capital continua
desabilitado e a força máxima permanece 40/100.

Foram avaliadas nove células fechadas:

- `retrain_every`: 10, 20 e 100 jogos;
- bloco temporal externo: 38, 95 e 190 jogos;
- 1.620 filtros por fold;
- 77.760 avaliações de combinação registradas ao todo;
- replay externo inteiramente em 2023, após prefixo de desenvolvimento;
- odds OU2.5 retrospectivas agregadas de 16–25 bookmakers;
- correção de Holm dentro de cada fold;
- escolha por limite inferior do ROI, estabilidade e amostra, nunca pelo maior
  ROI isolado.

## Resultado econômico

O baseline “apostar sempre no maior EV do modelo” perdeu em todas as cadências:

| Refit | ROI | Limite inferior IC95 |
|---:|---:|---:|
| 10 | −8,95% | −19,85% |
| 20 | −8,52% | −19,36% |
| 100 | −9,59% | −20,51% |

Os filtros aninhados produziram entre **zero e 12 picks** por célula. Resultados
positivos apareceram somente com `n=3`, um lado e uma faixa de odd; são
inutilizáveis. A célula de maior amostra (`n=12`) perdeu 17,33%, com limite
inferior de −70,09%. A variação entre tamanho de bloco e cadência confirma
instabilidade, não edge.

O preço de mercado de-vigado teve Brier `0,243928`. O modelo ficou pior nas três
cadências (`0,247790` a `0,248359`). Portanto o mercado contém mais informação
probabilística no mesmo painel.

## Aplicação do manuscrito “o que precisamos para prever”

- identidade, kickoff e corte temporal: preservados pelo evaluator prequential;
- jogos simultâneos: guardados por kickoff estritamente anterior;
- probabilidades antes de picks: preservadas;
- coverage e `n`: reportados em todas as células;
- accuracy: não usada para promoção;
- 2024–2026: tratados como observados/contaminados e não usados nesta matriz;
- ensemble xG: permaneceu desligado, conforme H12;
- escalação, VORP e estatísticas: não injetados, pois não há transformação PIT
  validada no painel;
- CLV: indisponível, porque a fonte histórica não identifica casa e horário de
  captura; não foi falsificado;
- capital: `false` em todos os artefatos.

## Interpretação

Continuar tentando thresholds no mesmo painel seria p-hacking. Com 77.760
leituras já contabilizadas, qualquer novo vencedor retrospectivo precisa ser
tratado como contaminado. O candidato congelado correto é **NO_BET** até uma
coorte prospectiva A1 com snapshots executáveis, casa nomeada e fechamento da
mesma casa.

O arquivo `ou25_factorial_summary.json` contém as nove células, baselines,
contagens e hashes dos resultados integrais.
