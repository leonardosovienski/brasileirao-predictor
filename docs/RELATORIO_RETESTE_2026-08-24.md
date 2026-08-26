# Relatório de reteste read-only — 2026-08-24

Escopo: regressão e diagnóstico. Nenhum serving, modelo, cache, configuração,
threshold, trial ou banco foi alterado. 2024 e 2025 não foram carregados para
seleção ou medição nesta sessão. Capital permaneceu bloqueado.

## 1. Regressão histórica 2021–2023

Comando canônico executado:

```powershell
uv run python scripts/benchmark_predictor.py `
  --model h9-ou25-prospective-replication `
  --engine h9_frozen `
  --period 2021-01-01,2023-12-31 `
  --output <arquivo-temporario>
```

**Resultado: incidente de pipeline; identidade histórica não atestável.** O
walk-forward produziu as 940 previsões, mas o painel caiu ao calcular o estrato
T2 de 2021 com `n=7`: o bootstrap móvel exige `block_length=21` e levanta
`ValueError: series length 7 < block_length 21`. Nenhum output canônico foi
gravado.

Além disso, não existe no repositório ou documentação um relatório anterior
`h9_frozen` 2021–2023 contendo RPS, Brier, log loss e accuracy. Os artefatos
com `n=940` localizados pertencem a outros motores/controles e não são
comparáveis. Portanto não é cientificamente possível declarar “idêntico” ou
aplicar o limite de `1e-6` contra uma referência inexistente.

Como diagnóstico de causa, sem substituir o painel, as mesmas linhas globais
já produzidas pelo evaluator foram agregadas diretamente:

| Métrica | Valor global auxiliar |
| --- | ---: |
| n | 940 |
| RPS | 0,210630303919 |
| Brier 1X2 | 0,617282407778 |
| log loss | 1,029720411841 |
| accuracy | 47,1276596% |

Esses números são fallback de investigação, não uma nova régua congelada. O
painel não foi corrigido porque esta sessão proíbe alterar pipeline/modelo.

## 2. Diagnóstico 2026 atualizado

O banco operacional continua com 225 jogos encerrados em 2026 e data máxima
`2026-08-17`. Não houve observação nova desde a sessão anterior.

| Métrica | Antes, n=225 | Agora, n=225 | Delta |
| --- | ---: | ---: | ---: |
| RPS | 0,208918 | 0,208918433078 | +0,000000433078 |
| Brier 1X2 | 0,630819 | 0,630818694126 | −0,000000305874 |
| log loss | 1,044541 | 1,044540692917 | −0,000000307083 |
| accuracy | 47,11% | 47,111111% | 0,00 pp na precisão publicada |

As três diferenças contra os valores publicados de seis casas são menores que
`1e-6`; trata-se de reprodução numérica, não mudança de performance.

### T1/T2

- T1: `n=190`, accuracy 50,5263%, RPS 0,2093793, Brier 0,6145225,
  log loss 1,0222132;
- T2: `n=35`, 10 acertos, accuracy 28,5714%, RPS 0,2064166,
  Brier 0,7192836, log loss 1,1657473;
- intervalo preditivo binomial 95% sob `p=0,50`: 12–23 acertos;
- os 10 acertos continuam fora do intervalo.

Comparação: antes `n=35`, 10/35 e 28,6%; agora exatamente o mesmo. Não houve
ganho de amostra.

| Marginal T2 | Lambda média | Gols médios | Delta | IC95 do delta |
| --- | ---: | ---: | ---: | ---: |
| Casa | 1,453215 | 1,142857 | +0,310358 | [−0,035999; +0,656715] |
| Fora | 1,033955 | 1,114286 | −0,080331 | [−0,383948; +0,223287] |

Os dois ICs continuam incluindo zero. Veredito:
`RESULT_NOISE_NOT_PARAMETER_DRIFT` **mantém-se**, mas não foi reforçado nem
enfraquecido porque `n` não mudou.

### Matriz de confusão 2026

Linhas são resultado real; colunas são previsão argmax, na ordem
fora/empate/casa:

| Real \ previsto | Fora | Empate | Casa |
| --- | ---: | ---: | ---: |
| Fora | 19 | 0 | 37 |
| Empate | 16 | 0 | 51 |
| Casa | 15 | 0 | 87 |

### Lambda por resultado real

| Resultado | n | λ casa | gols casa | λ fora | gols fora |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fora | 56 | 1,317495 | 0,517857 | 1,135228 | 2,142857 |
| Empate | 67 | 1,442753 | 1,119403 | 1,043534 | 1,119403 |
| Casa | 102 | 1,499401 | 2,225490 | 0,989965 | 0,588235 |

`p_draw` médio foi 25,0218%, contra taxa real de empates de 29,7778%.
Reliability por dez faixas fixas de largura 0,1:

| Faixa | n | p_draw médio | empates reais |
| --- | ---: | ---: | ---: |
| 0,1–0,2 | 16 | 18,0958% | 31,2500% |
| 0,2–0,3 | 209 | 25,5521% | 29,6651% |

As demais faixas ficaram vazias. É diagnóstico de calibração, não threshold.

## 3. Saúde do coletor A1

O contexto “coletor em shadow” não corresponde ao runtime observado.

| Item | Estado real |
| --- | --- |
| dias acumulados | 0 |
| arquivos diários JSONL | 0 |
| snapshots | 0 |
| requests nos logs do coletor | 0 |
| orçamento mensal | 0/245 registrado |
| métricas diárias | ausentes |
| quarentenas | 0 arquivos; nenhum motivo registrado |
| tarefas `brasileirao-a1-*` | não instaladas |
| Sportingbet BR após PoC | sem snapshots posteriores |
| Pixbet após PoC | sem snapshots posteriores |

`scripts/evaluate_gate_a1.py` retornou `NOT_STARTED`, com `days=[]`, todos os
nove critérios falsos, `restart_clock_required=false`, `homologated=false` e
capital desligado. `REHEARSAL_ONLY` só será possível depois que existirem
métricas econômicas; não é o estado atual.

Hash-chain: não há arquivos diários para verificar. A propriedade “100% das
cadeias existentes íntegras” é vacuamente verdadeira, mas deve ser reportada
como **N/A (0 arquivos)**, não como homologação.

Não há evidência posterior para atualizar Sportingbet/Pixbet; a lacuna foi
registrada em `docs/COVERAGE.md`.

## 4. Integridade do repositório

- pytest: 752 passed, 1 deselected, 3 warnings numéricos conhecidos;
- Ruff: verde;
- Pyright: 0 erros, 0 warnings;
- `ci_check.py`: 5/5, incluindo smokes pré-jogo e live;
- `data/trials.json`: 26 nomes únicos, todos com status;
- snapshots com `homologated=false`: 0/0; nenhum dado chegou ao detector;
- `structural_edge.py`: nenhuma integração/importação pelo coletor;
- endpoint histórico: não exposto pelo cliente e nenhuma chamada aparece em
  logs; como não existem logs de coleta, a conclusão vale para o pipeline
  local auditado, não para acessos externos fora do repositório;
- SQLite `integrity_check`: `ok`;
- commit/push: nenhum.

## 5. Desvios explícitos

1. O prompt declarou shadow ativo, mas o runtime está `NOT_STARTED`, sem chave,
   tarefas, manifesto, snapshots ou métricas.
2. Não havia dados novos de 2026; `n=225` e T2 `n=35` permaneceram iguais.
3. O painel canônico `h9_frozen` falhou depois das 940 previsões por bootstrap
   de bloco 21 em estrato de tamanho 7.
4. Não existe referência histórica `h9_frozen` documentada com as quatro
   métricas; logo a identidade a `1e-6` não pôde ser atestada. Os valores
   globais auxiliares não foram promovidos a baseline.
5. A reliability de empate foi calculada read-only em dez faixas fixas porque
   o painel atual não materializa esse guardrail no relatório.
6. Hash-chain, coverage e quarentenas são N/A, não PASS, por ausência total de
   snapshots.
