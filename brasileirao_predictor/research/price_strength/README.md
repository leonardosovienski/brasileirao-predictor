# Pesquisa offline de preços e forças xG

## Complemento DC-20260909: admissibilidade e contabilidade

Três módulos puros e aditivos, sem chamadas de API ou banco:

- `historical_admission.py`: último estado antes de T−60, rejeição de estados
  conflitantes/inativos e validação dos clocks; timeline não ganha receipt histórico inventado.
- `live_capture_admission.py`: identidade e estados de bookmaker, mercado e
  seleção; receipt local não vira publicação do bookmaker ou fill garantido.
- `closing_scenario.py`: congela escolhas usando somente preços, depois
  liquida labels; reserva exposição diária e reconcilia principal, retornos e custos.

São usados pelos scripts isolados da
[rodada DC](../../../docs/continuation/data_completion_2026-09-09/REPRODUZIR.md).
Não ativam scanner operacional, capital ou coortes. O cenário closing não é
validação econômica e a fonte teve problema documentado na referência.
Os resultados anteriores abaixo mantêm seu escopo.

Estado local e caminhos: [ESTADO_ATUAL.md](../../../docs/ESTADO_ATUAL.md).
O diagnóstico puro `price_hurdle.py` foi acrescentado em 09/09/2026: calcula
o preço necessário para empatar sob custos explícitos e recusa transformar
odds agregadas sem proveniência em ofertas executáveis. A [rodada encerrada](../../../docs/continuation/price_feasibility_2026-09-09/RESULTADO.md)
e sua [reprodução](../../../docs/continuation/price_feasibility_2026-09-09/REPRODUZIR.md)
preservam os limites. O scanner, estudo xG e exemplos abaixo mantêm seus contratos.

Este pacote implementa uma linhagem independente de pesquisa: compara preços entre casas e produz previsões com médias móveis de xG por time e mando. Toda saída tem escopo `RESEARCH_ONLY`. Não coleta dados, envia apostas, dimensiona capital, altera o modelo operacional, promove candidatos, modifica coortes ou libera os gates do scaffold PIT legado.

A demonstração usa partidas, casas, preços e resultados **fabricados em 2030**. Serve para exercitar contratos e cronologia; seus números não são resultados financeiros nem evidência estatística de vantagem. Um replay exploratório também não constitui um novo holdout intocado.

## Executar a demonstração

Na raiz do repositório, com o ambiente Python do projeto ativado:

```powershell
python -m brasileirao_predictor.research.price_strength demo --output-dir .\work\price-strength-demo-001
```

O diretório de saída deve ser novo. A demonstração cria `protocol.json`, `history.jsonl`, `fixtures.jsonl`, `quotes.jsonl` e seu recibo; depois executa o estudo em `run/`. São 24 partidas sintéticas, das quais quatro são fixtures de avaliação. Esses arquivos são os exemplos completos e compatíveis com a implementação.

Para repetir o estudo com os mesmos arquivos explícitos e outra saída nova:

```powershell
python -m brasileirao_predictor.research.price_strength study --protocol .\work\price-strength-demo-001\protocol.json --history .\work\price-strength-demo-001\history.jsonl --fixtures .\work\price-strength-demo-001\fixtures.jsonl --quotes .\work\price-strength-demo-001\quotes.jsonl --output-dir .\work\price-strength-replay-001
```

O CLI não descobre bancos ou arquivos automaticamente. As entradas sob `data/` do repositório são recusadas; a saída não pode ser a raiz do repositório, estar sob `data/` ou `.git`, nem já existir. A implementação foi exercitada com fixtures sintéticas; estes exemplos não iniciam treino com dados reais.

## Comparar somente preços

Salve o objeto abaixo em um arquivo explícito, por exemplo `work/policy-synthetic.json`. Ele reproduz a política da demonstração:

```json
{
  "reference_books": ["synthetic_reference"],
  "max_age_seconds": 120,
  "max_skew_seconds": 30,
  "cost_per_unit": 0.02,
  "commission_on_profit": 0.0,
  "min_reference_books": 1,
  "min_ev": 0.0,
  "max_ev": 0.15
}
```

Use o horário da primeira decisão sintética, obtido do próprio arquivo:

```powershell
$decisionAt = (Get-Content .\work\price-strength-demo-001\fixtures.jsonl -First 1 | ConvertFrom-Json).decision_at
python -m brasileirao_predictor.research.price_strength scan --quotes .\work\price-strength-demo-001\quotes.jsonl --policy .\work\policy-synthetic.json --as-of $decisionAt --output-dir .\work\price-strength-scan-001
```

`scan` publica `scan.json` e recibo. Os snapshots recebidos depois de `--as-of` ficam excluídos. O estudo completo faz a comparação separadamente no horário de cada fixture.

## Contratos de entrada

Arquivos `.json` contêm um objeto; arquivos JSONL contêm **um objeto completo por linha**, sem linhas vazias. A leitura exige UTF-8, rejeita chaves duplicadas e números não finitos. Não use números em strings ou booleanos como substitutos. Todos os horários são strings ISO 8601 com fuso, por exemplo `2030-01-01T18:00:00+00:00`; internamente são convertidos para UTC.

### Protocolo (`protocol.json`)

O objeto exige exatamente estes campos:

- `schema_version`: `price-strength-study/1`.
- `study_id`, `hypothesis`, `stopping_rule`: textos não vazios, definidos antes de examinar a avaliação.
- `data_kind`: `SYNTHETIC_DEMONSTRATION` ou `EXPLORATORY_REPLAY`.
- `training_end`, `calibration_end`, `evaluation_start`, `evaluation_end`, `report_as_of`.
- `xg_config`: objeto de parâmetros do candidato; a demonstração grava todos explicitamente.
- `price_policy`: objeto da política descrita acima.

A ordem exigida é `training_end < calibration_end < evaluation_start <= evaluation_end <= report_as_of`. As decisões das fixtures devem estar dentro da janela inclusiva de avaliação. `stopping_rule` registra a regra declarada pelo pesquisador; o CLI não interpreta seu texto como uma linguagem de agendamento ou parada automática.

### Histórico (`history.jsonl`)

Cada linha exige `match_id`, `home_team`, `away_team`, `kickoff`, `completed_at`, `available_at`, `home_xg` e `away_xg`. Os identificadores são textos não vazios, os times devem diferir e os xG são números finitos não negativos. `home_goals` e `away_goals` são opcionais: forneça ambos como inteiros não negativos, ou omita ambos/use `null` em ambos. Outros campos não são aceitos.

A cronologia é `kickoff < completed_at <= available_at`. `available_at` representa a disponibilidade efetiva daquela observação ou revisão, incluindo o recebimento local necessário ao uso. Uma revisão deve manter o horário real em que ficou disponível; não retrodate uma captura tardia para o horário original da partida ou de publicação.

O modelo usa somente observações com `available_at < decision_at`, exclui o próprio `match_id` previsto e exige partidas concluídas. Para cada partida escolhe a revisão mais recente visível naquele instante. Duplicatas idênticas não aumentam a amostra; identidades conflitantes ou versões conflitantes no mesmo horário visível são recusadas. Revisões futuras não substituem a versão histórica disponível.

Os gols não alimentam a previsão xG bruta. Servem como alvos da calibração e como labels para métricas. Sem gols disponíveis até `report_as_of`, a fixture pode ter previsão e diagnóstico de preços, mas não pontuação. Placar ou identidade conflitante entre labels visíveis interrompe o estudo; não se escolhe uma versão pelo resultado mais favorável.

### Fixtures (`fixtures.jsonl`)

Cada linha contém exatamente `match_id`, `home_team`, `away_team`, `kickoff`, `decision_at`. O `match_id` deve ser único no arquivo e a decisão deve preceder estritamente o kickoff. Não há necessidade de resultados futuros para produzir previsões.

### Snapshots de preços (`quotes.jsonl`)

Cada linha representa o estado **completo de um mercado de uma casa**, com exatamente estes campos:

| Campos | Conteúdo |
| --- | --- |
| `snapshot_id`, `source`, `source_event_id`, `event_id`, `bookmaker` | Identificadores não vazios, sem espaços nas extremidades. |
| `market`, `period`, `line` | `1x2`, `ou25` ou `btts`; período `FT`; linha `2.5` em `ou25`, `null` nos demais. |
| `observed_at`, `available_at`, `received_at`, `kickoff_at` | Horários com fuso; observação, disponibilidade, recebimento local e início da partida. |
| `status` | `active`, `suspended` ou `unavailable`. |
| `snapshot_scope` | Literal `complete_market`. |
| `odds` | Objeto com todas as seleções quando ativo; `{}` quando suspenso ou indisponível. |
| `raw_payload_hash` | SHA-256 declarado do payload de origem, com 64 caracteres hexadecimais. |

As seleções exatas são `home`, `draw`, `away` em `1x2`; `over`, `under` em `ou25`; `yes`, `no` em `btts`. Odds ativas são números finitos maiores que 1. O estudo exige que todos os `event_id` pertençam às fixtures explícitas e que `kickoff_at` corresponda à fixture.

A ordem é `observed_at <= available_at <= received_at <= decisão`, com decisão estritamente anterior ao kickoff. O estado vigente é o de maior `received_at` elegível para cada evento/casa/mercado. Estados recentes suspensos, indisponíveis, inválidos ou vencidos bloqueiam o reaproveitamento de preços antigos. Um registro malformado sem identidade ou horário ordenável pode bloquear o lote inteiro. Divergências de identidade, kickoff, origem ou snapshots também aparecem nas rejeições.

Não adapte registros legados inventando `active`, `complete_market`, horários ou hashes ausentes. O contrato requer a informação de origem e de captura; acrescentar campos presumidos não comprova que aquele preço existia ou estava disponível. O hash registra proveniência declarada, sem autenticar a fonte nem provar execução na casa.

## Política de preços e interpretação do EV

Cada casa de referência precisa fornecer um mercado completo, ativo, recente, sincronizado e com soma das probabilidades implícitas maior que 1. A margem é removida proporcionalmente: cada `1 / odd` é dividido pela soma do mercado. A referência final é a média normalizada dessas distribuições. A casa que oferece o preço é sempre excluída da referência usada para avaliá-lo.

`max_age_seconds` limita a idade desde `observed_at`. `max_skew_seconds` limita diferenças de observação, disponibilidade e recebimento entre a oferta e as referências, e entre as referências. `min_reference_books` define a quantidade mínima de casas independentes da ofertante.

Para probabilidade `p` e odd decimal `o`, o cálculo por unidade de aposta hipotética é:

```text
gross_ev = p * o - 1
net_ev = p * (1 + (o - 1) * (1 - commission_on_profit)) - 1 - cost_per_unit
```

`cost_per_unit` é custo fixo por unidade apostada, cobrado independentemente do resultado. `commission_on_profit` incide sobre o lucro de **cada aposta vencedora**; não representa compensação de perdas nem comissão sobre o resultado líquido agregado de um mercado. Ambos ficam em `[0, 1)`. Limites opcionais `min_ev` e `max_ev` ficam em `[0, 1]`; EV líquido não positivo é sempre rejeitado.

O scanner seleciona no máximo um candidato por evento, pelo maior EV líquido calculado com a referência de preços e desempate determinístico. `selected_for_research` não significa aposta realizada. No estudo, `xg_diagnostics` acrescenta probabilidades, diferença contra a referência e EV dos candidatos xG; esses diagnósticos não substituem a regra de seleção do scanner. Não há liquidação financeira, comprovação de stake disponível ou simulação de carteira executada.

## Candidato rolling xG e calibração

O candidato é novo e não reproduz literalmente o modelo GAP. Para cada time usa suas últimas `window_matches` aparições no mando da fixture, ordenadas por kickoff. Calcula médias de xG a favor e contra com decaimento exponencial por idade e redução em direção a priors explícitos. A intensidade de gols de cada lado é a média da força de ataque correspondente com o xG concedido pelo adversário naquele mando.

Poisson independente e Skellam produzem distribuições normalizadas para `1x2`, `ou25` e `btts`, sem truncar uma grade de placares. Os parâmetros padrão, sem seleção por resultados do projeto, são:

| Parâmetro | Padrão |
| --- | ---: |
| `window_matches` | 5 |
| `min_team_matches` | 3 |
| `half_life_days` | 90.0 |
| `prior_weight` | 2.0 |
| `prior_home_xg` | 1.5 |
| `prior_away_xg` | 1.2 |
| `min_calibration_matches` | 20 |
| `calibration_prior_exposure` | 5.0 |
| `calibration_lead_minutes` | 60 |

A demonstração usa janela 4, mínimo por time 2 e mínimo de calibração 6, explicitamente no seu protocolo sintético. Não são parâmetros promovidos para uso real.

A calibração estima duas escalas multiplicativas de taxa, uma para cada lado: `(soma de gols + exposição prévia) / (soma de lambdas previstas + exposição prévia)`. Os alvos têm kickoff em `[training_end, calibration_end)` e resultados disponíveis estritamente antes de `calibration_end`. Cada previsão histórica é reconstruída em `kickoff - calibration_lead_minutes`, sem suas próprias estatísticas nem observações posteriores.

**`training_end` delimita os alvos da calibração; não congela as forças móveis.** Partidas anteriores da própria janela podem atualizar as forças quando já estiverem disponíveis antes da decisão seguinte. A mesma regra vale durante a avaliação. As duas escalas são ajustadas uma vez antes da avaliação e só podem ser aplicadas depois de `calibration_end`, à mesma configuração, sem o próprio alvo entre os IDs usados.

Histórico insuficiente por time/mando retorna `INSUFFICIENT_HISTORY`, sem probabilidades. Calibração insuficiente retorna `INSUFFICIENT_CALIBRATION` para a previsão calibrada; a bruta pode continuar elegível. Priors não contornam esses mínimos. O ajuste é calibração de intensidades, não demonstração de que as probabilidades estejam estatisticamente calibradas.

## Comparadores e saídas

O benchmark de mercado usa a referência associada à primeira casa ofertante elegível em ordem lexical por mercado, fora da lista de casas de referência. A escolha não depende de EV ou do resultado observado. O estudo registra essa proveniência e compara perdas apenas nas fixtures comuns a cada par candidato/comparador/mercado.

`--baseline caminho.jsonl` permite fornecer previsões externas congeladas. Cada linha exige exatamente `match_id`, `decision_at`, `generated_at`, `candidate_id`, `probabilities`. O ID deve pertencer às fixtures e ser único; `decision_at` deve coincidir com a decisão da fixture e `generated_at <= decision_at`. O objeto `probabilities` contém os três mercados e todas as seleções acima, com valores finitos em `[0, 1]` e soma 1 por mercado. O CLI não executa nem importa o modelo operacional para criar esse baseline. Sua origem e congelamento precisam ser sustentados externamente.

O estudo publica:

- `protocol.json`: protocolo fornecido.
- `forecasts.jsonl`: previsões brutas/calibradas, elegibilidade, lambdas, configuração, IDs históricos e de calibração usados e última disponibilidade.
- `price_scans.jsonl`: avaliações, referências, rejeições e candidatos de pesquisa por fixture.
- `comparisons.jsonl`: labels disponíveis e Brier/log loss por candidato e comparador.
- `rejections.jsonl`: motivos de indisponibilidade e validação.
- `summary.json`: contagens e diferenças médias de perdas pareadas; valores negativos favorecem o candidato, de forma descritiva.
- `manifest.json`: recibo `COMPLETE`, hashes SHA-256 e tamanhos de entradas/artefatos, hashes dos fontes Python do pacote e metadados.

O Brier 1X2 soma os erros quadráticos das três classes; os mercados binários usam a classe positiva. O log loss limita a probabilidade usada no log a `1e-15`. As médias pareadas não incluem intervalos de confiança, testes de significância ou conclusão de rentabilidade.

O conteúdo e o hash de cada entrada são obtidos dos mesmos bytes; mudanças detectadas antes da publicação recusam o recibo completo. Falhas após a criação da saída podem deixar `failure.json` e arquivos parciais. Use outro diretório novo para uma nova tentativa. Os recibos apoiam a reprodução do cálculo, mas não certificam horários, fontes, execução ou integridade anterior ao fornecimento dos arquivos. `profitability_established` e `real_capital_enabled` permanecem falsos.
