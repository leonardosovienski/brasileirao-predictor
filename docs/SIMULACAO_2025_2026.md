# Simulação 2025 + 2026 (17 rodadas) — diagnóstico e melhoria (2026-07-16)

> Pergunta do operador: "simula os jogos do ano passado e as 17 rodadas deste
> ano, veja por que está ruim e tenta melhorar."
> Reprodutível: `scripts/sim_2025_2026.py` (baseline + diagnóstico) e
> `scripts/sim_melhorias.py` (candidatos; `--valida` = escolha de
> hiperparâmetros em 2024-H2). Banco read-only; walk-forward mensal sem
> lookahead (Elo forward, calibração só com jogos anteriores ao mês).

## O baseline em números (por que "está ruim")

| Métrica | 2025 (380 j) | 2026 (177 j) | Mercado (Shin fech.) |
|---|---:|---:|---:|
| 1X2 acerto | 50,5% | 49,7% | 53,5% / 51,4% |
| 1X2 Brier | 0,5998 | 0,6217 | 0,5808 / 0,5971 |
| OU2.5 Brier | 0,2469 | 0,2512 | 0,2436 / 0,2484 |
| probMax média | 49,1% | 50,0% | 50,8% / 50,2% |
| λ_total (média±dp) | 2,44±0,12 | 2,50±0,12 | gols reais 2,52 / 2,66 |

Diagnóstico (confirma e refina o que os docs da Copa já apontavam):

1. **O modelo NÃO está descalibrado — está sem resolução.** A curva de
   calibração do pick é quase perfeita (conf ~40%→38,8% real, ~50%→51,6%,
   ~60%→61,5%, ~70%→71,8%). O problema é que ele raramente sai da zona dos
   40-55% de confiança: probMax média 49%, λ_total praticamente constante
   (dp 0,12). Ele sabe *quanto* sabe; ele só sabe *pouco*.
2. **Empate nunca é o pick** (0 em 557 jogos) — mas P(empate) média 25-26%
   vs 26-27% real: calibrado na média. O mercado também quase nunca tem
   empate como moda; o custo em Brier é pequeno. Não é a alavanca.
3. **O escalar único (ΔElo) não representa times assimétricos.** Botafogo
   2026: +8,3 gols feitos E −11,6 sofridos vs o esperado — time de ritmo
   alto que um único rating não descreve (ataque forte ≠ defesa forte).
   Mesmo padrão em Athletico (+3,7/+6,6) e Cruzeiro (−0,1/−6,7).
4. **Times promovidos entram superestimados** (Elo inicial 1500 = média da
   liga): 2025, o modelo esperou 191 pts dos 4 promovidos e vieram 174
   (+17 de erro); 2026 quase neutro (+3). Efeito real mas secundário.
5. **No Brasileirão o mercado também é achatado** (probMax 50-51% vs 66% na
   Copa) — a liga é equilibrada. O gap modelo−mercado aqui é ~0,02 de
   Brier, não o abismo da Copa. Ou seja: dá para encostar.

## Candidatos testados (protocolo anti-snooping)

Hiperparâmetros escolhidos por validação interna em **2024-H2** (walk-forward
ago–dez/2024), congelados, e só então avaliados em 2025+2026 — os dados de
teste não participaram da escolha. Comparação pareada por jogo, bootstrap
2000 iterações, seed 13.

| Candidato | O que muda | dBrier 1X2 (2025+2026) | IC95 |
|---|---|---:|---|
| C1 força-única batch (hl=0,75a, reg=10) | Poisson-ridge batch, 1 força/time | −0,0040 | [−0,0095, +0,0019] |
| C2 atk/def batch (hl=0,75a, reg=10) | 2 params/time, gols | −0,0021 | [−0,0084, +0,0047] |
| C3 atk/def **xG** (w=0,85, reg=1) | força estimada em 0,85·xG+0,15·gols; α/ρ nos gols reais | −0,0093 | [−0,0190, +0,0015] |
| **C4 ensemble 50/50 (baseline+C3)** | média das probabilidades | **−0,0073** | **[−0,0122, −0,0019] ✅** |

O C4 é significativo **também em cada ano isolado**: 2025 [−0,0105, −0,0001],
2026 [−0,0223, −0,0008]. Acerto 1X2: 50,3% → **52,1%** (C3 puro: 52,8% =
acerto do mercado). LogLoss idem (−0,0098, IC fechado). **OU2.5 não degrada**
no ensemble (dBrierOU +0,0008, IC cruza zero) — importante porque OU2.5 é a
única população com CLV validado (H1).

### Por que funciona

- O xG tem ~metade do ruído do gol como medida de força (corr xG→gol 0,53;
  média não-viesada: 1,45 xG vs 1,49 gols mandante). Estimar ataque/defesa
  em xG e reservar os gols reais para dispersão (α) e Dixon-Coles (ρ) usa
  cada dado no que ele é bom.
- Ataque/defesa separados dão ao modelo o que o ΔElo não tem: λ_total que
  varia por confronto (dp 0,31 vs 0,12) — exatamente o eixo do diagnóstico #3.
- O ensemble corta a variância dos dois estimadores (online vs batch) —
  por isso fecha significância onde o C3 sozinho ainda oscila.
- Confirma a previsão de `docs/CONCLUSOES.md`: xG é **informação nova** que
  o Elo não vê (≠ atk/def puro em seleções, que era o mesmo dado
  reorganizado e não agregou).

### O que NÃO funcionou / não move

- C1/C2 (batch em gols, sem xG): direção certa, nunca significativo — o lead
  "estimador batch" da Copa não se replica aqui porque o Elo do Brasileirão
  atualiza a cada rodada (na Copa ele ficava congelado no torneio).
- `form_half_life_years`: já refutado em
  `docs/RELATORIO_FORWARD_18JOGOS_2026-07-12.md`; não retestado.
- Empate como pick: inatacável por esta via — nenhum candidato muda a moda.

## Ressalvas honestas

1. **Seleção de grid**: C3 saiu de um grid (w, reg, hl) validado em 2024-H2.
   O teste 2025+2026 é fora-da-seleção, mas o *ensemble 50/50* foi decisão
   a posteriori (peso não foi otimizado — 50/50 era o default natural; pesos
   alternativos NÃO foram varridos).
2. Isto melhora **previsão** (Brier/logloss), não prova **edge de aposta**.
   Para virar dinheiro precisa passar pelo funil de governança: registrar
   como hipótese nova (padrão `scripts/governanca.py`) e medir CLV/ROI
   forward — o mesmo tratamento do candidato `calibration_window_years=0,5`.
3. xG do Sofascore chega **pós-jogo** — para serving pré-jogo isso não é
   lookahead (usa xG de jogos passados), mas exige o sync rodando em dia.
4. O mercado continua na frente no Brier agregado (0,586 vs 0,599 do C4);
   C3 empatou em acerto (52,8%). O gap caiu de ~0,021 para ~0,013 (C3 puro:
   ~0,011).

## Recomendação

1. **Adotar o C4 (ensemble) como candidato de serving** atrás de flag/config,
   mantendo o baseline como está para as hipóteses pré-registradas em curso.
2. Pré-registrar (H-novo) o efeito do C4 no funil OU2.5/CLV em modo sombra —
   sem tocar em H1/H3.
3. Leads menores, em ordem: prior negativo para promovidos (~17 pts de erro
   em 2025), peso do ensemble, λ_total dependente de confronto no OU.
