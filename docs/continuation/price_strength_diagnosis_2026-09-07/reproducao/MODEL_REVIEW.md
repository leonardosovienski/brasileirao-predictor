# Revisão técnica do candidato rolling xG

Revisão em 08/09/2026 UTC, restrita a código, contratos, fixtures sintéticas e incidência de registros no histórico já autorizado. Não houve novo backtest econômico, consulta ao banco operacional, inspeção de coortes protegidas ou ajuste de parâmetros.

**Conclusão:** há um bug mecânico real na validação de revisões, agora corrigido. As fórmulas de mando, médias e probabilidades implementam o desenho declarado. A contração das forças, o uso de médias sem ajuste pela força dos adversários e a calibração de apenas duas taxas são limitações de arquitetura; alterá-las cria outro candidato. Há também uma anomalia de proveniência: todos os xG de 2021 são pares zero, mas a origem desses zeros não foi comprovada. Essa anomalia alcança dez fixtures de 2025 e nenhuma janela da calibração de 2024; não explica a piora geral do calibrado.

## Contratos e arquivos examinados

- `docs/continuation/PROMPT_MELHORIA_LUCRO.md`, `docs/continuation/RETOMADA.md` e os checkpoints atuais de `HANDOFF.md`.
- `contracts/season-2026-turn-split-paper.json`: preservar estudos encerrados, coortes, divisões, capital bloqueado e ausência de fit em 2026.
- `brasileirao_predictor/research/pit_features/contracts.py`: o scaffold anterior continua bloqueado por seu gate; esta revisão não o ativa.
- `brasileirao_predictor/research/price_strength/dynamic_xg.py` e seus testes.
- `work/price_strength_evaluation/conditional_model.py`: adaptador encerrado, sem modificações nesta revisão.
- Código de `ingest_sofascore.py`, `db.py`, `data/missingness_audit.py` e preparação do snapshot histórico; somente leitura para examinar proveniência.

Os defaults, janelas, priors, configuração e fórmulas do candidato não foram modificados. As previsões e os resultados encerrados permanecem como publicados. O fingerprint da configuração não muda com a correção de validação; o hash do código muda, como deve ocorrer em uma nova revisão de engenharia.

## Bug corrigido: conflito ocultado pela ordem das revisões

Antes da correção, `_visible` guardava somente a última revisão de cada partida. Considere três registros visíveis do mesmo jogo:

1. A: `available_at=t1`, `home_xg=1.8`.
2. B: `available_at=t1`, `home_xg=5.0`, contradiz A no mesmo instante.
3. C: `available_at=t2>t1`, `home_xg=4.0`.

Se A e B eram processados juntos antes de C, o conflito era recusado. Se C já fosse o último registro guardado, A e B eram comparados apenas com C: os horários diferiam e o conflito antigo passava. O mesmo conjunto de dados podia ser aceito ou rejeitado conforme sua ordem.

A regressão sintética enumerou as seis permutações: **quatro falharam antes do reparo**, por ausência da exceção esperada. A correção mantém um índice de todas as revisões visíveis por `(match_id, available_at)` para validar conflitos independentemente da seleção da última versão. Continua filtrando registros futuros e o próprio alvo antes de validar; duplicatas idênticas continuam toleradas.

Foram alterados somente `dynamic_xg.py` e `tests/test_price_strength_dynamic_xg.py` no pacote atual, após autorização específica. Não houve alteração em médias, probabilidades, ajuste, configuração ou candidato arquivado. O adaptador condicional já rejeita qualquer duplicata e não chama `_visible`: esse reparo não modifica a execução histórica encerrada.

Validação isolada:

- Regressão vermelha: 4 falhas e 2 passagens nas permutações de conflito.
- Após correção: 69 testes passaram em `test_price_strength_dynamic_xg.py` e `test_price_strength_study.py`.
- Ruff e verificação de formato passaram para os dois arquivos.
- Mais quatro testes sintéticos em `work/price_strength_diagnosis/test_model_review.py` passaram, demonstrando as propriedades estruturais abaixo.

Recibos em `work/validation/`: `price_strength_revision_conflict_red`, `price_strength_revision_conflict_green`, `price_strength_revision_lint`, `price_strength_revision_format` e `price_strength_model_structure_synthetic`, com arquivos `.json` e `.log`. O runner usa checkout descartável, ambiente por allowlist, bloqueio de acesso ao repositório operacional e bloqueio de conexões Python externas.

## xG zero: anomalia real, causa original não demonstrada

Fonte autorizada: backup `work/selection_reanalysis/historical_input.json`, idêntico a `data/research/season_2026_turn_split/historical_2021_2025.json`.

SHA-256: `14153f7cbb348e9eef22a8e1c438757b1ef482951e2576d4a8381d7928e8e142`.

| Ano | Jogos | Ambos xG zero | Ambos positivos | Algum xG ausente |
| --- | ---: | ---: | ---: | ---: |
| 2021 | 380 | 380 | 0 | 0 |
| 2022 | 380 | 0 | 380 | 0 |
| 2023 | 380 | 0 | 380 | 0 |
| 2024 | 380 | 0 | 379 | 1 |
| 2025 | 380 | 0 | 380 | 0 |

Não há pares com exatamente um lado zero. As contagens examinam somente presença e valores de xG, sem odds, acertos ou retorno. O padrão anual é forte indício de falta de cobertura ou proveniência inadequada, mas não identifica o mecanismo que gerou os zeros.

A cadeia de código examinada não comprova imputação de ausência para zero:

- `prepare_input.py` seleciona `s.home_xg` e `s.away_xg` sem `COALESCE` e os copia para `result`.
- O parser `parse_xg` examinado retorna `(None, None)` quando não encontra a estatística; o ramo sem coleta também usa `None`.
- O schema declara colunas `REAL`, sem `DEFAULT 0`, e o upsert copia os valores recebidos.
- O relatório legado de missingness conta `IS NOT NULL` como válido/observado. Isso mede presença; não comprova proveniência nem cobertura semântica. Correção desse relatório é trabalho separado do root.

Não foram abertos payloads privados adicionais para atribuir a origem histórica dos zeros. A classificação defensável é `ZERO_PAIR_AMBIGUOUS`, não `MISSING_CONFIRMED`. Uma quarentena uniforme pode impedir uso de pares ambíguos, mantendo os bytes originais e a razão de exclusão. Ela não deve transformar zeros em `null` factual, nem depender de placares, odds, acertos ou perdas. Zero individual também pode ser um valor legítimo de xG; o parser não deve convertê-lo globalmente em ausência.

### Incidência antes de qualquer novo score

A incidência foi calculada por IDs e janelas, sem novas previsões probabilísticas ou métricas econômicas:

- Em `outputs/TESTE_XG_REAL/forecasts.json`, **10 das 380 fixtures de 2025** têm algum ID de 2021 em `raw.history_ids`; são dez IDs históricos distintos de 2021.
- **Zero IDs de 2021** aparecem em `calibrated.calibration_match_ids` das previsões congeladas.
- Reconstrução somente das janelas dos 380 alvos de 2024, com atraso assumido de 48h e decisão uma hora antes, encontra **zero alvos com histórico de 2021**. Dos 380, 368 satisfazem o mínimo de três partidas por mando, sem consultar seus gols para essa contagem.

Fixtures de 2025 com incidência: `13473341`, `13473357`, `13473359`, `13473377`, `13473380`, `13473397`, `13473398`, `13473417`, `13473426`, `13473438`.

Esses números medem influência potencial, não magnitude ou direção de melhora. A quarentena pode mudar elegibilidade ou intensidades nesse subconjunto, mas não corrige as escalas ajustadas em 2024, cujas entradas não contêm os zeros de 2021. O próprio xG de um alvo não deve decidir sua elegibilidade de previsão, avaliação ou calibração: apenas o histórico utilizado precisa passar pela política de qualidade.

## O que as fórmulas efetivamente fazem

### Forças e encolhimento

Para uma série no mando pertinente, a média é:

```text
w_i = 0.5 ** (idade_em_dias_i / half_life_days)
média = (prior_weight * prior + soma(w_i * xG_i)) / (prior_weight + soma(w_i))
lambda_casa = (ataque_da_casa + xG_cedido_pelo_visitante_fora) / 2
lambda_fora = (ataque_do_visitante_fora + xG_cedido_pela_casa) / 2
```

Com cinco partidas, a soma dos pesos nunca excede cinco. O prior de peso dois limita a contribuição dos dados a no máximo `5/7` de cada média. Se apenas a série de ataque da casa sobe em uma unidade, mantendo sua defesa adversária fixa, a resposta da intensidade é `0.5 * S/(2+S)`, menor que `5/14 ≈ 0.357`. O teste sintético confirma essa atenuação.

Isso não é dupla contagem acidental de um prior: é consequência da regularização seguida da média aritmética especificada. Pode comprimir diferenças entre times. Trocar a média por soma de efeitos ou produto de razões muda a hipótese do modelo e exige nova versão; não há prova de que uma dessas mudanças melhora os dados reais.

### Adversários, mando e sazonalidade

Os índices de mando estão corretos. O ataque da casa é confrontado com o xG da casa nos jogos anteriores do atual visitante, isto é, o que o visitante sofreu fora. O cálculo do visitante usa a relação inversa. Teste com adversários e mandos distintos já verificou equivalência do adaptador com o candidato; não encontrei troca de colunas ou de sinal.

O modelo não estima a força dos adversários históricos. Trocar seus nomes sem alterar xG, horários e o mando do time analisado deixa a previsão idêntica; o teste sintético demonstra essa invariância. Portanto diferenças de dificuldade do calendário podem ser confundidas com força de ataque/defesa.

Não há estado próprio por temporada, competição ou elenco, nem parâmetro de campo neutro no contrato estrito. O adaptador condicional ignora esses metadados do snapshot. Decaimento temporal aproxima as médias dos priors após um hiato, mas não verifica mudanças de elenco, promoção/rebaixamento ou comparabilidade da competição. Essa informação deve ser restringida no universo de entrada ou modelada em outro candidato.

O mínimo de amostra conta partidas, não peso efetivo. Um time pode continuar elegível com cinco partidas extremamente antigas cujos pesos praticamente desapareceram. O teste sintético de um hiato de cem anos retorna cinco partidas e lambdas iguais aos priors até tolerância numérica. Isso demonstra uma limitação de elegibilidade, não um caso real examinado. Introduzir peso mínimo ou idade máxima constitui uma nova política de candidato, a registrar antes de avaliação; não deve ser escolhido para favorecer as dez fixtures afetadas.

### Probabilidades

`_probabilities` aplica Poisson independente para os gols de cada time. Skellam fornece corretamente casa/empate/fora; a Poisson da soma fornece OU2,5; o produto das probabilidades de cada time marcar fornece BTTS. Todas as distribuições são normalizadas e o cálculo analítico evita descarte de cauda de uma grade pequena.

O teste independente soma uma grade Poisson de 40×40 em um exemplo sintético e confirma as três probabilidades 1X2 até `1e-12`. Não encontrei bug de orientação da Skellam, normalização ou limiar 2,5.

Essas fórmulas impõem independência entre os gols e igualdade entre média e variância de cada Poisson. Correlação, excesso de dispersão ou excesso de certos placares não podem ser corrigidos só pela normalização. Adicionar Dixon–Coles, bivariada ou mistura seria mudança arquitetural, sem melhoria garantida.

### Calibração: duas taxas, não uma otimização dos mercados

Cada escala é `(soma_gols + exposição_prévia)/(soma_lambdas + exposição_prévia)`. Isso corresponde ao ótimo de um objetivo Poisson para uma escala comum, com regularização que puxa a escala para um. O código aplica exatamente essa regra e respeita os cortes temporais declarados.

O objetivo não é minimizar Brier ou log loss de 1X2, OU2,5 ou BTTS, nem retorno. Corrigir uma média agregada de gols pode prejudicar a distribuição de probabilidades de um mercado. As duas escalas também não corrigem uma relação errada entre força e intensidade, dificuldade de calendário ou diferenças de erro entre grupos. Elas pressupõem que a correção estimada em 2024 se transfira para 2025.

`training_end` é a fronteira de alvos de calibração, não um congelamento das forças. Partidas anteriores da própria calibração atualizam as médias quando passam pelo corte temporal. Não há vazamento nesse mecanismo por si só. No adaptador de replay, o corte usa a hipótese declarada de 48h; não fornece prova de disponibilidade histórica e não deve ser convertido em um `available_at` observado.

## Decisão recomendada

1. Manter a correção factual de `_visible`, já testada, sem alterar probabilidades para históricos válidos e sem revisões contraditórias.
2. Corrigir a descrição de cobertura e acrescentar uma política de qualidade de entrada separada, com pares zero ambíguos identificados, proveniência e incidência preservadas. Não atribuir o desempenho agregado a essa pequena incidência.
3. Preservar o estudo encerrado e seu resultado. Qualquer análise de impacto da quarentena precisa de plano próprio, candidato/defaults fixos, universo completo e comparação pareada que revele abstinências.
4. Se prosseguir em modelagem, declarar um candidato separado que explicite ajuste por adversário, estado temporal, mando/campo neutro e objetivo de calibração. Não apresentar mudança de média, prior, janela, idade mínima, distribuição ou função de perda como conserto de um erro já provado.

Esta revisão sustenta uma melhoria de engenharia e um problema de qualidade/proveniência a tratar. Não demonstra que uma nova arquitetura ou a quarentena tornará o sistema lucrativo.
