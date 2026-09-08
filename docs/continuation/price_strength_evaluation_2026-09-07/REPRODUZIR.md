# Reprodução do diagnóstico condicional

Este estudo foi executado uma vez. Reproduzir os mesmos cálculos não autoriza mudar seus parâmetros nem reabrir a busca encerrada. Não executar o runner sobre arquivos operacionais ou coortes protegidas.

O backup independente `C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07/price_strength_evaluation_2026-09-07/` preserva:

- `outputs/`: plano, previsões, painel, resultados por evento, agregados, auditoria e recibos.
- `reproducao/`: `conditional_model.py`, `evaluate.py`, `frozen_economics.py`, auditor e testes.
- `inputs/`: os quatro arquivos históricos exatos usados, somente fora do Git.
- `candidate_code/`: cópia da implementação do candidato; o SHA de `dynamic_xg.py` é exigido pelo runner.
- `validation/`: comandos e logs da execução isolada, além do guard e runner utilizados.

Para uma reprodução, use uma pasta nova com esta estrutura relativa:

```text
<nova-raiz>/work/price_strength_evaluation/     programas de reproducao/
<nova-raiz>/work/price_strength_evaluation/inputs/  quatro insumos
<nova-raiz>/work/price_strength_evaluation/plan.json  cópia exata de outputs/PLANO.json
<nova-raiz>/outputs/TESTE_XG_REAL/PLANO.json    mesma cópia exata
```

Use checkout isolado com o pacote `candidate_code/` e o ambiente Python preservado do projeto; disponibilize esse checkout no `PYTHONPATH`. Reaplique o guard e a allowlist de ambiente do runner de validação. Os scripts importam somente o candidato matemático e o módulo de contabilidade congelado; não precisam de banco, credenciais ou rede. A execução original usou Python 3.14.6.

Primeiro execute `pytest` sobre `test_conditional_model.py` e `test_evaluate.py`. Depois execute `evaluate.py` e `audit.py`. Ambos usam exclusivamente os insumos explícitos sob a estrutura acima; `evaluate.py` verifica o hash do plano, dos dados, do candidato e da contabilidade. As saídas são exclusivas e uma reprodução não pode sobrescrever a execução original.

Não rode `prepare_plan.py` para reproduzir: ele foi usado para a preparação original e carrega os caminhos originais. O plano já congelado deve ser copiado byte a byte. Compare métricas e previsões determinísticas; os registros de horário/local de execução podem diferir. Não transforme o lag hipotético de 48h em timestamp observado nem as previsões retrospectivas em emissões pré-jogo.
