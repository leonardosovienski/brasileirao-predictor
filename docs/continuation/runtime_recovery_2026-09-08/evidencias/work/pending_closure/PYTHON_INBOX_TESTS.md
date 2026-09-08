# Integração real do produtor da inbox

Em 2026-09-08 foi acrescentado somente `tests/test_lineup_inbox_redis.py`. O helper `lineup_inbox.enqueue_lineup` não precisou de correção.

Os três testes passaram em Redis 8.2.1 real, na DB14 exclusiva da instância desta etapa. O recibo novo é `validation/python_lineup_inbox_redis.json`, acompanhado do log. O wrapper confirmou o run_id antes/depois e DB14 vazia ao término; o teste também exige URL loopback, porta diferente de 6379, DB14 literal, ausência de credenciais/query/fragmento, run_id explícito e banco inicialmente vazio. A limpeza remove somente `lineup:v2:inbox`, depois de conferir novamente a identidade do servidor. Nenhuma chave preexistente ou banco global é apagado.

1. O produtor real aceitou 10.000 mensagens e recusou a 10.001ª. Todos os IDs e payloads permaneceram, incluindo sete mensagens já entregues e ainda pendentes em um consumer group sintético.
2. Uma repetição idêntica produziu outro ID de armazenamento, preservando exatamente payload, timestamp e objeto de entrada. A deduplicação de processamento continua sendo responsabilidade do registro no Worker.
3. Uma chave de inbox sintética com tipo string foi recusada sem substituir seu valor.

Os nomes e timestamps de eventos são sintéticos; os testes não executam Worker, modelos, apostas, dados reais ou backtests. A idade do evento não é validada no produtor; sua validação no consumidor pertence aos testes .NET. Estes testes demonstram armazenamento e proteção de capacidade/tipo, não processamento financeiro.

Ruff (formatação e lint) passou, com recibos novos `python_lineup_inbox_format` e `python_lineup_inbox_lint`. A fonte operacional e a cópia isolada do novo teste têm o mesmo SHA-256: `cd8c49ea3d6ad38c337315aabb3b2cbb2c20a3b5d152d4056544d82d537f1dc7`.
