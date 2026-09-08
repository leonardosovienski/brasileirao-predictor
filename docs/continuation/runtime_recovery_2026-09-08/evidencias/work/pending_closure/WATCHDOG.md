# Watchdog persistente após confirmação da primeira escalação

Falha demonstrada: depois de registrar a primeira escalação e executar XACKDEL da entrada, o único acompanhamento do timeout permanecia em `_pending`, na RAM. Uma instância nova do Worker não conhecia a partida e não aplicava fallback quando a segunda escalação faltava.

O novo estado tem `WatchdogDeadlineUnixMs` opcional, um inteiro Unix em milissegundos. O Worker deriva o prazo da captura conhecida na primeira aceitação; correções posteriores preservam esse valor. O próprio Register Lua valida que um prazo já presente não muda e atualiza `lineup:v2:watchdogs` no mesmo CAS que grava lineup/current/request. O índice é um ZSET por match_id, com score igual ao prazo. Estado completo remove a partida do índice. Tipo/ACL do índice são verificados antes de qualquer mutação do registro.

Não há mais `_pending` em RAM como autoridade. O watchdog consulta o índice ao iniciar e periodicamente, usando Redis TIME e ZSCAN com cursor. Continua páginas com pausas curtas; após terminar uma varredura espera o intervalo configurado. A publicação do fallback e a remoção do índice compartilham o CAS de estado/current; o script repete a verificação do prazo contra Redis TIME. Um snapshot velho não pode substituir o estado novo nem apagar seu índice.

Replay idêntico também sincroniza o índice a partir do snapshot corrente antes de o handler retornar, portanto antes do ACK. O reparo compara os bytes de lineup/current; se outra escalação venceu a corrida, relê o estado. Duplicata do Register recupera o prazo do snapshot canônico, nunca do payload de uma nova tentativa. A remoção de partidas completas, já encerradas por fallback ou sem estado também compara os snapshots, evitando limpeza atrasada de uma entrada nova.

As respostas e invocações v2 não mudaram. Python continua comparando o JSON bruto de lineup_state; nenhuma fórmula, seleção, odd ou regra financeira foi modificada. Os scripts da outbox e seus fences permanecem iguais.

## Verificação

- Snapshot novo: `work/pending_closure/watchdog_before/MANIFEST.json`, cinco fontes anteriores preservadas.
- `dotnet_watchdog_ack_baseline.json`: teste real com Redis confirmou a falha anterior. Primeira escalação registrada e ACK concluído; instância nova não produziu fallback em três segundos após o prazo.
- `dotnet_watchdog_first.json`: seis regressões dirigidas passaram, incluindo recuperação após ACK/reinício, preservação do prazo nas correções, reparo de índice no replay antes do ACK, recusa atômica de índice de tipo inválido, snapshot velho sem apagar acompanhamento novo e retry após resposta incerta.
- `dotnet_watchdog_full.json`: suíte completa Release com XPlat Code Coverage, 109 aprovados, um skip reservado ao E2E entre processos, zero falhas.
- Cobertura: 839/969 linhas = 86,58%; 350/426 desvios = 82,15%. Ambos gates de 80% preservados e satisfeitos. XML: `work/integration-repo/artifacts/dotnet-watchdog-full/1e6d51e5-8560-4daf-b9ac-8a5ce915d339/coverage.cobertura.xml`.
- `dotnet_watchdog_warnaserror.json`: build Release `--no-restore --no-incremental --warnaserror`, zero avisos e erros.
- Recibos em `work/pending_closure/validation`; Redis isolado DB15, run_id `273e80f8cca2bcfdf62f19e6244aabc4dc5ecd06` conferido antes/depois, DB vazio após os testes.

## Limites explícitos

O acompanhamento depende da retenção do estado no Redis, configurada pelo TTL de lineup; não recupera um snapshot cujo TTL já terminou. Índices órfãos vencidos são removidos por CAS. A garantia começa nos aceites desta implementação: snapshots legados sem o novo prazo não recebem história inventada nem são descobertos por uma varredura de dados operacionais. Se uma nova atualização válida de um snapshot legado for aceita, o prazo inicial usa a captura já conhecida desse snapshot; não se afirma reconstruir a primeira captura histórica perdida.

O prazo compara timestamps declarados com Redis TIME. Persistência depois de falha do servidor Redis depende de sua configuração. Esta mudança resolve perda por reinício do processo Worker dentro dessa retenção; não promete retenção infinita, autenticação do relógio do provedor ou entrega financeira.
