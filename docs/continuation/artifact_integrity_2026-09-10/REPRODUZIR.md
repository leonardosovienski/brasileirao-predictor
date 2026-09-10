# Reprodução ARI

Ambiente RI Python 3.13.12 em C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe. Helpers em C:/BRASILEIRAO/work/artifact-integrity-2026-09-10. Windows, Git, PowerShell e aplicativo são dependências externas inevitáveis.

run_isolated.py exige um diretório novo e lista explícita: test_residual_artifact_integrity.py, test_market_residual.py e test_closeout_research_inputs.py (52 casos); test_residual_walkforward.py foi executado separadamente (2 casos). Não executar sobre dados reais nem repetir o gate A10 ou coortes para esta reprodução. Isolamento final recusou socket.bind antes de acesso; nenhuma liberação de rede foi necessária.

before contém 24 falhas; after contém 50 passagens; final contém 52 passagens, incluindo duas verificações adicionais de gradiente; consumer contém 2 passagens. Contagem final única=54, não soma de todos os lotes. quality-first preserva os checks iniciais; quality-checks-final tem os comandos aprovados. check_changed.py usa diff não staged, portanto adaptar a lista se o código já estiver commitado.

build_package.py cria wheel/sdist offline e instala em target próprio; hashes/logs em evidence/package-receipt-final.json. Docs finais foram escritos depois do pacote e são entregues separadamente. Backup verifica bytes do módulo no wheel, ZIP e evidências no Git restaurado. Sem restore de DB/Redis/coortes operacionais.
