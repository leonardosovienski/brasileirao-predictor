# Investigação dos erros, acertos e tentativa de correção

**As correções de engenharia passaram nos testes. A nova alternativa reduziu o prejuízo simulado, mas não demonstrou lucro nem melhora geral.** A análise distingue falhas reproduzíveis, mecanismos plausíveis e resultados ocasionais. Nenhuma aposta real foi feita.

## O que explica as perdas observadas

No estudo original, o xG calibrado escolheu **125 vitórias de visitantes e acertou 13 (10,4%)**, embora atribuísse em média **23,54%** de chance a essas escolhas. A referência de mercado atribuía 16,04%. Esse grupo perdeu **59,35u**, de um saldo total de −68,70u. Nas 104 apostas com odds a partir de 5, houve dez acertos e saldo de −48,33u. Isso mostra excesso de probabilidade no conjunto selecionado; não permite descobrir uma causa tática para cada derrota.

A regra escolhe o maior retorno estimado entre mercados. Como o cálculo multiplica probabilidade pela odd, desvios de probabilidade em resultados pouco prováveis podem dominar a seleção. O modelo comprime diferenças entre equipes ao combinar uma janela curta, redução em direção à média e média aritmética de ataque/defesa; não ajusta a força dos adversários históricos. Essas são limitações verificadas no código e em exemplos sintéticos, **não uma identificação causal isolada do prejuízo**.

A calibração reduziu a taxa média prevista de gols do visitante de 1,0802 para 0,9848; a média observada foi 0,9973. Portanto ela cumpriu parcialmente seu objetivo agregado. Isso não garante probabilidades melhores para cada seleção nem retorno positivo. Em relação ao xG bruto, a diferença de **−40,733u** foi decomposta exatamente:

| Alteração de decisão | Jogos | Efeito cal−raw |
| --- | ---: | ---: |
| Troca da seleção | 44 | −25,740u |
| Aposta bruta retirada | 38 | −15,320u |
| Aposta calibrada acrescentada | 10 | +0,327u |
| Mesma aposta / nenhuma em ambos | 276 | 0u |

O Brier mede qualidade probabilística envolvendo confiabilidade e discriminação; uma redução isolada não prova calibração nem lucro. Foram usadas curvas por faixas fixas e comparações entre previsão e frequência, além do Brier. [Documentação de calibração do scikit-learn](https://scikit-learn.org/stable/modules/calibration.html), [Gneiting e Raftery, regras de pontuação próprias](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf).

## O que os acertos sustentam

Os acertos foram auditados junto com as derrotas, mantendo todas as faixas e mercados. No calibrado original, empates tiveram +5,403u em nove apostas, under 2,5 teve +1,157u em seis e ambas marcam “sim” teve +1,565u em três. São amostras pequenas demais para transformá-las em filtros vencedores.

Os cinco maiores acertos do calibrado somaram +26,40u, mas vieram todos de vitórias de visitantes, justamente o grupo que mais perdeu no agregado. Logo, acertar algumas surpresas não valida apostar sistematicamente nelas. No xG bruto, mandantes tiveram +10,97u em 79 apostas; esse resultado foi preservado como diagnóstico, sem escolher uma política “somente mandantes” depois de vê-lo.

Probabilidades médias entre acertos e erros ajudam a descrever separação, mas a taxa de 100% nos acertos e 0% nos erros é consequência da divisão. A origem dos gols, escalações, expulsões, finalizações e outros mecanismos de cada partida não foram investigados com novas fontes; não inventamos explicações individuais.

## Falhas concretas corrigidas

1. **Cobertura de xG confundida com validade.** Todos os 380 jogos de 2021 têm ambos xG zero. A auditoria anterior contava qualquer valor não nulo como “válido”. A versão atual separa presença, valor numérico, ausência, par incompleto, valor inválido e par zero sem origem atestada. Os nomes antigos permanecem como aliases documentados de presença, para compatibilidade.
2. **Leitura de xG aceitava outra estatística ou valores inválidos.** O parser podia tomar “Expected goals on target” como xG, aceitar negativos, NaN e booleanos, ou escolher a primeira de duas observações conflitantes. Agora exige identidade e período corretos, par numérico finito não negativo e duplicatas consistentes. Zero reportado continua sendo zero; não é reescrito globalmente como ausente.
3. **Conflitos entre revisões dependiam da ordem.** Uma revisão mais recente podia ocultar dois registros antigos incompatíveis no mesmo horário. A validação agora considera todas as revisões visíveis, independentemente da ordem, mantendo o bloqueio a informações futuras.

Esses defeitos foram reproduzidos antes do reparo. Não há evidência de que as falhas do parser/revisões tenham produzido os saldos históricos; corrigir o código não reconstitui payloads ausentes. A cadeia de extração examinada também não comprova quem gerou os zeros de 2021.

## Tentativa delimitada e resultado

Foi congelado um novo plano antes do ajuste e das novas métricas, SHA-256 `2c9a6615f77c2568ecc70868ce8283f6bb6a5796c622df898bc3858927e11a92`. É uma investigação posterior ao diagnóstico de 2025 já visto, não um novo teste cego. Os estudos anteriores permanecem encerrados e seus arquivos não foram reescritos.

A alternativa combina duas intervenções explícitas:

- Quarentena uniforme de pares xG zero ambíguos somente no histórico de características. Os valores originais permanecem intactos; o xG do próprio alvo não decide se seus gols podem ser avaliados.
- Combinação convexa de **xG bruto temporal com mercado sem margem**, com pesos aprendidos uma vez somente em 2024. As entradas não usam a calibração de gols ajustada aos próprios rótulos de 2024. Os pesos ficam fixos durante 2025; não foram escolhidos por lucro.

| Mercado | Peso aprendido do xG | Observações de ajuste em 2024 |
| --- | ---: | ---: |
| Vitória/empate/derrota | 0% | 366 |
| Over/under 2,5 | 59,13% | 246 |
| Ambas marcam | 81,79% | 247 |

Em 1X2, a alternativa reproduz exatamente o mercado e deixa de gerar as apostas baseadas em divergência do xG nesse mercado. Isso não demonstra informação adicional do xG. As probabilidades finais são válidas por mercado, mas não representam uma única distribuição conjunta de placares.

A quarentena afeta dez previsões de 2025 e **nenhuma entrada da calibração de taxas de 2024**, cujos resultados ficaram exatamente iguais. Seis jogos deixam de atingir o mínimo de três observações por mando; nos quatro restantes as diferenças numéricas são mínimas. **No conjunto comum, a quarentena sozinha não altera nenhuma seleção ou pagamento.** Sua contribuição foi corrigir qualidade e elegibilidade, não explicar a melhora financeira.

Dos 380 jogos de 2025, o painel original tinha 368; o novo painel comum tem **362**. Todas as linhas abaixo usam exatamente esses mesmos jogos, preços, filtros e custo de 0,02u por aposta, com uma unidade fixa e no máximo uma aposta por jogo.

| Candidato | Apostas | Acertos / erros | Saldo simulado | ROI |
| --- | ---: | ---: | ---: | ---: |
| Anterior bruto, ajustado até 2024 | 293 | 83 / 210 | −39,811u | −13,59% |
| xG bruto original | 334 | 100 / 234 | −26,597u | −7,96% |
| xG calibrado original | 307 | 82 / 225 | −65,850u | −21,45% |
| Nova combinação com mercado | 170 | 66 / 104 | **−23,373u** | **−13,75%** |

A nova alternativa perde **42,477u menos que o calibrado**, reduzindo a exposição de 307 para 170 apostas. Contra o bruto, perde apenas 3,224u menos e tem **ROI pior**. O drawdown cai de 71,945u no calibrado para 27,021u. Menos perdas absolutas com menos apostas não equivalem a uma estratégia lucrativa.

A comparação com o bruto é ainda mais limitada: o saldo **antes dos custos piora** de −19,917u para −19,973u. A melhora líquida de 3,224u vem de economizar 3,280u de custos com 164 apostas a menos, descontada essa pequena piora bruta. Não houve melhora do pagamento bruto frente a esse controle.

### Acertos preservados e oportunidades abandonadas

A auditoria independente rastreou todas as transições da nova alternativa contra o xG calibrado, nos mesmos 362 jogos:

| Transição | Quantidade | Efeito líquido da mudança |
| --- | ---: | ---: |
| Derrotas retiradas | 94 | +95,880u |
| Apostas vencedoras retiradas | 43 | −85,097u |
| Troca de derrota por vitória | 34 | +74,343u |
| Troca de vitória por derrota | 7 | −28,033u |
| Troca entre duas apostas vencedoras | 11 | −14,616u |
| Troca entre duas apostas perdedoras | 60 | 0u |
| Mesma aposta: 21 acertos e 37 erros | 58 | 0u |

As 137 abstenções acrescentam 10,783u e as 112 trocas acrescentam 31,694u, totalizando 42,477u. A alternativa **também abandona acertos**, não apenas evita erros. Essas categorias foram calculadas depois da decisão, para explicar o resultado; não alimentaram o ajuste dos pesos.

Contra o xG bruto, foram evitadas 107 derrotas, mas retiradas 57 apostas vencedoras: o efeito líquido dessas abstenções foi **−10,720u**. Isso reforça que uma regra que reduz apostas não preserva automaticamente as oportunidades boas. Nenhum desses grupos foi convertido em filtro após o resultado.

O arquivo `CORRECAO/original_panel_results.json` conserva também os 368 jogos originais, incluindo as seis novas abstenções. Ele impede atribuir a retirada de jogos à melhora das probabilidades. Nesse painel completo, os novos saldos são os mesmos porque não há apostas nessas seis fixtures; os resultados anteriores permanecem −68,70u no calibrado e −27,967u no bruto.

## Qualidade preditiva depois da tentativa

Brier médio, menor é melhor; comparar dentro de cada linha, sem misturar a escala de três classes com a binária.

| Mercado | xG calibrado original | Nova combinação | Mercado sem margem |
| --- | ---: | ---: | ---: |
| Vitória/empate/derrota | 0,600756 | **0,579597** | **0,579597** |
| Over/under 2,5 | 0,250996 | 0,246122 | **0,242387** |
| Ambas marcam | 0,251471 | 0,251864 | **0,249014** |

O log loss apresenta a mesma direção. A alternativa melhora 1X2 e OU frente ao calibrado e piora ligeiramente ambas marcam. Frente ao mercado, empata em 1X2 e perde nos dois mercados binários. Por isso, **não houve melhora geral nem vantagem demonstrada sobre o mercado**.

O bootstrap pareado de 33 semanas, com 2.000 reamostragens, produz intervalo descritivo de 95% de [−0,0253; +0,2455]u para a diferença de saldo por jogo contra o calibrado. Inclui zero. Não há correção das buscas anteriores ou da incerteza de ajuste; não é confirmação de vantagem futura.

## Limites e evidências

As observações de xG continuam condicionais à hipótese de disponibilidade após 48 horas. As odds de 2024 e 2025 são agregadas retrospectivas, sem comprovação de casa, horário da oferta ou aceitação. A comparação entre casas continua sem dados elegíveis. Não houve acesso ao banco operacional, resultados protegidos, alteração de agendas ou liberação de capital.

As verificações de código dirigidas passaram: **318 testes aprovados e um teste de symlink não executado por restrição do Windows**; mais seis testes do novo runner, quatro testes estruturais e seis do auditor independente. Ruff, formato, Pyright nos cinco módulos alterados/novos e barreiras estáticas passaram. Não foi repetida a suíte geral nem resolvida a pendência Redis/Compose desta etapa anterior.

O diagnóstico completo está em `ACHADOS.md` e `diagnostico.json`. O plano, ajuste, previsões, decisões, métricas, bloqueios de execução e hashes estão em `CORRECAO/`. A auditoria independente de fontes, pesos, decisões e pagamentos passou; uma segunda implementação confirmou as 28 estatísticas e intervalos do bootstrap em 95 verificações. Os recibos são `CORRECAO/audit.json` e `CORRECAO/bootstrap_audit.json`; `estado.json` registra a preservação dos 14 hashes protegidos. Código de correção local; sem commit, push ou promoção do candidato.
