Adendo de 8 de setembro de 2026, 04:39 UTC, à revisão de ambiente. Os recibos e hashes anteriores foram preservados.

Os mesmos quatro cenários ACL foram repetidos no Redis real DB12 após a alteração do watchdog. Fonte C# final: SHA-256 `ce1ff57f0411305a983d89dc80e2b867a2c7f952d48ea5adb0278d78ab1679ea`. Script Lua extraído, incluindo `Checks`: SHA-256 `f4c61eb6f85fe5da26192252b518c722282a55b46c09527589b6a992898b507d`.

Todos passaram. Negar XADD, SET ou ZREM preservou ready e não gravou outbox ou marcador; o replay autorizado criou exatamente um lote. Negar PUBLISH reteve o lote e o marcador; o replay retornou zero sem duplicar. Payload e quatro campos de identidade foram preservados. DB12 terminou vazio como começou, sem FLUSHDB/FLUSHALL, removendo somente chaves e usuários ACL UUID criados pelo próprio auditor. Run_id e PID foram conferidos: `273e80f8cca2bcfdf62f19e6244aabc4dc5ecd06`, PID `10`.

A comparação textual mostrou que o corpo de `PublishSignals` e os helpers de tipo/ACL continuam iguais à versão auditada às 04:21 UTC. `Checks` acrescentou `watchdogDeadline`, o que alterou o hash do script completo e justificou a repetição sobre a fonte final. Esta rodada não executou novos cenários para Register/ApplyWatchdog/Synchronize e não apresenta aqueles limites como cobertos por esta auditoria de outbox.

Recibos: `outbox_acl_20260908T043905/audit.json`, `source_comparison.json` e `KernelRedisProtocolV2.cs.snapshot`. O resultado anterior em `outbox_acl_20260908T042148/` continua disponível. Compose build/up permanece não executado. O Redis ainda está ativo para os testes finais da equipe; limpeza não foi iniciada.
