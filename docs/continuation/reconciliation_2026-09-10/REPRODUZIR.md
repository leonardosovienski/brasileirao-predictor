# Reproduzir a verificação RCA

Ambiente: C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe; Python 3.13.12. Trabalho: C:/BRASILEIRAO/work/reconciliation-2026-09-10. Helpers, seus inputs e logs são preservados no pacote de entrega. Não executar scripts de pesquisa histórica ou coortes para repetir estes testes.

O runner recebe um nome de saída novo, exclusivo dentro do work, seguido de test_reconciliation_gate_contracts.py e test_residual_gate.py. Exemplo em PowerShell:

```powershell
& C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe -X utf8 -I -B C:/BRASILEIRAO/work/reconciliation-2026-09-10/run_isolated.py reproducao-nova test_reconciliation_gate_contracts.py test_residual_gate.py
```

O teste test_existing_a10_report_is_formally_no_go não foi executado; não usar o allowlist histórico do helper como autorização para reavaliar relatório congelado. O runner bloqueia rede, subprocessos e dados operacionais; todas as fixtures ficam na saída exclusiva. Na execução final houve uma tentativa socket.bind bloqueada antes da operação; sua origem não foi rastreada, e ela não abriu um serviço de rede.

Após a troca dos guias, README mudou como metadado do pacote. Por isso houve um segundo build/instalação/smoke em package-after-guides, também aprovado, com recibo próprio. Os logs e artefatos da primeira execução permanecem preservados; não se trata de 14 verificações únicas. As checagens de metadados de dependências não são auditoria completa de vulnerabilidades.

before/junit.xml preserva 42 falhas/4 passagens; after e final têm 49 passagens cada. O source Git da base mais o novo arquivo de regressões permite examinar a reprodução anterior; não resetar a main para isso. check_changed.py executou Ruff e Pyright explícitos fora da exclusão global de research. build_package.py construiu offline e instalou somente o wheel no target, usando dependências já presentes no venv RI; não afirma ambiente reinstalado do zero. Saídas desses helpers são exclusivas ou nomeadas: não sobrescrever as evidências finais ao repetir.

verify_current_evidence.py conferiu inventário, hashes da entrega anterior, requisitos/extras e metadados DC; não importa a aplicação nem lê placares. recover_chat.py extraiu somente mensagens visíveis da tarefa exata; o primeiro print encontrou limitação de encoding do console, mas os arquivos foram salvos e relidos com -X utf8. A fotografia do chat cresce depois da leitura, então seu hash não deve ser comparado como se o log ativo fosse imutável.

Integração: prepare_integration.py usa caminhos exatos, verifica bytes indexados e não altera ignores globais. backup_delivery.py cria bundle, restaura em bare isolado, compara HEAD/árvore/evidências e bytes do wheel/ZIP. Esse procedimento verifica recuperação de código e evidências, não bancos/serviços operacionais.
