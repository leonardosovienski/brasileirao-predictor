# OU2.5 anual — lucro ou prejuízo de 2021 a 2026

Data de corte: 27/08/2026. Unidade: uma unidade por aposta.

## Resultado

| Temporada | Jogos com preço e previsão válidos | Contrafactual “apostar sempre” | ROI | Limite inferior 95% | CLV médio | Política v2 governada |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 180 | −31,630 u | −17,57% | −30,77% | indisponível | 0 apostas / 0,000 u |
| 2022 | 380 | −40,470 u | −10,65% | −19,95% | indisponível | 0 apostas / 0,000 u |
| 2023 | 380 | −32,360 u | −8,52% | −19,06% | indisponível | 0 apostas / 0,000 u |
| 2024 | 149 | −0,154 u | −0,10% | −16,84% | +11,64% | 0 apostas / 0,000 u |
| 2025 | 374 | +89,450 u | +23,92% | +13,20% | +16,83% | 0 apostas / 0,000 u |
| 2026 parcial | 219 | +0,123 u | +0,06% | −11,36% | +8,49% | 0 apostas / 0,000 u |

Total do contrafactual: **−15,041 unidades em 1.682 apostas**. O total mistura fontes de preço diferentes e é apenas descritivo. A política v2 efetivamente autorizada fez zero apostas e terminou em zero.

## Como ler 2025

2025 foi positivo no replay e continuou positivo no limite inferior e após Holm entre os seis testes anuais. Porém, isso **não libera capital**:

- a temporada já havia sido aberta/observada e está marcada como contaminada;
- as odds são aberturas retrospectivas agregadas do SofaScore, não snapshots A1 executáveis de uma casa nominal;
- o próprio histórico do projeto já identificou risco de “abertura-fantasma”: preço histórico disponível no feed não significa preço capturável pelo apostador;
- a regra governada v2 foi congelada como `NO_BET`, sem candidato elegível.

O resultado de 2025 é uma hipótese para réplica prospectiva, não uma autorização de aposta.

## Qualidade dos dados

- 2021 usa somente 180 jogos porque os primeiros 200 formam o burn-in mínimo do modelo walk-forward.
- 2021–2023 usam médias históricas agregadas de múltiplas casas, sem horário executável e sem CLV.
- 2024 possui apenas 149 pares de odds recuperáveis no feed atual.
- 2025 possui 374 pares válidos.
- 2026 é parcial: 235 jogos encerrados no banco e 219 pares válidos após o gate.
- Dezesseis pares de 2026 com placeholders `51,0 / 1,002` foram rejeitados. Sem a correção, o ROI falso seria +140,9%.
- 2024, 2025 e 2026 permanecem dados observados/contaminados.

## Metodologia

- Probabilidades esportivas produzidas em ordem temporal, sem usar o resultado do próprio jogo.
- Mesma regra contrafactual em todos os anos: uma unidade no lado Over/Under com maior EV bruto do modelo; não há escolha anual de threshold.
- Mercado comparado por probabilidade de-vigada.
- CLV, quando possível, usa odd tomada × probabilidade justa de fechamento de-vigada − 1.
- IC de retorno por bootstrap temporal em blocos.
- Correção de Holm aplicada aos seis testes anuais.
- Perdas individuais preservadas em CSV.
- Capital desabilitado e indicação limitada a 40/100 até A1 prospectivo.

## Conclusão

O resultado combinado não comprova lucro. Três anos perderam materialmente, 2024 ficou próximo de zero com incerteza ampla, 2026 ficou praticamente em zero e 2025 foi um achado retrospectivo forte porém contaminado. A decisão segura e metodologicamente correta continua sendo **NO_BET**, mantendo 2025 como hipótese congelada para validação prospectiva A1.
