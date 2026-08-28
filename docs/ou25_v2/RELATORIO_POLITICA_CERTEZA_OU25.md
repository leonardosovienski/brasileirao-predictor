# Política de “apostar somente quando há certeza”

## Definição implementada

“Certeza” foi convertida em uma regra auditável: o limite inferior de Wilson da
taxa calibrada, calculado somente em partidas anteriores com probabilidade
semelhante, precisa superar o break-even da odd mais 2% de fricção.

Foram avaliadas 54 políticas por braço:

- confiança: 90%, 95% e 99%;
- amostra mínima de calibração: 30, 50 e 100;
- vizinhança probabilística: ±5 e ±10 pontos percentuais;
- EV conservador mínimo: 0%, 2% e 5%;
- correção de Holm sobre todas as políticas;
- dois braços: modelo esportivo e modelo ancorado ao mercado.

## Resultado

Nenhuma política foi elegível. Capital permanece bloqueado.

| Braço | Políticas | Com algum pick | Maior `n` | Elegíveis |
|---|---:|---:|---:|---:|
| Modelo esportivo | 54 | 54 | 89 | 0 |
| Ancorado ao mercado | 54 | 9 | 7 | 0 |

O resultado nominal mais atraente do modelo esportivo teve ROI +25,63%, mas
somente 16 apostas, limite inferior −24,44% e `p_Holm=1`. No braço ancorado, o
melhor limite veio de apenas 7 apostas, ROI +21,86%, limite inferior −19,29% e
`p_Holm=1`. Nenhum deles é evidência de lucro.

## Interpretação

A blindagem funciona: quando se exige uma probabilidade inferior que ainda
pague a odd após fricção, a cobertura cai drasticamente. O modelo puro ainda
produz até 89 apostas porque é excessivamente confiante em relação ao mercado;
a âncora reduz isso para no máximo 7. Essa redução confirma que muitos EVs do
modelo eram falsos positivos.

Não existe configuração que simultaneamente apresente amostra adequada,
intervalo inferior positivo, estabilidade e significância após multiplicidade.
Logo, a política congelada continua sendo `NO_BET`, força máxima 40/100 e
capital zero.
