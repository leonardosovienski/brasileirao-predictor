# Correção do código de saída da CLI

Em 2026-09-08 o teste de processos completos do root revelou que `python -m brasileirao_predictor.kernel_daemon --healthcheck` terminava com código 0 mesmo quando `main()` retornava 1. O guard do módulo chamava `main()` sem propagar seu retorno ao sistema operacional. As verificações diretas da função e do Lua não cobriam esse limite de processo.

A correção de runtime foi somente trocar a chamada final por `raise SystemExit(main())`. O retorno normal do daemon (`None`) continua produzindo saída 0. O healthcheck agora produz saída 1 quando não há heartbeat válido. Fórmulas, TTLs e scripts Redis não mudaram.

O novo `tests/test_kernel_cli_redis.py` invoca o módulo em subprocesso real, sem stub de `main()`, e verifica os três estados: heartbeat ausente (saída 1), sessão sintética saudável (saída 0) e heartbeat efetivamente expirado (saída 1). O caminho de banco fornecido é absoluto, temporário e inexistente; permanece inexistente após a verificação. Os subprocessos herdam o ambiente isolado do runner.

## Evidências novas

- `validation/python_entrypoint_red_missing`: antes da edição, DB14 vazia e heartbeat comprovadamente ausente; regressão falhou porque o processo retornou 0 quando deveria retornar 1.
- `validation/python_entrypoint_green`: os três testes passaram após a correção.
- `validation/python_entrypoint_format` e `validation/python_entrypoint_lint`: Ruff aprovado; apenas o teste novo precisou ser formatado.
- O primeiro recibo `python_entrypoint_red` não é prova de regressão: omitiu `-m integration` e selecionou zero testes. Foi mantido para transparência; a execução seguinte corrigiu a seleção antes da edição de runtime.

Todas as execuções usaram Redis 8.2.1 exclusivo, loopback 26380/DB14, com run_id verificado antes/depois. O teste exige banco inicialmente vazio e remove somente sua chave `health:kernel`, após nova confirmação de identidade. DB14 terminou vazia; nenhum FLUSH, modelo, banco real, aposta ou backtest foi executado.

`python_entrypoint_after.json` contém os novos hashes e a igualdade entre fontes operacionais e isoladas. O snapshot anterior `python_after.json` foi preservado, sem reescrita. A validação de hosts completos será refeita separadamente pelo root com estas fontes.
