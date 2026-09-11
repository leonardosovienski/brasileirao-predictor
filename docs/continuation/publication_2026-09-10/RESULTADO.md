# Resultado — PUB-20260910

Releitura integral do histórico visível recuperado e dos dois mandatos concluída. Mantidas as correções RES após confronto com código, testes, registros e limites. Acrescentados runner portátil, configuração Compose isolada, controles de I/O, verificação de tipagem, arquivo do contexto e índices de recuperação. O GitHub e o checkout final devem ser conferidos pelo recibo de publicação; este documento não substitui o recibo do push/pull.

- Python 3.13 e 3.14: **345 testes aprovados por versão**, sem falhas, erros ou skips. São os 336 casos RES mais nove provas do isolamento; não são 690 casos distintos.
- .NET 10: **160 testes aprovados**, zero skips; **86,91% de linhas e 81,90% de ramos**, mantendo os pisos de 80%.
- Compose Linux: build, inicialização, health, hotpath sintético, interrupção/retorno do Redis, novo hotpath e desligamento normal aprovados. Volumes próprios removidos ao final; nenhum serviço operacional utilizado.
- Dependências instaladas a partir dos lockfiles no runner; wheel/sdist gerados. Ruff, formatação e Pyright aprovados para as ferramentas novas.
- [Execução final no GitHub](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34552247397), commit `cc38b57bd3ba6f8c2cbdce6353eaf085d4ece14f`. Logs, XML, hashes e resumos preservados em evidence. A execução anterior 34544695904 também foi mantida; houve correção posterior de duas anotações de retorno do guard.

**A CI global não foi executada.** `ci.yml` inclui avaliadores H14/H15/A1 e registries reais; rodá-lo indiscriminadamente contrariaria o mandato. Seus critérios não foram reduzidos. A publicação em main usa `[skip ci]`, e o workflow delimitado tem nome e escopo próprios. Verde nesse workflow não significa autorização financeira, homologação comercial ou sistema integralmente pronto.

O registro corrente conserva **52 itens validados e sete bloqueados**. A falta do ensaio Linux foi resolvida; o restante de RCA-P09 diz respeito ao escopo global. Permanecem requisitos de operação protegida, fonte/entrada comercial autenticada, estado verificável da automação, ofertas/aceite/capacidade/custos e restauração operacional. Lucro líquido futuro executável continua não demonstrado; capital desabilitado.

O arquivo do contexto contém as 134 mensagens visíveis até o checkpoint, os mandatos integrais e 155 roteiros/documentos locais de trabalho. Esta etapa adicional está registrada aqui e em PROXIMO_PROMPT.md. Não foram arquivados raciocínio interno, mensagens de sistema ou credenciais. Roteiros históricos são evidência e não autorização para reexecutar comandos sobre caminhos existentes.

[Reavaliação das decisões](REVISAO_DO_CHAT.md), [registro completo](REGISTROS.json), [dados/fontes](DADOS_E_FONTES.md), [reprodução](REPRODUZIR.md), [retomada](PROXIMO_PROMPT.md). Os seis guias principais apontam para este estado; os documentos antigos continuam datados e preservados.

O clone Git recupera conteúdo versionado. Dados privados e raws sem redistribuição estabelecida continuam sob C:/BRASILEIRAO, com seus inventários e backups. Preservar a pasta é necessário; GitHub público não equivale a backup integral de toda a máquina. A conversa não precisa ser a fonte de continuidade depois que o recibo de recuperação estiver aprovado.

[Publicação, pacote e recuperação conferidos](PUBLICADO.md).
