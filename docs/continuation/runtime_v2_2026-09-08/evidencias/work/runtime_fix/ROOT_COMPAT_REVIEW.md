# Revisão breve de compatibilidade: smoke, schema, CI e processo sintético

08/09/2026, somente leitura das fontes de root. Nenhum cenário adicional executado nesta revisão.

## Achado encaminhado

`hotpath_smoke._READ_RESULT` verifica current, request.payload, completed, fair/result e TTL fair, mas não verifica `lineup_state:{match}` contra o snapshot do request. Assim, uma mudança de lineup sem mudança do head pode produzir PASS no smoke embora kernel/consumidor v2 recusem o estado. Recomendei acrescentar a chave de lineup ao script, conferir snapshot e prazo do request. A correlação do resultado também deve incluir idempotency_key.

Os doubles de `test_hotpath_smoke.py` usam um request incompleto para v2, omitindo inputs, timestamp_t3 e idempotency_key. Eles verificam o comportamento local do helper, mas não atestam um envelope completo. Recomendei completar a fixture e conferir formato/identidade v2. O ponto foi comunicado a root antes de qualquer edição; correção e reteste pertencem a root.

Isso é uma falsa aprovação possível no verificador, não um caminho que force o kernel a aceitar dados não registrados: o kernel e o consumidor mantêm seus próprios fences.

## Compatibilidade confirmada por inspeção

- Schema v2 preserva v1 histórico, acrescenta state_version decimal ASCII, mantém additionalProperties=false e documenta a verificação adicional de Int64 no runtime. Compatível com o parser Python testado.
- `--synthetic-lineup` publica eventos com nomes/IDs sintéticos pelo canal do Worker. Não escreve current/request nem aloca versão; usa o produtor real. `verify_registered_request` só republica os bytes já registrados como wake-up, sem renovar TTL.
- CI Python e .NET usam Redis 8.2.1 em porta 26380, em jobs separados. A mesma porta entre esses jobs não conflita. DB14 Python e DB15 .NET correspondem às verificações opt-in. O run_id é lido do container de serviço do próprio job e disponibilizado por GITHUB_ENV.
- O segundo comando de testes Python seleciona explicitamente `-m integration`; não deixa os testes Redis novos silenciosamente deselecionados. Os testes unitários com exemplos de porta 6379 são doubles/configuração, não novas conexões operacionais.
- Smoke Compose passou a exercitar o Worker v2 por eventos sintéticos em vez de fabricar invocações v1. A mudança de canal/protocolo deixa de quebrar o smoke por construção.
- `synthetic_kernel_process.py` usa o daemon real, alterando somente `_load_params` para parâmetros sintéticos explícitos. Poll, Lua, grade, fair odds e lifecycle permanecem os reais. Endpoint restrito à instância local/DB13 usada pelo teste cruzado.

## Limites da inspeção

Não executei o workflow remoto, builds Compose ou medi seus gates de cobertura nesta revisão. A execução local das integrações e do teste cruzado tem recibos próprios. O teste cruzado .NET usa opt-in de processo Python e fica pulado no job CI .NET comum quando esse opt-in não é definido; o job Compose exerce outro caminho real. Não confundir esses dois escopos.

O teste cruzado encerra o processo Python com kill no cleanup, portanto ele por si só não atesta shutdown gracioso. Os testes de lifecycle e o passo específico de shutdown Compose verificam partes diferentes dessa obrigação.

As fontes finais do kernel, hashes e resultados estão em `work/runtime_fix/kernel_python_receipt.json`; a nota técnica detalhada está em `PYTHON_IMPLEMENTATION.md`. Conferi igualdade SHA-256 entre as seis fontes operacionais e as cópias efetivamente testadas.
