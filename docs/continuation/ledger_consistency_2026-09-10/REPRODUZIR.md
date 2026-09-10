# Reprodução LGC

Ambiente RI: C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe, Python 3.13.12. Ferramentas, dependências e saídas em C:/BRASILEIRAO; Windows/PowerShell/Git e aplicativo continuam dependências externas inevitáveis.

Helpers e argumentos completos em C:/BRASILEIRAO/work/ledger-consistency-2026-09-10. run_isolated.py recebe um nome novo de saída e a lista explícita de seis arquivos em evidence/final/isolation.json. Nunca apontar testes para ledger operacional. process_lock_lab.py executa somente a trava, em filhos próprios com identidade conferida, e exige nova pasta de saída. A primeira versão falhou e está preservada em process_lock_lab-first.py.

check_changed.py verificou os três arquivos de código/teste; usa diff não staged, portanto não deve ser repetido cegamente após commit. build_package.py construiu offline e instalou em target próprio; logs e hashes estão em evidence/package-receipt-final.json. Relatórios finais foram escritos depois do build e são entregues separadamente. Backup verifica também igualdade de bytes do módulo no wheel e evidências do Git restaurado.

Não somar execuções sobrepostas como testes independentes: antes=23, primeiro depois=95, final=95. O laboratório de processos complementa, sem aumentar artificialmente esse contador.
