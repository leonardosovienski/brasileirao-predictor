# Notas de verificação e falhas preservadas

O registro validation-summary.json distingue testes únicos de repetições.196 casos Python únicos aprovados no conjunto integrado/storage;27 Redis;119.NET entre execuções. A execução.NET runtime-after-02 teve uma falha de bootstrap, seguida de passagem do caso em runtime-cross-diagnostic, com import9s/JIT8s. A causa da primeira ocorrência permanece aberta.

O primeiro lote integrated-python usou dois nomes incorretos de arquivos e não executou testes. integrated-python-02 expôs dois subprocessos bloqueados pelo runner e um teste que esperava texto bruto da API. A CLI de prontidão foi testada em processo no teste unitário e novamente em subprocesso no pacote isolado. O erro da API foi sanitizado e a expectativa atualizada, sem reduzir a condição de falha. integrated-python-03 passou192.

Ruff corrigiu imports/formato; Pyright identificou duas anotações numéricas que foram corrigidas sem alterar resultados. As primeiras falhas e logs continuam na pasta de trabalho; o resumo final exige zero erro dos checks finais.

Na primeira instalação da wheel, uv autodetectou um Python de C:/Cripto, embora o destino de instalação e caches estivessem em C:/BRASILEIRAO. A descoberta foi registrada; a instalação final fixa --python no ambiente RI e limita PATH. Os testes de CLI em ambas as etapas usaram o Python RI explicitamente. Nenhum arquivo ou processo do outro projeto foi alterado por uma ação direcionada desta tarefa. A descoberta automática inicial não é apresentada como isolamento perfeito.

O sdist/wheel foram construídos antes desta nota de auditoria final; contêm o código testado e README vigente. Nota, manifestos e recibos de integração são entregues separadamente e não são falsamente atribuídos ao conteúdo do pacote.
