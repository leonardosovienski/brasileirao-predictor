# Reprodução isolada

Ambientes existentes e versões: ver recibos CPL e quality-checks-final.json. Python explícito C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe. Runners em C:/BRASILEIRAO/work/closeout-2026-09-10.

run_isolated.py exige pasta nova e lista explícita de testes; integration-test-scope.json registra34 arquivos. Ele impede rede/subprocessos/SQLite fora do destino sintético, não é licença para executar testes protegidos. integrated-final passou275; a única tentativa bloqueada foi socket.bind, sem conexão. O guard não é herdado automaticamente por processos filhos: CLIs da wheel usam ambiente explicitamente controlado.

O laboratório tools/runtime_lab/run.py exige Redis portátil comSHA, DB13/14/15 e run_id próprios. Seus recibos registram comandos, logs, encerramento e TRX.127.NET/27 Python Redis finais. Não reutilizar saída ou endpoint com dados. Não rodar Compose/cron/status/coletores contra destinos operacionais para reproduzir esta entrega.

check_changed.py roda Ruff e Pyright apenas no diff Python. build_package.py gera wheel/sdist offline, instala em destino explícito com --python RI e valida sete comandos de CLI com entradas sintéticas. backup_delivery.py confere bytes, ZIP CRC e restaura bundle em Git bare novo. Use pastas novas ao repetir; os scripts recusam sobrepor evidências.
