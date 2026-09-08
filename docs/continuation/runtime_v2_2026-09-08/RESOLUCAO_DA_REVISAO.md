# Resolução dos achados intermediários

Os achados de ROOT_COMPAT_REVIEW.md foram corrigidos depois daquela leitura:
o smoke compara o snapshot de lineup, o prazo do request e idempotency_key;
as fixtures têm envelope v2 completo e usam o parser efetivo do kernel.
Os 12 testes finais e o teste real entre processos passaram após as correções.

Recibos intermediários preservam falhas reais de compilação, setup, tipagem,
formatação e probes incompatíveis com a revisão em teste. A rodada Redis que
deselecionou testes e a checagem Pyright sem arquivos não contam como aprovação.
Somente os recibos explicitamente listados em estado.json fundamentam os
números finais. Probes Lua definitivos: lua_boundary_audit_20260908T033058.

A revisão foi interna. Não houve execução Compose nem CI remoto nesta etapa.
Os arquivos de reprodução registram caminhos desta máquina; outra máquina
precisa adaptar caminhos e provisionar sua própria instância descartável.
Não apontar os testes para Redis operacional. Arquivos fonte oficiais grandes
do provisionamento ficaram no scratch; os URLs, hashes e comandos foram
preservados no conjunto de evidências e na cópia persistente.
