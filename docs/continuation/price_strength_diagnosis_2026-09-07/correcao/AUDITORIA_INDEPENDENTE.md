# Auditoria independente da correção

Resultado: **PASS**, em 08/09/2026, 02:33 UTC. A auditoria usa somente a biblioteca padrão, sem importar módulos de ajuste, previsão ou replay. Seis testes sintéticos verificaram peso interior, peso limitado, degenerescência, escalas dos scores, rejeição numérica, pagamento e separação de perdas evitadas/acertos abandonados. Nenhum novo candidato foi ajustado; nenhuma previsão de modelo foi recalculada.

Foram conferidos os hashes do plano, fontes e arquivos; a fórmula dos pesos com aritmética decimal de 50 dígitos; identidades e fronteiras temporais de 2024; janelas de características e exclusão dos pares ambíguos; igualdade da calibração antiga; probabilidades combinadas; decisões, pagamentos, Brier e log-loss de todos os braços; agregados nos painéis comum e original. Os intervalos do bootstrap não foram recalculados por este auditor.

**A melhora de saldo contra o xG calibrado anterior tem duas partes.** No mesmo conjunto de 362 jogos, passou de −65,850u para −23,373u, diferença de +42,477u. A decomposição completa inclui tanto erros quanto acertos:

| Transição da seleção anterior para a nova | Jogos | Diferença líquida |
|---|---:|---:|
| Derrota anterior → abstenção | 94 | +95,880u |
| Vitória anterior → abstenção | 43 | −85,097u |
| Outra seleção: derrota → vitória | 34 | +74,343u |
| Outra seleção: vitória → derrota | 7 | −28,033u |
| Outra seleção: vitória → vitória, com preço diferente | 11 | −14,616u |
| Outra seleção: derrota → derrota | 60 | 0,000u |
| Mesma seleção vencedora mantida | 21 | 0,000u |
| Mesma seleção perdedora mantida | 37 | 0,000u |
| Ambos abstêm | 55 | 0,000u |
| **Total** | **362** | **+42,477u** |

As 137 abstenções adicionais contribuem +10,783u líquidos; as mudanças de seleção contribuem +31,694u. São consequências contábeis dessas decisões contrafactuais, não uma explicação causal dos resultados das partidas.

**A comparação com xG raw é menos favorável.** A nova receita evitou 107 derrotas, mas também abandonou 57 apostas vencedoras: essas abstenções custaram −10,720u líquidos em conjunto. As trocas de seleção acrescentaram +13,944u; o ganho líquido total foi apenas +3,224u. O saldo bruto piorou de −19,917u para −19,973u. A redução dos custos de 6,680u para 3,400u explica todo o ganho líquido contra esse controle. O ROI ficou pior: de −7,9632% no raw para −13,7488% na nova receita.

**A quarentena teve alcance pequeno e não explica o ganho principal.** Seis jogos ficaram sem histórico mínimo; outros quatro tiveram alteração máxima de probabilidade entre 0,00000356 e 0,00000999. Não mudou a identidade nem o preço de nenhuma aposta no painel comum. A calibração de taxas em 2024 permaneceu exatamente igual.

Os pesos de xG auditados são 0 em 1X2, 0,5913381541 em OU2,5 e 0,8178670376 em ambas marcam, com 366, 246 e 247 jogos de ajuste, respectivamente. Em 1X2, a receita reproduz o mercado. Em OU2,5 e ambas marcam, permanece pior que o mercado pelos dois scores. Ambas marcam também ficou ligeiramente pior que o xG calibrado anterior. A receita não atende ao critério congelado de melhora de Brier em todos os três mercados.

A execução continua exploratória sobre 2025 já visto, com disponibilidade de xG hipotética e preços agregados retrospectivos. O resultado econômico é negativo: 170 apostas, 66 vitórias, 104 derrotas e −23,373u. A aprovação desta auditoria confirma contas e proveniência registrada; não demonstra lucro realizável, generalização futura ou prontidão para capital real.

Recibo completo: `AUDITORIA_INDEPENDENTE.json`. Plano auditado SHA-256: `2c9a6615f77c2568ecc70868ce8283f6bb6a5796c622df898bc3858927e11a92`.
