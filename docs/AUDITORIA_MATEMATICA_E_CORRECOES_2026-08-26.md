# Auditoria matemática e correções — 2026-08-26

## Adendo operacional: o gargalo econômico continua sendo o A1

Inspeção local em 2026-08-26 confirmou: **0 arquivos de snapshots A1, 0 estado
de captura, 0 log diário, nenhuma tarefa A1 instalada e `ODDSPAPI_KEY` ausente
do processo**. Portanto o coletor continua `NOT_STARTED`. As correções desta
auditoria não constituem progresso econômico enquanto a coleta PIT
Pinnacle×soft não começar. Ligar a tarefa exige chave rotacionada válida e ação
operacional explícita; isso não foi inferido nem executado silenciosamente.

Três bugs adicionais foram então corrigidos:

- Kelly .NET: passou de `fraction*edge/(O-1)` para
  `fraction*(p*O-1)/(O-1)`;
- imagens Python: os wheels compartilhados são baixados, verificados com
  `sha256sum -c constraints/shared-wheels.sha256` e só então instalados;
- coletor A1: um item inválido no meio do lote não envenena a cadeia dos itens
  válidos seguintes; o lote é reencadeado contra o último snapshot realmente
  persistido e retries semanticamente idênticos continuam deduplicados.

## Impacto retroativo do antigo clip

O código anterior ao fix foi reexecutado e instrumentado no painel pareado
2021–2024 (`n=1.320`). Nenhuma previsão teve fator Dixon–Coles `tau<=0`; o
menor dos quatro fatores foi `0,9060766079783874`. Assim, o clip silencioso era
um defeito matemático real, mas **latente nesse painel**: não há evidência de que
ele tenha zerado células nos 1.320 benchmarks históricos examinados.

## Correção de interpretação: zero argmax de empate não é invariante matemática

O zero observado continua sendo uma assinatura importante do regime ajustado,
mas não é uma impossibilidade da família NB/Dixon–Coles. Um contraexemplo direto
com forças iguais, `a=-1`, `alpha=0,1` e `rho=0` produz aproximadamente
`22,55% / 54,90% / 22,55%`: empate é o argmax. Portanto a formulação correta é:
**o conjunto de parâmetros/lambdas ajustado no Brasileirão não gerou argmax de
empate no painel**, não “a arquitetura impede matematicamente empate”. Isso
reforça investigar resolução e ambiente de gols, sem justificar boost pós-hoc.

## Estado

Esta nota supersede as métricas dos relatórios anteriores, mas preserva esses
arquivos como registro histórico. Os benchmarks corrigidos documentados abaixo
já foram recalculados; nenhum deles é confirmação cega. O capital permanece
bloqueado.

## Correções implementadas

1. A likelihood NB+Dixon–Coles agora inclui o normalizador da distribuição
   conjunta usado pela grade servida.
2. `rho` precisa manter positivas as quatro células corrigidas. Probabilidades
   negativas não são mais apagadas com `clip`.
3. O Elo recebe regressão à média desde o último jogo de cada clube até o
   horizonte da previsão.
4. A climatologia é prequential, usa apenas resultados anteriores e permanece
   congelada para todos os jogos do mesmo bloco de data.
5. Estratos menores que o bloco de bootstrap recebem `ci95=null` e não abortam
   o artefato canônico.
6. O hash do cache inclui a versão do algoritmo, invalidando parâmetros e Elo
   produzidos pelo código anterior.
7. Falhas excepcionais do ajuste que acionem fallback deixam de ser silenciosas
   e emitem `RuntimeWarning`.
8. O fitter Dixon–Coles puro usa a PMF analítica do placar observado; placares
   acima da grade de exibição não são mais comprimidos para a célula da borda.

## Correções de interpretação

- Empate em 0% dos argmax históricos é uma assinatura do regime ajustado, não
  uma impossibilidade matemática universal do modelo.
- `lambda_total = 2*exp(a)*cosh(b*delta)` é igualdade exata no incumbent sem
  perturbações assimétricas.
- `10/35` em T2-2026 é anômalo nominalmente também contra `p=0,471277`, mas a
  causa permanece não identificada.
- Os casos Internacional/Bahia são exploratórios e exigem permutação que
  preserve calendário, mando e dificuldade antes de sustentar efeito de clube.

## Governança prospectiva

H13 foi marcada como substituída sem avaliação final porque baseline e motor
continham os defeitos acima. H14 tem 2026-08-27 apenas como primeira data
possível, mas permanece `NOT_STARTED`: a coorte só começa quando previsões dos
dois braços forem persistidas antes do kickoff com fingerprint do código.

H14 e H15 são contrastes científicos diferentes, mas não são independentes no
portfólio: usam a mesma corrente futura de resultados e o braço serving com
refit 100 participa dos dois contrastes. Ambos carregam
`prospective_family_id=track-a-future-2026-08-27`; qualquer alegação conjunta
usa Holm step-down a 5%. Diagnósticos auxiliares não podem virar novos gates
pós-hoc. Essa regra está registrada, mas o avaliador prospectivo que a executa
ainda precisa existir antes da ativação.

## Raio de impacto da climatologia corrigida

A função defeituosa era a baseline do painel canônico
`benchmark_predictor.py`, portanto artefatos históricos desse painel contra
`climatology` precisam ser recalculados para comparações científicas. O bug
deixava a climatologia artificialmente mais fraca ao omitir o burn-in já
observado.

Ele não decidiu capital nem invalida uma promoção econômica: nenhuma trial do
ledger autoriza capital; H13, que declarava essa baseline, foi substituída sem
avaliação; e a única trial atualmente marcada `comprovada`, H12, é uma
comparação pareada ensemble-xG ligado versus desligado, não um gate contra
climatologia. Scripts auxiliares que importam `_climatology_probs` continuam
merecendo interpretação caso a caso, mas não há no ledger uma promoção passada
cujo veredito dependa exclusivamente da baseline com burn-in omitido.

## Método do ajuste de multiplicidade de H11-v2

O intervalo Bonferroni não é Wald. O script reexecuta o mesmo bootstrap de
bloco móvel e toma diretamente os quantis 1,25% e 98,75% da distribuição de
10.000 médias reamostradas (`alpha=0,05/2`). A proximidade entre o centro do
IC95 e o do intervalo simultâneo é compatível com uma distribuição bootstrap
quase simétrica, mas não identifica o método. O artefato o rotula como
“Bonferroni by repercentiling the moving-block bootstrap distribution”.

## H9: duas falhas distintas

O achado do adendo permanece correto: o relatório abortava mecanicamente em
`2021-T2`, pois `n=7 < block_length=21`; agora esse estrato recebe IC nulo. A
ressalva nova é epistemológica e adicional: os parâmetros congelados de H9
descendem do H8 já observado, então o painel histórico corrigido não é uma
confirmação independente. O primeiro problema impedia gerar o artefato; o
segundo limita o que o artefato concluído pode provar.

## Escopo da correção de linhas O/U do A1

Não houve confirmação por payload real da OddsPapi. A leitura do parser mostrou
um caminho lógico capaz de classificar linhas 1.5/3.5 como OU2.5 quando o
provedor as agrupasse no mesmo mercado. O código agora exige a linha textual
exata 2.5/2,5 e há teste sintético multlinha. Isso elimina a vulnerabilidade
independentemente do agrupamento real, mas a forma concreta do payload continua
não verificada sem uma chave rotacionada e uma captura válida.

## Medição corretiva concluída

O benchmark canônico foi reexecutado com hashes, parâmetros, coverage, métricas
e diferenças contra o estado histórico. Números anteriores continuam
descrevendo apenas o algoritmo antigo.

## Benchmark histórico diagnóstico do algoritmo corrigido

Artefato: `reports/benchmark_serving_v2_corrected_2021_2024_2026-08-26.json`.
Este painel usa dados já examinados e não é confirmação da H14.

| Métrica | Serving v2 | Climatologia prequential | Delta | IC95 do delta |
|---|---:|---:|---:|---:|
| RPS | 0,213240 | 0,221284 | -0,008044 | [-0,012119; -0,004452] |
| Brier 1X2 | 0,622222 | 0,640130 | -0,017908 | [-0,025904; -0,010295] |
| Log loss | 1,036350 | 1,060805 | -0,024455 | [-0,036870; -0,013293] |

Foram avaliados 1.320 jogos, todos com kickoff real. O benchmark concluiu sem
warning de convergência após retry determinístico do otimizador.

### Diagnósticos corrigidos de 2025 e 2026

Esses períodos já tinham sido examinados. Os resultados abaixo medem o efeito
da correção, mas não validam H14 nem autorizam seleção de modelo.

| Período | n | RPS antigo | RPS v2 | Brier antigo | Brier v2 | Log loss antigo | Log loss v2 | Accuracy antiga | Accuracy v2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025 | 380 | 0,205339 | 0,205511 | 0,602207 | 0,602546 | 1,006240 | 1,006797 | 50,2632% | 50,5263% |
| 2026 até 26/08 | 225 | 0,208918 | 0,207998 | 0,630819 | 0,628574 | 1,044541 | 1,041528 | 47,1111% | 48,4444% |

Em 2025 a alteração é praticamente neutra e ligeiramente pior nas perdas
probabilísticas. Em 2026 há melhora diagnóstica em RPS, Brier, log loss e
accuracy. Nenhuma dessas diferenças foi usada para escolher a correção: todas
as mudanças decorreram de invariantes matemáticos e temporais identificados
antes deste recálculo.

O resultado de 2026 tem **peso probatório zero a favor das correções**. Os
diagnósticos T2-2026 e Internacional/Bahia já eram conhecidos e ajudaram a
direcionar a auditoria para baixa reatividade e decay. A melhora posterior era,
portanto, um resultado esperado da própria busca e não constitui confirmação,
nem mesmo fraca. Uma piora teria sido evidência contra a hipótese; a melhora é
um não-evento epistemológico.

## Comparação pareada v2 menos v1 em 2021–2024

O commit pré-fix `9ee7578` e a versão corrigida foram executados sobre o mesmo
SQLite (SHA-256 `8A3A2415AAB9B8525708EE18EE7B3FB360B40031904095F5C71B35871E5946CD`).
Os 1.320 jogos casaram por `event_id`, data e equipes, sem perda em nenhum
braço. Os ICs usam bootstrap de bloco móvel 21, 10.000 réplicas e seed 42.

| Perda | v1 | v2 | Delta v2-v1 | IC95 do delta |
|---|---:|---:|---:|---:|
| RPS | 0,213278190 | 0,213240045 | -0,000038145 | [-0,000118534; +0,000034512] |
| Brier 1X2 | 0,622300976 | 0,622221705 | -0,000079270 | [-0,000275410; +0,000093894] |
| Log loss | 1,036489245 | 1,036350382 | -0,000138864 | [-0,000417316; +0,000118414] |
| Accuracy | 47,575758% | 47,575758% | 0,000000 pp | [0; 0] |

Conclusão: o pacote corrige invariantes matemáticos e temporais, mas não há
evidência de upgrade preditivo agregado em 2021–2024. Os pontos estimados das
três perdas favorecem v2 por magnitude desprezível e todos os ICs incluem
zero. Também não apareceu trade-off mensurável nas métricas avaliadas.

Artefatos reproduzíveis:

- `reports/losses_serving_v1_2021_2024.json`;
- `reports/losses_serving_v2_2021_2024.json`;
- `reports/comparison_serving_v2_minus_v1_2021_2024.json`.
