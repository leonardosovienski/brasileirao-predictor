# Validação final da entrega OU2.5 v2

Estado congelado em 27/08/2026: `NO_BET`, capital desabilitado, força máxima
40/100 e nenhum candidato retrospectivo elegível.

## Verificações executadas

- Ruff: aprovado.
- Pyright: zero erros e zero avisos.
- Pytest: 809 aprovados, 1 teste de integração Redis desmarcado pela configuração
  padrão e 3 avisos numéricos conhecidos de testes sintéticos.
- CI local: todas as cinco barreiras aprovadas, incluindo contenção de
  `current_elo`, banco de pesquisa somente leitura e smokes de previsão.
- .NET: restore reproduzível com lock aprovado; 18 testes independentes de
  infraestrutura aprovados.
- .NET/Redis: `WorkerRuntimeTests` requer Redis local em `127.0.0.1:6380`; não
  foi contado como aprovação nem como defeito OU2.5. A execução falhou fechada
  por ausência do serviço externo.
- JSON: 33 arquivos lidos em modo estrito, sem `NaN` ou `Infinity`.
- Manifestos: 32 hashes internos conferidos byte a byte.
- Grade fatorial: 77.760 avaliações registradas.
- Resultado anual: política governada com 0 apostas/0 unidades; contrafactual
  apostar sempre com −15,041 unidades em 1.682 apostas.
- Gate de qualidade: 16 pares-placeholder `51,0 / 1,002` de 2026 rejeitados.
- Busca de segredos aplicada ao conteúdo novo; nenhum segredo real versionado.

## Limite da garantia

Esta validação sustenta que os artefatos commitados são internamente
consistentes e que as verificações disponíveis passaram nas condições acima.
Ela não transforma odds retrospectivas em preços executáveis nem garante lucro
futuro. Somente evidência prospectiva A1 pode alterar o estado `NO_BET`.
