# COLLECTION_ONLY — piloto brasileirao-predictor

`collection_run_id`: `collection-brasileirao-20260723-core-9d352654`.

Comando: `python scripts/collect_collection_only.py --dry-run` para validar sem
escrita; remova `--dry-run` para o ciclo arquivístico esportivo. O arquivo
append-only é `data/collection_only/brasileirao_events.jsonl`, ignorado pelo
Git. Ele arquiva somente calendário, participantes, competição, kickoff,
snapshot e resultado oficial da fonte esportiva configurada.

Estados: `DISCOVERED`, `VALIDATED`, `SNAPSHOT_RECORDED`, `EVENT_STARTED`,
`OFFICIAL_RESULT_FOUND`, `COMPLETE` e estados terminais operacionais do core.
`COMPLETE` exige resultado oficial. O contrato proíbe promoção para trial/gate:
não grava em `sombra_*.jsonl`, nem em `matches.db`, H3 ou H5.

O job esperado pelo tooling pode chamar o mesmo comando após a ingestão
esportiva saudável; retries são idempotentes por `canonical_event_id` e a
escrita é append-only via `CollectionArchive` do predictor_core.
