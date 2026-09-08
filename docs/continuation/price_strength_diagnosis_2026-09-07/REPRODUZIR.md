# Reproduzir a investigação

Operacional: `C:/Users/Superleo13/projetos/brasileirao-predictor`.

Use Python 3.14.6 e as dependências já instaladas do projeto, sem upgrades. A execução desta etapa usou um checkout descartável em `work/integration-repo`, ambiente com allowlist, bancos vazios e `work/guard/sitecustomize.py`, bloqueando acesso ao checkout operacional e conexões Python externas. Não rode a suíte inteira contra bancos reais.

## Conteúdo preservado

- `work/price_strength_diagnosis/diagnose.py`: diagnóstico dos exports encerrados, sem nova previsão.
- `prepare_correction.py`: plano de uma única receita. **Não executar por cima do estudo encerrado**.
- `evaluate_correction.py`: quarentena de características, ajuste raw/mercado em 2024, previsões e avaliação única de 2025.
- `audit_correction.py`: conferência independente de fontes, cronologia, pesos, probabilidades, decisões, pagamentos e métricas.
- `test_correction.py` e `test_model_review.py`: testes sintéticos do runner e das propriedades estruturais.
- `work/price_strength_evaluation/`: adaptador condicional e aritmética congelados da etapa anterior, sem modificações.
- `outputs/TESTE_XG_REAL/`: resultados anteriores intactos. `outputs/DIAGNOSTICO_XG/`: diagnóstico e tentativa posterior.

A cópia persistente preserva esses caminhos relativos. Os insumos privados permanecem fora do Git. O código novo/corrigido está no operacional e em `codigo/` no backup; fontes efetivamente usadas na execução foram verificadas pelos hashes do `EXECUTION_LOCK.json`.

## Verificação executada

O runner aceita um nome de recibo seguido de `--` e do comando. A partir da raiz desta cópia de trabalho:

```powershell
$pythonProjeto = 'C:/Users/Superleo13/projetos/brasileirao-predictor/.venv/Scripts/python.exe'
$testeCorrecao = Join-Path (Get-Location).Path 'work/price_strength_diagnosis/test_correction.py'
& $pythonProjeto work/validation_runner.py xg_correction_unit_tests -- $pythonProjeto -m pytest $testeCorrecao -q -p no:cacheprovider
```

O comando interno executa com cwd em `work/integration-repo`; passe caminhos absolutos para testes/scripts externos a esse checkout, como nos recibos salvos em `evidencias/`. Os recibos são a referência exata dos comandos realmente executados. `live_data_used=false` significa ausência de banco/dados operacionais ao vivo, **não dados sintéticos**: o estudo econômico usou o histórico real explicitamente listado no plano.

Para reproduzir números, crie uma nova área descartável com a mesma disposição `work/` e `outputs/`, copie as entradas e os exports antigos, e instale somente o código do snapshot em um checkout isolado com as mesmas dependências. Em `outputs/DIAGNOSTICO_XG/CORRECAO/`, copie apenas `PLANO.json` para iniciar a reprodução; os demais arquivos têm criação exclusiva e não podem ser sobrescritos. Execute o avaliador e o auditor com o runner adaptado aos caminhos da nova área. Não execute `prepare_correction.py` para reescrever o plano, não altere pesos e não use novos dados.

Compare probabilidades, IDs, escolhas e saldos com os exports preservados. Caminhos absolutos e recibos de execução podem variar; arquivos de dados, plano e cálculos científicos devem permanecer iguais. A presença do plano não torna 2025 um teste cego nem comprova disponibilidade histórica.

## API da combinação de probabilidades

O módulo puro `brasileirao_predictor.research.price_strength_reliability` expõe:

```python
fit = fit_weight(model_vectors, market_vectors, outcomes)
probabilities = blend(model_vector, market_vector, fit.weight)
```

Cada vetor tem dois ou três elementos. Em 1X2 a ordem é casa/empate/fora; OU é over/under; ambas marcam é sim/não. `outcomes` são índices inteiros das classes. O peso é compartilhado por todas as classes de um mercado. A função valida dimensões, valores e normalização; datas, IDs únicos, proveniência e separação das amostras são dever do chamador, cumpridos pelo runner congelado.

Não usar probabilidades ajustadas aos próprios rótulos como entradas de calibração e não aprender pesos com o ano avaliado. Peso zero significa mercado puro, não edge. Nenhum módulo ativa apostas, serving ou coleta. A auditoria de qualidade classifica pares zero como ambíguos; ela não transforma zero legítimo em dado faltante.
