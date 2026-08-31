# Relatório de Validação Forward — Brasileirão 2026 (iniciado 2026-07-12)

## Contexto

Teste forward (fora da amostra de calibração) sobre os primeiros 18 jogos
disputados do Brasileirão 2026, para checar consistência com o backtest
walk-forward de 1.165 jogos (`docs/RELATORIO_BACKTEST_2026-07-10.md`), cujo
único mercado com edge validado é **OU 2.5** (ROI +7,9%, CLV +19,6%).

## Metodologia

Mesma do backtest: Elo forward (só vê o passado, `window_years=6`,
`form_half_life_years=4.0`), Poisson/Dixon-Coles calibrado apenas com jogos
anteriores a 2026-01-28 (sem contaminação da temporada 2026 no treino),
odds de fechamento devigadas por Shin (`brasileirao_predictor.math_utils.shin_probabilities`).
Regra de compra idêntica ao backtest: só entra se `2% <= EV <= 15%`
(`cfg["backtest"]`).

Scripts (todos aceitam N de jogos como argumento posicional, default 18):
- [brasileirao_scripts/predict_first18_2026.py](../brasileirao_scripts/predict_first18_2026.py) `[N]` — 1X2 puro (hit-rate bruto)
- [brasileirao_scripts/predict_first18_ou_dc.py](../brasileirao_scripts/predict_first18_ou_dc.py) `[N]` — OU2.5 e DC (hit-rate bruto)
- [brasileirao_scripts/predict_walkforward_ev.py](../brasileirao_scripts/predict_walkforward_ev.py) `[N]` — EV/P&L simulado
- [brasileirao_scripts/predict_first18_teams.py](../brasileirao_scripts/predict_first18_teams.py) `[N]` — quebra por time (gols esperados vs reais, Brier por time)

## Resultados — N=18 (2026-07-12)

### 1X2 puro (hit-rate, sem EV)
9/18 → 7/18 acertos após corrigir bug de double-counting de home advantage (38,9%). Confirma o viés estrutural já documentado: o modelo nunca prevê empate (P(empate) nunca é a maior das três), então perde todos os 6 empates reais da amostra. Consistente com os 26,2% do backtest de 1.165 jogos.

### OU 2.5 e DC (hit-rate bruto, sem regra de EV)
| Mercado | Hit-rate |
|---|---:|
| OU 2.5 | 8/18 (44,4%) |
| DC (1X/X2, lado mais provável) | 13/18 (72,2%) |

### EV com Shin de-vig (regra de compra 2%–15%, stake 1u)
| Mercado | Apostas geradas | Vitórias | P&L | ROI |
|---|---:|---:|---:|---:|
| **OU 2.5** | 10/18 | 4 (40,0%) | **−1,45u** | **−14,5%** |
| **DC (1X/X2)** | 11/18 | 6 (54,5%) | **−2,83u** | **−25,7%** |

### Quebra por time (gols esperados vs reais, calibração)

Para cada time nos 18 jogos, comparamos gols feitos/sofridos reais com o
`lambda` (gols esperados) que o modelo atribuiu à partida, e o Brier score
(1X2) — mede se o erro está distribuído ou concentrado em times específicos.

| Time | J | ΔAtaque (GF−xGF) | ΔDefesa (xGC−GC) | 1X2 | Brier |
|---|---:|---:|---:|---:|---:|
| Botafogo | 2 | **+4,22** | **−2,92** | 1/2 | 0,53 |
| Grêmio | 2 | **+4,05** | −1,99 | 1/2 | 0,47 |
| Palmeiras | 2 | **+3,73** | −1,20 | 1/2 | 0,51 |
| Chapecoense | 2 | +2,52 | −0,66 | 1/2 | 0,64 |
| Vitória | 2 | +0,79 | −2,12 | **2/2** | 0,30 |
| Cruzeiro | 1 | −0,96 | **−2,50** | 1/1 | 0,37 |
| Coritiba | 1 | −1,58 | −0,09 | 0/1 | 0,95 |
| Internacional | 2 | **−1,22** | +1,14 | 0/2 | 1,10 |
| Flamengo | 2 | **−1,64** | −1,34 | 0/2 | 1,02 |
| *(demais 11 times)* | — | próximo de 0 | próximo de 0 | — | — |

ΔAtaque > 0 = time fez mais gols do que o modelo previa (ataque subestimado);
ΔDefesa > 0 = time sofreu menos gols do que o modelo previa (defesa
subestimada).

**Brier médio global (1X2): 0,657** vs. piso de referência "sempre
33%/33%/33%" = 0,667 — calibração praticamente nula nesta amostra (mal supera
o chute uniforme). Mas o erro não está distribuído igualmente: está
concentrado em ~5 times com viés forte nos dois lados simultaneamente
(Botafogo/Grêmio/Palmeiras para cima, Flamengo/Internacional para baixo),
enquanto o restante do elenco está razoavelmente calibrado. Padrão consistente
com drift do Elo herdado de 2024/25 não capturando mudanças de elenco/técnico
rápido o suficiente (`form_half_life_years=4.0`) — hipótese a investigar se
persistir na marca de 40 jogos, não indicativo suficiente ainda.

## Resultados — N=40 (2026-07-15)

Reexecução com o dobro da amostra (jogos de 2026-01-28 a 2026-03-11).

| Métrica | N=18 | N=40 | Tendência |
|---|---:|---:|---|
| 1X2 hit-rate | 38,9% (7/18) | 42,5% (17/40) | leve melhora |
| OU2.5 hit-rate (bruto) | 44,4% (8/18) | 47,5% (19/40) | leve melhora |
| DC hit-rate (bruto) | 72,2% (13/18) | 77,5% (31/40) | melhora |
| OU2.5 EV — apostas geradas | 10 | 25 | — |
| **OU2.5 EV — ROI** | −14,5% | **−33,8%** | **piorou** |
| DC EV — apostas geradas | 11 | 23 | — |
| DC EV — ROI | −25,7% | −16,5% | melhorou |
| Brier médio (1X2, piso uniforme=0,667) | 0,657 | 0,656 | estagnado |

### Quebra por time — N=40 (destaques)

| Time | J | ΔAtaque | ΔDefesa | 1X2 | Brier |
|---|---:|---:|---:|---:|---:|
| Palmeiras | 4 | **+5,66** | −1,32 | 3/4 | 0,43 |
| Chapecoense | 3 | +4,02 | −2,71 | 1/3 | 0,71 |
| Grêmio | 4 | +3,48 | −2,63 | 3/4 | 0,42 |
| Botafogo | 3 | +3,23 | −2,47 | 2/3 | 0,49 |
| Internacional | 5 | **−2,07** | +0,68 | 2/5 | 0,77 |
| Cruzeiro | 4 | −1,21 | **−4,17** | 1/4 | 0,82 |

Palmeiras, Grêmio e Botafogo mantêm o mesmo viés positivo de N=18 (times que
o modelo subestima) com base agora 2x maior — não era ruído do N=18.
Internacional segue subestimado negativamente. Cruzeiro surge como o pior
calibrado em defesa (sofreu bem mais gols do que o modelo previa), sinal
novo que não estava claro em N=18.

## Leitura

O achado central de N=40 **não é "mais do mesmo" — é uma inversão de
expectativa**. Em N=18 a leitura foi "cedo demais pra refutar o backtest de
1.165 jogos". Com o dobro da amostra:

- **O ROI de OU2.5 não convergiu de volta para o +7,9% do backtest — piorou
  de −14,5% para −33,8%**, com mais que o dobro de apostas geradas (25 vs
  10). O viés (o modelo apostando OVER onde o backtest histórico indicava
  edge no UNDER) se repetiu e se intensificou, não diluiu. Isso já não é
  atribuível só a ruído de amostra pequena.
- **DC melhorou de −25,7% para −16,5%** — ainda negativo, mas na direção
  certa. Hit-rate bruto subiu de 72,2% para 77,5%, mais perto do patamar
  necessário pras odds curtas (~1,3–2,0) darem ROI positivo.
- **Calibração (Brier) ficou estagnada** (0,657 → 0,656) — o modelo não está
  "aprendendo" a temporada 2026 conforme mais jogos entram nessa janela de
  40, e o viés por time (Palmeiras/Grêmio/Botafogo pra cima,
  Internacional/Cruzeiro pra baixo) se manteve entre as duas marcas.
- **Investigação de causa raiz concluída para N=40** (ver seção dedicada
  abaixo): duas hipóteses testadas por sweep de hiperparâmetro,
  `form_half_life_years` refutada e `calibration_window_years` com efeito
  grande na média mas **sem significância estatística** no bootstrap —
  nenhuma virou mudança de config.

## Investigação de causa raiz — sweep de hiperparâmetros (2026-07-15)

Scripts: [brasileirao_scripts/investigate_half_life.py](../brasileirao_scripts/investigate_half_life.py) `[N]`,
[brasileirao_scripts/investigate_calibration_window.py](../brasileirao_scripts/investigate_calibration_window.py) `[N]`
— ambos read-only (não tocam `config.yaml`), recomputam Elo/Poisson do zero
por valor do grid e reportam Brier, hit-rate, viés nos 5 times flagged
(Palmeiras/Grêmio/Botafogo/Internacional/Cruzeiro) e EV/ROI real de OU2.5
(Shin de-vig, regra 2%–15%) — tudo em N=40.

### `form_half_life_years` — REFUTADA

Grid 0,5 a 6,0 anos + sem decaimento. Confirmado que o sweep muda os ratings
de verdade (rating final do Palmeiras varia de 1650 a 1748 conforme o valor),
mas o impacto nas métricas de teste é irrisório: Brier 0,649→0,658 (1,4% de
variação), viés nos times flagged 26,45→26,99 (2%). **O valor atual (4,0) já
está essencialmente no ótimo do grid.** Não é a causa do viés persistente.

### `calibration_window_years` — efeito grande na média, SEM significância estatística

| cy (anos) | n_train | hit OU2.5 | Brier | Apostas EV | Vitórias | **ROI** |
|---|---:|---:|---:|---:|---:|---:|
| 0,25 | 84 | 52,5% | 0,660 | 11 | 63,6% | **+22,1%** |
| **0,50** | 222 | 55,0% | 0,667 | 21 | 61,9% | **+25,7%** |
| 0,75 | 320 | 50,0% | 0,662 | 31 | 41,9% | −12,9% |
| 1,00 | 380 | 50,0% | 0,661 | 28 | 32,1% | −33,8% |
| 1,5–4,0 (atual) | 572–760 | 47,5% | 0,656 | 25 | 32,0% | −33,8% |

A partir de cy≈1,75 o resultado satura (dataset só tem histórico desde
abril/2024, então cy=2, 3, 4 e "sem limite" processam exatamente os mesmos
760 jogos de treino — por isso ficam idênticos). O corte que importa é
cy≤0,5 (calibrar só com dados de meados/fim de 2025, sem misturar 2024).

**Ressalvas antes de tratar como confirmado**:
- N pequeno nos dois lados (11–21 apostas) — dá pra virar com poucos jogos a
  mais, não é prova ainda.
- `n_train` cai de 760 para 222 jogos em cy=0,5 — menos dado pra estimar
  `alpha`/`rho` (dispersão e correlação Dixon-Coles), risco real de
  overfitting num padrão de curto prazo em vez de sinal genuíno.
- **cy=0,75–1,0 é um "vale" com ROI pior que o extremo longo** (−12,9% e
  −33,8%) — não é uma curva suave rumo ao ótimo, é uma transição abrupta
  entre dois regimes. Isso pede cautela: parece mais "o modelo muda de lado"
  do que "convergência gradual".

**Decisão inicial**: não alterar `config.yaml` ainda. Antes de qualquer
mudança de produção, bootstrap do IC95% do ROI em cy=0,5 (mesmo padrão usado
no veredito H1/H4) e confirmação em N=80.

### Bootstrap do IC95% (2026-07-15) — nenhum candidato é significativo

Script: [brasileirao_scripts/bootstrap_calibration_window.py](../brasileirao_scripts/bootstrap_calibration_window.py) `[CY] [N]`
— cluster bootstrap por jogo (`brasileirao_predictor.bootstrap.ci_mean_cluster`, não i.i.d. por
aposta: OVER/UNDER do mesmo jogo compartilham o choque do resultado), 1000
iterações, seed 13 — mesma config oficial usada no veredito H1/H4.

| cy | Apostas | ROI médio | IC 95% | Veredito |
|---|---:|---:|---|---|
| 0,25 | 11 | +22,1% | [−30,9%, +75,5%] | NÃO significativo |
| **0,50** | 21 | +25,7% | **[−22,2%, +66,2%]** | **NÃO significativo** |
| 4,0 (atual) | 25 | −33,8% | [−69,6%, +10,2%] | NÃO significativo |

**Nenhum dos três é evidência real** — todos os IC95% cruzam zero. O ROI de
+25,7% em cy=0,5 que parecia sinal forte na tabela bruta tem intervalo de
−22,2% a +66,2%: totalmente compatível com edge real zero (ou negativo) e o
resultado observado sendo sorte de amostra pequena (21 apostas). O mesmo vale
pro −33,8% do config atual — também não é estatisticamente diferente de
zero.

**Decisão final**: com N=40, este teste **não tem poder estatístico pra
decidir nada** — nem confirmar cy=0,5, nem refutar o config atual (4,0). Não
é só "cautela por N pequeno" (como a decisão inicial dizia) — é ausência
literal de significância dos dois lados. `config.yaml` permanece inalterado.
O próximo ponto de decisão real é N=80, quando o IC pode apertar o
suficiente pra separar sinal de ruído.

## Resultados — N=80 (2026-07-15)

Reexecução com o dobro da amostra de novo (jogos até 2026-04-01; a base
local tem 177 jogos disputados disponíveis no momento, então N=80 ainda tem
folga).

| Métrica | N=18 | N=40 | **N=80** | Tendência |
|---|---:|---:|---:|---|
| 1X2 hit-rate | 38,9% | 42,5% | **47,5%** | melhorando |
| OU2.5 hit-rate (bruto) | 44,4% | 47,5% | **56,2%** | melhorando bem |
| DC hit-rate (bruto) | 72,2% | 77,5% | 75,0% | estável |
| Brier (calibração, piso uniforme=0,667) | 0,657 | 0,656 | **0,625** | **saiu da estagnação** |
| OU2.5 EV — apostas | 10 | 25 | 47 | — |
| **OU2.5 EV — ROI** | −14,5% | −33,8% | **−22,9%** | melhorando (ainda negativo) |
| DC EV — ROI | −25,7% | −16,5% | **−11,4%** | melhorando |

**Primeiro sinal real de melhora**: o Brier saiu da estagnação das duas
marcas anteriores (0,656-0,657) e caiu pra 0,625 — a calibração está
melhorando conforme a temporada avança, consistente com a hipótese de que
parte do viés inicial era efeito de abertura de temporada (elenco/ritmo
ainda não refletido no histórico), não um bug estrutural do modelo. O ROI de
OU2.5 também vem melhorando (−33,8%→−22,9%), ainda no vermelho mas na
direção certa — não voltou a piorar como tinha acontecido de N=18 para N=40.

### Bootstrap do candidato `calibration_window_years=0,5` — N=80

| cy | Apostas | ROI médio | IC 95% | Veredito |
|---|---:|---:|---|---|
| 0,5 | 43 | +13,5% | [−17,6%, +43,6%] | ainda NÃO significativo |
| 4,0 (atual) | 47 | −22,9% | [−50,6%, +7,0%] | ainda NÃO significativo |

Os intervalos **encolheram** frente a N=40 (cy=0,5: amplitude de 88pp→61pp;
config atual: 80pp→58pp) — comportamento esperado com mais dado. Nenhum
cruzou a linha de significância ainda, mas o config atual (4,0) está perto
pelo lado negativo (limite superior +7,0%, quase todo o intervalo no
vermelho). Ainda sem base pra mudar `config.yaml`.

### Quebra por time — achado novo

**Botafogo despencou em defesa**: ΔDefesa foi de −2,92 (N=18) para −8,25
(N=80) — sofreu 18 gols contra 9,75 esperados pelo modelo, o maior desvio
isolado observado até agora neste teste. Palmeiras (+4,45) e Grêmio (+3,24)
mantêm o mesmo viés de ataque desde N=18 (modelo subestima os dois de forma
consistente nas três marcas). Cruzeiro segue mal calibrado em defesa
(ΔDefesa −5,47, crescendo desde N=18).

## Resultados — N=160 (2026-07-15)

Reexecução com o dobro da amostra mais uma vez (base local tinha 177 jogos
disputados disponíveis; 160 já cobre quase toda a temporada até aqui).

| Métrica | N=18 | N=40 | N=80 | **N=160** |
|---|---:|---:|---:|---:|
| 1X2 hit-rate | 38,9% | 42,5% | 47,5% | **48,8%** |
| OU2.5 hit-rate (bruto) | 44,4% | 47,5% | 56,2% | **53,1%** |
| Brier (piso uniforme=0,667) | 0,657 | 0,656 | 0,625 | **0,631** |
| OU2.5 EV — apostas | 10 | 25 | 47 | **98** |
| **OU2.5 EV — ROI (config atual)** | −14,5% | −33,8% | −22,9% | **−22,1%** |
| DC EV — ROI | −25,7% | −16,5% | −11,4% | **−10,8%** |

O ROI de OU2.5 com o config atual **estabilizou** em torno de −22% entre
N=80 e N=160 (−22,9%→−22,1%), depois de duas marcas de melhora — primeiro
sinal de que o valor pode estar convergindo pra um patamar real, não mais
oscilando por causa do tamanho de amostra.

### Bootstrap do candidato `calibration_window_years=0,5` — N=160: os dois critérios bateram

| cy | Apostas | ROI médio | IC 95% | Veredito |
|---|---:|---:|---|---|
| **0,5** | 82 | +23,0% | **[+1,0%, +43,8%]** | **SIGNIFICATIVO (positivo)** |
| **4,0 (atual)** | 98 | −22,1% | **[−42,0%, −2,2%]** | **SIGNIFICATIVO (negativo)** |

Os dois critérios definidos no compromisso anterior bateram simultaneamente:
o config atual fechou totalmente negativo e o candidato cy=0,5 fechou
totalmente positivo, nenhum cruzando zero.

**Ressalva séria antes de tratar como confirmado — comparação múltipla não
corrigida.** Este resultado veio de um **grid de 9 valores** de
`calibration_window_years` testados em `investigate_calibration_window.py`
(0,25 a 4,0 + sem limite), e só depois escolhi o de melhor ROI (cy=0,5) pra
rodar o bootstrap isolado. Testar 9 configurações e destacar a vencedora
antes de medir significância é o mesmo problema que o H1 original tratava
descontando o DSR pelas tentativas de registro
(`docs/RELATORIO_BACKTEST_2026-07-10.md`: *"DSR descontado pelas 2
tentativas do registro"*, regra explícita *"NÃO variar configuração — N+1
deflaciona"*). O IC95% de [+1,0%, +43,8%] é o IC do "melhor entre 9
candidatos testados nestes mesmos 160 jogos", não o IC verdadeiro de "cy=0,5
tem edge" — sistematicamente mais otimista do que um teste único teria dado.

**Isso não invalida o achado — muda o que ele significa.** Deixa de ser
"decisão pra aplicar em config.yaml" e vira **candidato forte pra um H-novo
pré-registrado**, no mesmo padrão do H1/H4: declarar `calibration_window_years
= 0,5` como hipótese única, ANTES de olhar mais dados, e testar num
walk-forward fresco — idealmente sobre jogos que ainda não entraram nesta
exploração (não reaproveitar estes mesmos 160 usados pra escolher o
candidato, sob pena de repetir o viés de seleção).

### Quebra por time — reversão importante

**Os "5 times flagged" das marcas anteriores não são mais o quadro
completo — dois deles reverteram de sinal.** Em N=80, Palmeiras (+4,45) e
Grêmio (+3,24) pareciam ter viés de ataque persistente; em N=160,
**Palmeiras caiu pra −0,74 e Grêmio pra −0,88** — o viés inverteu
completamente. Internacional também inverteu (de −1,65 em N=80 pra **+1,38**
em N=160). Isso é um alerta importante: **o padrão que eu vinha chamando de
"persistente" entre N=18/40/80 era, na verdade, fragilidade de amostra
pequena por time** (cada time só tinha 1-5 jogos nas marcas anteriores) —
não uma característica real e estável do modelo para esses times.

Times com viés que **cresceu e se manteve na mesma direção** (esses sim
parecem reais): **Botafogo** (ΔDefesa −2,92→−8,25→**−11,04**, sofrendo cada
vez mais gols do que o modelo prevê) e **Cruzeiro** (ΔDefesa −2,50→−4,17→
**−6,60**). **Chapecoense** surge como novo extremo (ΔDefesa −10,33, ainda
sem histórico nas marcas anteriores pra confirmar persistência).

## Compromisso de reexecução

**Não é mais "dobrar N e reavaliar"** — a investigação de
`calibration_window_years` mudou de fase exploratória para candidata a
pré-registro formal. Próximos passos, em ordem:

1. **Pré-registrar `calibration_window_years=0,5`** como hipótese única
   (H-novo), seguindo o padrão de `brasileirao_scripts/governanca.py` — sem mais variar
   o valor depois de registrado.
2. **Testar em dados que ainda não entraram nesta exploração** — aguardar
   jogos novos além dos 177 já usados (sincronizar via
   `brasileirao_scripts/sync_matches_from_sofascore.py` quando a temporada avançar) em
   vez de reaproveitar os mesmos 160 jogos que escolheram o candidato.
3. Continuar monitorando **Botafogo e Cruzeiro** na quebra por time — os
   únicos dois times com viés crescente e consistente nas quatro marcas,
   candidatos a um problema real e localizado (não de hiperparâmetro
   global).

## Status operacional

Brasileirão entra em **modo de observação** (mesmo regime já aplicado ao
mercado cripto): sem intervenções ativas neste teste forward. O modo sombra
continua operando automaticamente (captura ~10h, settle ~23h,
`brasileirao_scripts/sombra_diaria.py`), acumulando dados sem necessidade de
intervenção manual até a próxima marca de reavaliação.
