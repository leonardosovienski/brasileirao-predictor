# Hipóteses versus assinaturas de erro atuais — 2026-08-26

## Escopo e governança

Esta análise procura mecanismos em dados liberados para desenvolvimento. Ela não
usa 2025/2026 para escolher hipótese. O painel 2021–2024 já foi visto em trials
anteriores; portanto os resultados abaixo são diagnóstico e geração de candidato,
não confirmação. H14 prospectiva permanece separada.

### Multiplicidade da família de cadência

“Por rodada” e `retrain_every=10` são o mesmo tratamento. A busca em código,
relatórios e histórico encontrou somente dois valores realmente avaliados no
painel canônico: **10 e 100 jogos**. Não houve sweep documentado de outras
cadências. Porém o contraste 10-vs-100 foi lido **duas vezes na mesma amostra**:
H11 original e H11-v2 depois das correções de algoritmo. Portanto H11-v2 é a
segunda olhada da família, não uma confirmação independente.

Como sensibilidade, um Bonferroni simples para duas leituras troca o IC95 nominal
do delta RPS por IC simultâneo de 97,5%: `[-0,004249;-0,000334]`, ainda favorável.
Isso não recupera cegamento nem independência e não autoriza promoção. O Track A
não tinha um ledger de multiplicidade equivalente ao DSR do Track B; essa
assimetria fica agora explicitamente registrada.

## Verificação v1 × v2

O pareamento direto contém 1.320/1.320 eventos e zero órfãos. Houve **zero flips
de argmax** e zero mudanças de acerto, embora as probabilidades tenham mudado: o
maior deslocamento absoluto de uma célula foi 0,030684 e a média do maior
deslocamento por jogo foi 0,001537. Logo o IC95 `[0;0]` da accuracy é correto: a
série jogo a jogo de deltas de acerto é literalmente toda zero, não cancelamento
de flips opostos. Hashes e contagens estão no manifesto pareado.

## Assinatura do erro do serving corrigido

Em 2021–2024 (`n=1.320`), o argmax escolheu casa em 1.089 jogos, fora em 231 e
empate em **zero**. Dos 356 empates reais, 278 foram classificados como casa e 78
como fora. Isso não prova que forçar empate melhora a decisão: a regra histórica
“placar modal empatado → empate” já perdeu. A assinatura correta é falta de
**resolução/calibração condicional do empate**, não mero threshold categórico.

## Comparação por hipótese

| Hipótese/intervenção | O que melhorou | O que piorou/não resolveu | Leitura atual |
| --- | --- | --- | --- |
| Correções v2 de invariantes | Pequenos ganhos médios em RPS/Brier/log loss | 0 flips; ICs agregados v2−v1 cruzam zero | correção matemática, não upgrade histórico |
| H12: desligar ensemble xG | Melhora robusta global: ligar novamente piora RPS `+0,004485`, IC95 `[+0,001563;+0,007962]`; também piora Brier e log loss | O xG ligado melhora muito os empates isoladamente, mas destrói lados corretos | melhora descritiva robusta e já aplicada; a confirmação não foi cega |
| H11-v2: refit 10 vs 100 após as correções | RPS `−0,002230`, IC95 `[−0,004006;−0,000583]`; IC Bonferroni 97,5% para duas leituras `[-0,004249;−0,000334]`; 103 flips laterais e +14 acertos | Continua com zero argmax de empate; segunda leitura do mesmo contraste/amostra | diagnóstico retrospectivo N+1 `inconclusiva`; H15 futura foi pré-registrada separadamente |
| A02 força dinâmica | Melhora perdas dos resultados fora e produz 20 acertos fora adicionais | Piora empates fortemente (Brier `+0,018754` nos empates), perde 26 acertos de casa; agregado pior e IC cruza zero | refutada; não reutilizar para o erro atual |
| A10 calibração binária de empate | Nenhuma melhora validada | Em 2024 piora Brier-draw `+0,000156`, RPS `+0,000025`, Brier e log loss; todos ICs cruzam zero; 0 flips | **NO-GO**; falta de resolução não é corrigida por intercept/slope global |
| `rho=0` | Sinal minúsculo na mesma direção em desenvolvimento e 2024 | Todos os ICs cruzaram zero | inconclusiva e pequena demais para explicar o erro |
| temperature `0,9` | Melhorou perdas em desenvolvimento | Piorou todas em 2024 e subestimou empate | NO-GO |
| multiplicador direto de empate | `0,95` melhorou RPS quase zero | piorou log loss; boost de empate foi pior | NO-GO |
| ataque/defesa simples | Melhorou desenvolvimento a 25% | piorou todas as métricas em 2024 | NO-GO |
| ambiente de gols/mando/K/meia-vida/prior de promovido | alguns sinais locais em desenvolvimento | não repetiram em 2024 ou o incumbent venceu | NO-GO conforme registro |
| MARKET-02/03 | nenhum ganho preditivo estável do residual | modelo perdeu para abertura/mercado; nicho de empate não foi monotônico | não corrige o motor esportivo |

## Resultado da busca

Duas conclusões sobrevivem:

1. **H12 já corrigiu um erro real:** retirar o ensemble xG foi uma melhora robusta
   global. O fato de ele ter ajudado empates mostra a região do erro residual, mas
   o componente é amplo demais e não deve voltar. Esse resultado sugere uma
   hipótese futura diferente: sinal novo atuando somente na dimensão
   empate/não-empate, preservando a razão casa:fora. Ela ainda não está congelada
   como trial porque precisa de mecanismo e arquitetura novos; não é reabertura de
   H12 nem novo blend do ensemble.
2. **H11-v2 é a única candidata nova com ganho robusto no painel corrigido:** refit
   mais frequente melhora principalmente confusões casa↔fora. Como esse contraste
   foi reaberto depois das correções e usa história já observada, serve para
   gerar a H15 prospectiva, não para mudar o serving agora. O resultado
   retrospectivo foi registrado como `inconclusiva`, nunca `comprovada`.

Nenhuma hipótese registrada resolveu a ausência de resolução de empate sem dano
global. A A10 estreita também falhou. A próxima hipótese de empate só deve ser
aberta com mecanismo novo — por exemplo regime PIT de baixa pontuação ou modelo
alternativo de dependência de gols — e não com novo sweep de threshold/boost sobre
os mesmos dados.

## Artefatos reproduzíveis

- `reports/comparison_serving_v2_minus_v1_2021_2024.json`
- `reports/error_signature_h11_2021_2024.json`
- `reports/error_signature_a02_2021_2023.json`
- `reports/error_signature_h12_xg_on_2021_2024.json`
- `reports/trial_draw_calibration_a10_2024.json`
- `scripts/export_version_losses.py`
- `scripts/compare_hypothesis_errors.py`
- `scripts/trial_draw_calibration_a10.py`
