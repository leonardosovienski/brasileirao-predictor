# Recuperação Python de resultados ainda válidos

Etapa de 2026-09-08. Alteração mecânica no transporte Redis v2; nenhuma fórmula, parâmetro, dado operacional, coorte ou dependência foi alterado por este patch.

## Contrato

`kernel:v2:ready` é um ZSET cujo membro é `run_id` e cujo score é o vencimento absoluto real de `fair_odds:{match_id}`, obtido por `PEXPIRETIME` na mesma execução Lua que grava a resposta. A validade permanece `min(5000 ms, PTTL(request))`. Redis 7 ou posterior é necessário para os comandos usados; a instância de teste é Redis 8.2.1.

`COMPLETE_SCRIPT` recebe sete chaves, nesta ordem: current, request, lease, fair, pending, lineup, ready. Os argumentos são payload, run, token, fair_json, fair_ms e canal. Antes de mutar, verifica tipos, ACLs das operações seguintes, current/request/snapshot exatos, lease próprio e validade do pedido. Após gravar fair e seu índice, registra `status=completed` e `result`, remove pending e lease, e tenta a notificação PubSub. Uma falha inesperada da notificação deixa o resultado concluído e localizável; não reabre cálculo nem renova sua validade.

A repetição de completion concluída não recria odds, não reinsere o índice nem renova o TTL. Se as odds venceram ou deixaram de corresponder ao resultado, remove somente o membro dessa execução. Completion antiga/expirada também limpa somente seu membro, sem retirar uma execução nova. Os produtores e consumidores .NET devem remover o membro substituído/consumido e usar o índice para descobrir resultados ainda válidos, submetendo-os às mesmas verificações finais e deduplicação do caminho PubSub.

O índice elimina a dependência exclusiva do aviso `fair_odds_ready` enquanto a janela original estiver aberta. Não amplia essa janela, não é confirmação de recepção financeira e não promete execução financeira exatamente uma vez. Reinício/queda do próprio Redis sem persistência ou OOM durante mutações não ganha garantia transacional de rollback por este patch.

## Validação isolada

Recebimentos e conclusões são sintéticos. A suíte não leu banco de modelos nem executou apostas ou backtests.

- `validation/python_ready_red`: a nova regressão falhou no código anterior porque o resultado concluído não tinha entrada no índice.
- `validation/python_ready_unit`: 139 testes passaram.
- `validation/python_ready_redis_green`: 24 testes passaram em Redis real 8.2.1, DB 14, incluindo aviso perdido, prazo idêntico ao `PEXPIRETIME`, replay sem renovação, expiração, substituição de execução, tipo inválido e ACLs insuficientes antes de qualquer escrita de fair/index.
- `validation/python_ready_format`: seis arquivos sem mudanças de formatação; `python_ready_lint`: Ruff aprovado; `python_ready_pyright`: zero erros, avisos ou informações.

O wrapper validou antes/depois a instância criada para esta etapa (`run_id=273e80f8cca2bcfdf62f19e6244aabc4dc5ecd06`, loopback 26380). A limpeza removeu apenas chaves/membros sintéticos próprios, sem FLUSH; DB 14 terminou vazio. Cada execução possui recibo JSON e log no diretório `validation`. Esses testes demonstram o lado Python/Lua; a recuperação de um processo MSE reiniciado e a deduplicação do batch são validadas separadamente pelos testes .NET.

## Integridade

`python_before.json` preserva os hashes anteriores, capturados antes da edição. `python_after.json` registra os hashes finais e comprova igualdade byte a byte entre fonte operacional e cópia isolada dos seis arquivos verificados. Nesta etapa mudaram `kernel_daemon.py`, `kernel_redis_v2.py`, `test_kernel_v2_runtime.py` e `test_redis_integration.py`; os outros dois arquivos de teste mantiveram seus hashes. Recibos e snapshots da etapa anterior não foram alterados.
