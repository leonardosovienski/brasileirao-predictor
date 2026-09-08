Preparação concluída em 08/09/2026, 12:31 UTC. Esta etapa validou configuração e fixtures offline; não iniciou Docker, containers, Redis ou distros. Não alterou fontes da aplicação, outputs anteriores ou backups.

O estado encerrado em `outputs/PENDENCIAS_CORRIGIDAS/estado.json` foi lido e confrontado com o repositório live. Os 36 arquivos declarados correspondem aos hashes registrados; os 35 arquivos de runtime/testes/configuração coincidem também com o checkout isolado. O Markdown do contrato mantém a exceção documental registrada. `pyproject.toml` e `uv.lock` também foram confrontados, sem alteração. Recibo: `harness/manifest.json`.

Foi corrigida somente a nova fixture: o harness anterior tinha `replacement`, mas `VorpStateService.StartAsync` exige `replacement_levels`. A nova cópia usa o campo correto. A checagem limitada confirmou que `docker/vorp.json:1` já estava correto, `compose.yaml:61` monta esse diretório e o CI usa esse Compose sem gerar outro VORP. Não há correção necessária no Compose original ou no CI por esse motivo. A fixture anterior foi preservada.

O parser Compose aprovou `harness/compose.yaml`. O pós-check inicial esperava `false` explícito no JSON normalizado; o Compose omite esse valor em `bind: {}`. Essa interpretação foi corrigida, mantendo os arquivos da primeira tentativa. Os novos mounts somente leitura apontam exclusivamente para fixtures novas e têm `create_host_path: false` na configuração de origem. Não há porta publicada, rede de host, modo privilegiado, volume externo ou credencial herdada. O Docker usa diretório próprio com `auths` vazio e um `.env` vazio.

O contrato JSON de VORP foi conferido contra os campos lidos pelo carregador C#. Além disso, `init_compose_data` criou dois bancos novos dentro de `harness/synthetic_db_check`, e `_load_params` leu o cache real nessa configuração. Resultado: `(0.2, 1.0, 0.1, 0.0, 0.0, 12)`, zero partidas em ambos os bancos, sem fit/backtest ou dados operacionais. Esse subprocesso executou sob lista de ambiente permitida e guard de rede/arquivos. O check não simula permissões do filesystem Linux nem substitui um boot em container. Recibo: `harness/synthetic_db_check/receipt.json`.

Os três scripts passaram na análise sintática; `run_compose.py plan` terminou com código zero e descreveu 21 comandos principais. A revisão final acrescentou exigência explícita de `Server.Os=linux` e encerramento da árvore de processo própria em timeout. Os recibos finais são `runner_validation_final.json` e `runner_plan_final.json`; os anteriores foram preservados. O modo de execução do runner ainda não foi exercitado.

Para ver o plano sem executar Docker, no PowerShell:

```powershell
& 'C:/Users/Superleo13/projetos/brasileirao-predictor/.venv/Scripts/python.exe' -X utf8 'C:/Users/Superleo13/Documents/Codex/2026-09-07/leia-e-execute-c-users-superleo13/work/compose_completion/run_compose.py' plan
```

Somente depois de o diagnóstico do host estar resolvido e o endpoint mostrar Server Linux válido, a execução preparada é:

```powershell
& 'C:/Users/Superleo13/projetos/brasileirao-predictor/.venv/Scripts/python.exe' -X utf8 'C:/Users/Superleo13/Documents/Codex/2026-09-07/leia-e-execute-c-users-superleo13/work/compose_completion/run_compose.py' run --engine 'npipe:////./pipe/dockerDesktopLinuxEngine'
```

O endpoint alternativo explicitamente aceito é `npipe:////./pipe/docker_engine`. O runner não inicia ou eleva o Docker. Cada execução gera projeto aleatório novo derivado de `brasileirao-compose-final-0ff21c335d`, exige `Server.Os=linux`, confere ausência de containers/volumes/redes desse projeto e recusa fontes/fixtures divergentes. Os argumentos exatos ficam em `runner_plan_final.json` e, na execução futura, nos recibos exclusivos de `runs/`. A saída final só pode ser PASS depois de todos os checks e da limpeza conferida.

O roteiro futuro compreende build, up com espera de saúde, Worker→inbox→kernel→resultado, perda/retorno de Redis, restart dos consumidores, health antes/depois de SIGKILL e parada graciosa. A probe one-off do Worker tem o mesmo hostname sintético que o serviço e deve passar antes do kill, evitando falso negativo por identidade diferente. Saúde é consultada repetidamente dentro de prazo; não se considera um heartbeat ainda válido prova de processo vivo após o crash.

Cada comando Docker usa `Popen`. Em timeout, o runner registra o PID criado e, se ele ainda está ativo, chama `taskkill /PID <PID próprio> /T /F`, preservando código e saída dessa tentativa antes de iniciar a limpeza de Compose. Não procura processos por nome nem encerra Desktop/daemon globalmente. O encerramento de clientes não atesta cancelamento de trabalho interno do daemon; timeout nunca resulta em PASS. Essa fronteira também permanece sem exercício real neste host.

O `finally` guarda logs e chama `down --volumes --remove-orphans` somente para o projeto recém-criado, verificando depois sua ausência por label. Não há prune, FLUSHDB/FLUSHALL ou limpeza de recursos globais. Imagens e caches de build podem permanecer; a limpeza declarada cobre containers, volumes e rede do projeto. Se a limpeza falhar, o resultado registra a falha e os recursos devem ser inspecionados pelo nome exato do projeto do recibo.

O endpoint de mercado é inerte. Esse roteiro verifica inicialização, cálculo e recuperação entre os três serviços, mas não emissão com um feed operacional, liquidez, execução financeira ou lucro. O E2E separado de sinais da etapa anterior continua sendo evidência daquela execução. Host, imagens Linux, inicialização em containers e modo `run` continuam pendentes de validação real; a preparação não transforma esse bloqueio em aprovação.
