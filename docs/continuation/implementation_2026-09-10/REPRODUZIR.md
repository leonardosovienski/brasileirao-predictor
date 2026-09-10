# Reprodução IE-20260910

Executar somente em C:/BRASILEIRAO. O ambiente completo RI e SDK portátil existentes foram reutilizados; o venv mínimo PF e os helpers da captura permaneceram preservados. Python 3.13.12, .NET SDK 10.0.401 e versões do uv.lock. O laboratório é descartável e contém somente parâmetros fabricados; seus resultados não autorizam operação financeira.

## Integração Windows

O ZIP redis-windows8.2.9 está em work/implementacao-2026-09-10/software, SHA256 dcff676e861a4ae0a9854556239398e77a7469c9379af64a4a76798d166d1aa0, 12.336.427bytes. O executável tem SHA256 f9bf66f93438ec461b6e32453e6c9a8dde2f8c93c1018d1b75aa38b113ba3f14. Sua release/digests estão em evidence. Não instalar ou executar start.bat/serviço. A porta 26380 deve estar livre; o runner recusa ocupação antes de conectar e não encerra servidores externos.

PowerShell, a partir de C:/BRASILEIRAO/brasileirao-predictor, escolhendo saída NOVA:

```powershell
& C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe -I tools/runtime_lab/run.py `
  --output C:/BRASILEIRAO/work/implementacao-2026-09-10/runtime-NOVO `
  --repo C:/BRASILEIRAO/brasileirao-predictor `
  --server C:/BRASILEIRAO/work/implementacao-2026-09-10/software/redis-8.2.9/Redis-8.2.9-Windows-x64-msys2/redis-server.exe `
  --server-sha256 f9bf66f93438ec461b6e32453e6c9a8dde2f8c93c1018d1b75aa38b113ba3f14 `
  --dotnet C:/BRASILEIRAO/work/revisao-integral-2026-09-09/dotnet-sdk/dotnet.exe `
  --nuget-cache C:/BRASILEIRAO/work/revisao-integral-2026-09-09/nuget-packages
```

O runner salva comandos, códigos de saída, PID/run_id, logs e TRX em receipt.json/arquivos locais. Reutiliza o cache NuGet RI; perfis e novos temporários ficam na nova saída. Nunca apontar ao Redis operacional. `--cross-only` delimita uma investigação de processo; não equivale ao lote completo. `--diagnostics` registra somente tipo/local de exceção do smoke sintético. O runner nativo exige Windows; a configuração CI usa Redis Linux e o mesmo bootstrap sintético, mas esta CI remota ainda não foi executada.

## Consumidor de capturas

CLI empacotada: `python -m brasileirao_predictor.research.price_strength.capture_decision --contract CONTRATO --receipt RECIBO --capture RAW1 --capture RAW2 --capture RAW3 --output-dir SAIDA_NOVA`. Todo arquivo salvo do fixture deve constar da lista; tentativas fracassadas sem corpo permanecem no universo via recibo. O contrato exige fixture, cinco identificadores positivos, kickoff, cutoff, banca de cenário e política de custos explícita. Exemplo efetivamente usado: evidence/capture-contract.json. `run_capture_experiment.py` na pasta work é a reprodução delimitada DC; preserva o hash do contrato e recebe um sufixo numérico novo de saída.

O comando não realiza GET, login, leitura automática de data/DB, inferência de caminhos de payload ou liquidação. O resultado sempre distingue comparação API condicional de execução. Manifestos fixam hashes dos bytes usados e do pacote de pesquisa, publicação sem sobrescrever outra saída. Não usar o cutoff do diagnóstico como substituto da captura futura congelada.

## Checks e escopo

`run_isolated.py` copiado da RI na pasta work recebe uma saída nova e uma lista explícita de testes. Lote final e pulos em evidence/summary.json. As tentativas anteriores e correções intermediárias permanecem em work; não remover falhas para apresentar aprovação limpa.

Ruff: `ruff check brasileirao_predictor brasileirao_scripts tests tools/runtime_lab` e `ruff format --check` no mesmo escopo. Pyright padrão mais configuração explícita em work/implementacao-2026-09-10/pyrightconfig.json; executar o Node local e o index.js da versão1.1.411, sem instalar latest. Build Python e smoke do wheel usam saídas novas dentro da rodada, sem DB/rede após construção. Backups finais: bundle Git verificado, clone bare/fsck e ZIP de evidências, descritos no recibo de auditoria. Não são restauração operacional de dados protegidos.
