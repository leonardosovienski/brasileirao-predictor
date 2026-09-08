# Comparação de preços e candidato xG implementados

Etapa de 07/09/2026, São Paulo; execução e recibos em 08/09 UTC.

Implementado no repositório operacional, em `brasileirao_predictor/research/price_strength/`, com três comandos: `scan`, `study` e `demo`. Nenhuma dependência nova foi instalada. As mudanças permanecem locais, sem commit ou push.

## O que funciona

- **Comparação entre casas:** 1X2, over/under 2,5 e ambas marcam, sempre no jogo completo. A casa ofertante é excluída da referência; o consenso usa probabilidades sem margem de mercados completos. Os limites de idade e de diferença entre horários, referências, custo fixo e comissão são explícitos.
- **Disponibilidade temporal:** seleciona primeiro o último estado recebido até a decisão. Uma suspensão, indisponibilidade, inconsistência ou cotação vencida impede reutilizar preço anterior. O relatório preserva avaliações, rejeições, casas, horários e hashes. Um preço observado continua sem comprovação de aceitação ou limite disponível.
- **Candidato dinâmico xG independente:** combina criação e concessão recentes por mando, com decaimento temporal e aproximação a médias iniciais declaradas. Usa apenas jogos concluídos e estatísticas disponíveis antes da decisão. Não é reprodução literal do GAP nem reativação do ensemble H12.
- **Calibração cronológica:** duas escalas de intensidade de gols aprendidas em janela anterior, com previsões reconstruídas antes de cada jogo. As probabilidades de 1X2/OU/BTTS permanecem coerentes com a mesma distribuição de gols. Histórico insuficiente gera rejeição explícita.
- **Comparação probabilística:** candidato bruto e calibrado contra mercado; aceita também arquivo de previsões congeladas de outro modelo. Brier e log-loss são comparados nos mesmos jogos disponíveis por mercado. Não há ajuste automático por ROI nem alegação de teste cego retroativo.
- **Execução auditável:** arquivos JSON/JSONL fornecidos explicitamente; diretório de saída novo; leitura estrita e hashes dos mesmos bytes processados. Grava protocolo, previsões, avaliações, rejeições, resumo e manifesto de fontes/entradas/saídas.

## Validação executada

**141 testes passaram; 1 foi pulado** porque o Windows não permitiu criar um link simbólico de teste. As regressões cobrem informação futura, observação tardia, suspensão, conflitos, duplicatas, ordem das entradas, amostra insuficiente, custos, identidade dos resultados, escrita exclusiva e hashes.

Ruff, formato e Pyright dirigido aos **sete arquivos Python novos** passaram. A primeira chamada de Pyright herdou a exclusão de `research` e verificou zero arquivos; esse resultado foi descartado e substituído pela configuração explícita preservada nesta etapa. As barreiras existentes de pesquisa somente leitura e contenção de Elo corrente passaram.

Foi executada a demonstração completa com **24 partidas fabricadas**, oito alvos elegíveis de calibração e quatro partidas de avaliação. Os quatro sinais de preço são fabricados para exercitar o fluxo; não são lucro ou oportunidade no Brasileirão. A demo está em `demo/`, com recibo de execução em `demo/run/manifest.json`.

Testes e demonstração rodaram no worktree isolado, sem banco ou credenciais operacionais, com rede Python externa bloqueada. Os 14 hashes protegidos foram preservados. A suíte geral anterior não foi reexecutada; Redis/Compose continua como pendência da etapa de runtime e não é requisito deste fluxo offline.

## Uso

No PowerShell, a partir do repositório operacional:

```powershell
Set-Location 'C:\Users\Superleo13\projetos\brasileirao-predictor'
& .venv\Scripts\python.exe -m brasileirao_predictor.research.price_strength demo --output-dir 'C:\Users\Superleo13\projetos\price-strength-demo-01'
```

O diretório precisa ser novo. A demo gera os modelos de entrada `protocol.json`, `history.jsonl`, `fixtures.jsonl` e `quotes.jsonl`. O guia `GUIA.md` desta entrega detalha os comandos `scan` e `study`, campos, fórmulas e limitações. Dados reais admissíveis devem ser fornecidos em arquivos isolados; o programa não busca dados no banco operacional.

## Limite do resultado

**A implementação está validada com dados sintéticos; vantagem econômica real ainda não foi demonstrada.** Não houve coleta nova, backtest real, aposta, alteração de agenda, coorte, trial, parâmetro do baseline ou desbloqueio do scaffold PIT anterior. Os estudos encerrados e o resultado principal T2 de −1,23u permanecem preservados.

Os snapshots legados não trazem necessariamente estado completo, suspensão e todos os horários exigidos. Não existe conversão automática que invente esses campos. O próximo estudo econômico depende de observações admissíveis com essa proveniência e de um protocolo declarado antes de avaliar seus resultados.
