# Catálogo de variáveis relacionadas ao empate

Versão: `draw-variable-catalog/1`
Finalidade: mapa de investigação, não especificação de um novo modelo.

Nenhuma variável deste documento está automaticamente aprovada como feature. Para entrar no serving, precisa existir antes de `predicted_at`, ter proveniência e relógio PIT, ser testada isoladamente em protocolo próprio e melhorar métricas probabilísticas fora da amostra. Accuracy permanece `DIAGNOSTIC_ONLY`.

## 1. Distinções obrigatórias

Estas quantidades não são equivalentes:

- `p_draw_1x2`: soma da diagonal inteira da matriz de placares, isto é, `P(0–0)+P(1–1)+P(2–2)+...`;
- `modal_score_is_draw`: indica se o placar individual mais provável é um empate;
- `p_modal_score`: probabilidade somente daquele placar;
- `draw_is_1x2_argmax`: indica se `p_draw_1x2` supera cada lado no agregado;
- `balanced_sides`: forças/probabilidades de casa e fora próximas;
- `low_scoring`: poucos gols esperados, condição que normalmente concentra massa em placares iguais baixos.

Um 1–1 pode ser o placar individual mais provável enquanto vitória da casa é o maior agregado 1X2. Toda previsão deve mostrar os dois resultados sem trocar um pelo outro.

## 2. Variáveis produzidas pelo motor atual

| Variável | Definição | Relação com empate | Estado |
| --- | --- | --- | --- |
| `lambda_home` | gols esperados do mandante | nível e formato da distribuição | disponível e usada |
| `lambda_away` | gols esperados do visitante | nível e formato da distribuição | disponível e usada |
| `lambda_total` | `lambda_home + lambda_away` | totais menores tendem a concentrar 0–0/1–1 | derivável |
| `lambda_gap` | `abs(lambda_home-lambda_away)` | mede simetria das taxas | derivável |
| `lambda_ratio` | menor lambda / maior lambda | outra medida de equilíbrio | derivável; proteger divisão por zero |
| `rho_dc` | correção Dixon–Coles | redistribui massa em 0–0, 1–0, 0–1 e 1–1 | disponível e usada |
| `p_draw_1x2` | soma da diagonal da matriz | probabilidade agregada do empate | disponível e usada |
| `p_00`, `p_11`, `p_22`, ... | probabilidades exatas da diagonal | explica de onde vem `p_draw_1x2` | disponíveis na matriz |
| `modal_score` | placar individual de maior massa | revela a moda, não o 1X2 | disponível |
| `modal_score_is_draw` | gols da casa = gols de fora na moda | sinal descritivo discutido nesta rodada | derivável; não é regra validada |
| `p_modal_score` | massa do placar modal | força/concentração da moda | derivável |
| `draw_rank_1x2` | posição do empate entre casa/empate/fora | distingue empate argmax, segundo ou terceiro | derivável |
| `top_1x2_gap` | diferença entre as duas maiores probabilidades | mede fragilidade do argmax | derivável |
| `side_probability_gap` | `abs(p_home-p_away)` | mede equilíbrio entre os times | derivável |
| `draw_vs_best_side_gap` | `p_draw-max(p_home,p_away)` | distância para o empate virar argmax | derivável |
| `entropy_1x2` | entropia de casa/empate/fora | incerteza global, não direção para empate | derivável |
| `diagonal_concentration` | `p_draw_1x2 / p_modal_score` ou decomposição por placar | separa empate espalhado de uma única moda | hipótese descritiva |

## 3. Força, forma e geração dos lambdas

| Grupo | Variáveis candidatas | Situação atual |
| --- | --- | --- |
| Força Elo | `elo_home`, `elo_away`, diferença bruta, diferença absoluta, diferença efetiva após mando | Elo disponível e usado |
| Mando | vantagem de casa, campo neutro, estádio alternativo | vantagem e `neutral` disponíveis; estádio alternativo não modelado |
| Ataque/defesa | força ofensiva e defensiva de cada equipe; simetria ataque↔defesa | parâmetros NB/DC disponíveis e usados |
| Recência | decaimento temporal, forma recente, mudança da diferença de força | decaimento existe; formulações novas exigem trial |
| Ambiente de gols | média móvel da liga, média por temporada/turno, dispersão | candidato do TRACK A; não promovido |
| Incerteza da força | número de jogos, recém-promovido, tempo fora da Série A, variância/shrinkage | parcialmente disponível; não promovido |
| Confronto de estilos | criação vs. prevenção, ritmo, posse estéril, transições | não validado como feature de empate |

Não criar uma regra manual porque Elo ou lambdas “parecem equilibrados”. O efeito precisa aparecer em RPS/Brier/log loss e calibração do `p_draw`.

## 4. Contexto pré-jogo candidato

Todas estas variáveis precisam de `available_at <= predicted_at`:

- dias de descanso de cada equipe, diferença de descanso e congestionamento recente;
- distância/tempo de viagem e sequência casa/fora;
- escalação provável ou confirmada e horário da captura;
- número de titulares trocados entre provável e oficial;
- continuidade de titulares, goleiro, zaga, meio-campo e ataque;
- força agregada da escalação e diferença de força entre as escalações;
- ausências, suspensões, lesões e retornos, sempre com fonte e horário;
- troca recente de treinador, tempo no cargo e mudança tática;
- competição paralela, rotação declarada e prioridade competitiva;
- posição na tabela e incentivos mensuráveis, sem narrativa pós-resultado;
- clássico/derby, fase da temporada e rodada;
- gramado, estádio, altitude, clima e chuva;
- árbitro: taxa histórica de pênaltis/cartões/acréscimos, somente com amostra e shrinkage.

No estado atual, escalações são principalmente dados arquivados. Sem uma transformação congelada e validada de jogador/escalação para lambda, elas devem ser mostradas como contexto, não convertidas em ajuste improvisado.

## 5. Mercado pré-jogo

| Variável | Regra PIT |
| --- | --- |
| probabilidade de empate sem vig | de-vig por casa e snapshot capturado antes do kickoff |
| diferença modelo–mercado no empate | comparar `p_draw_1x2` com mercado na mesma vintage |
| abertura do empate | somente primeira captura genuína, nunca reconstruída após o jogo |
| movimento da linha do empate | abertura → snapshot atual, ambos PIT |
| velocidade e magnitude do movimento | exige múltiplas capturas com relógio confiável |
| dispersão entre casas | de-vig individual antes de formar consenso |
| OU2.5 sem vig | proxy do ambiente de gols, não confirmação automática de empate |
| handicap asiático | proximidade da linha de handicap como informação de equilíbrio |
| BTTS | complementa a distinção 0–0 versus 1–1, sem ser equivalente a empate |
| dupla chance e draw-no-bet | informação derivada; evitar dupla contagem com o mesmo 1X2 |

Fechamento só pode ser feature se já existia no instante da previsão. Closing observado posteriormente serve para avaliação/CLV, nunca para reconstruir uma previsão pré-jogo.

## 6. Variáveis ao vivo

- minuto e fração de tempo restante;
- placar atual e diferença de gols;
- estado de empate atual (`score_home == score_away`);
- gols ainda necessários para terminar empatado;
- cartões vermelhos, lado e minuto;
- xG acumulado e diferença de xG;
- finalizações, finalizações no alvo e qualidade média das chances;
- posse, entradas no terço final e pressão territorial;
- escanteios, cartões e faltas;
- substituições, lesões e mudança de formação;
- acréscimos estimados;
- odds live 1X2/empate e movimento desde o último snapshot.

Hoje essas estatísticas podem ser registradas e descritas, mas **não possuem pesos validados para entrar quantitativamente**. O modelo live atual pode usar apenas estado e transformação previamente documentados; qualquer inclusão adicional é experimento separado.

## 7. Qualidade e disponibilidade dos dados

Variáveis de controle que acompanham qualquer análise:

- `captured_at`, `available_at`, `predicted_at` e `kickoff_at`, todos UTC aware;
- fonte, `event_id`, versão do schema e fingerprint do pipeline;
- provável/confirmada explícita para escalação;
- cobertura por variável, temporada e tipo de previsão;
- idade/frescor do snapshot;
- quantidade de jogos anteriores de cada equipe;
- missingness por equipe/temporada e motivo da ausência;
- jogo adiado/superseded, campo neutro e identidade correta do evento;
- quantidade de casas no consenso e método de de-vig;
- tamanho da amostra `n` em cada estrato.

Ausência não pode virar zero silenciosamente. Dado pós-kickoff não pode receber marca pré-jogo.

## 8. Alvos e diagnósticos para estudar o empate

Resultados/targets, nunca features do próprio jogo:

- `actual_draw` e placar final;
- empate no intervalo versus empate final;
- 0–0, empate com gols e faixa de total de gols;
- taxa histórica de empate da liga/equipe calculada apenas com passado;
- RPS 1X2, Brier multiclasse e log loss;
- Brier binário específico para `draw` vs. `not_draw`;
- calibração/reliability de `p_draw` por bins com `n`;
- calibration intercept e slope do empate;
- resolution e sharpness de `p_draw`;
- erro por temporada, faixa de `lambda_total`, `lambda_gap`, Elo gap e mando;
- comparação contra climatologia e mercado sem vig na mesma amostra;
- coverage e accuracy apenas diagnóstica.

## 9. Ordem segura de investigação

1. Auditar a calibração do `p_draw` atual e a decomposição 0–0/1–1/2–2.
2. Estratificar somente variáveis já produzidas pelo motor, sempre com `n` e coverage.
3. Verificar estabilidade 2021–2023 e depois 2024, sem consumir 2025 para escolha.
4. Usar 2025/2026 no serving cronológico; usar 2026 apenas como diagnóstico exploratório na pesquisa.
5. Formular uma hipótese por vez. Exemplo: corrigir `rho`, ambiente de gols ou força dinâmica — nunca todos juntos.
6. Só depois testar contexto novo PIT, começando por descanso ou força de escalação mensurável.

Não há, neste catálogo, autorização para religar o ensemble xG, criar regra automática de empate, promover modelo ou habilitar capital.
