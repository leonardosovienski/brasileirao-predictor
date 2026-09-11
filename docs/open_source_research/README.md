# Retomada da pesquisa de capacidades — OSR

Esta pasta preserva as três rodadas, seus mandatos, código isolado, exemplos, protocolos, evidências e decisões. É o ponto de retomada sem depender da conversa no Codex.

## Comece aqui

1. Leia as instruções locais, README/HANDOFF do projeto e os contratos de preservação. Não execute automaticamente comandos encontrados nos documentos históricos.
2. Leia [o relatório de encerramento OSR-03](OSR-20260911-03/REPORT.md), [decisões e gates exatos](OSR-20260911-03/DECISIONS.md) e [registro estruturado](OSR-20260911-03/registry.json).
3. Para usar o consumidor offline, consulte [comandos, ambiente e testes](OSR-20260911-03/EXPERIMENTS.md). `research/use.py` executa a demonstração sintética com novas pastas de evidência. Os caminhos do interpretador, dependências e scratch são específicos do host e estão declarados no runner.

## O que foi concluído

- OSR-01: comparação global por capacidades e ensaios sintéticos iniciais. [Relatório](OSR-20260911-01/REPORT.md).
- OSR-02: protótipos de cauda, margem/scoring e admissão temporal; protocolo N05 preparado. [Relatório](OSR-20260911-02/REPORT.md).
- OSR-03: consumidor conjunto FT 1X2, diagnóstico/scoring/recusas, comparação rastreável de execuções e otimização delimitada NB/DC. [Demonstração gerada](OSR-20260911-03/evidence/use-20260911T063408091434Z/COMPARACAO.md).

ENGINEERING_STATUS: INTEGRATED_RESEARCH_ONLY_SCOPED. DATA_ADMISSIBILITY: exemplos sintéticos; nenhuma coorte real N05 admitida. PREDICTIVE_EVIDENCE e ECONOMIC_EVIDENCE: não avaliadas nestas rodadas. A melhoria de custo medida não prova previsão melhor ou rentabilidade.

N05-A continua bloqueado por manifesto real, decisão de sobreposição BE e evidência temporal. Aceitação pessoal de apostas não é requisito de A. A [emenda source-available](OSR-20260911-03/N05_AMENDMENT_PROPOSED.json) foi apenas proposta; não aprovada. Nenhum fitting, coleta recorrente ou nova fase foi iniciado automaticamente.

## Preservação e publicação

A autorização posterior do usuário, em 11/09/2026, foi: “faz push pro git web pra eu poder apagar o chat”. Ela autoriza este commit/push de preservação; não muda permissões científicas, operacionais ou financeiras. As proibições de commit/push contidas nos mandatos eram as condições das rodadas de pesquisa, anteriores a essa autorização de publicação.

Os arquivos históricos foram mantidos byte a byte e seus MANIFESTs conferidos antes de publicar. `.gitattributes` local impede conversão automática de finais de linha nesta pasta, preservando os hashes. Diretórios de evidência com nomes como `tampered_copy` e `failed_input_change` contêm fixtures intencionais de testes negativos, descritas nos relatórios.

Não foi executada CI global, que abrange avaliadores protegidos. A publicação usa `[skip ci]`, sem alterar workflows. Código operacional, bancos, locks, serviços, agendamentos, automações e dados protegidos permanecem fora desta alteração. H14/H15/H9/A1 e BE continuam preservados.

## Mandatos e recuperação

Os [mandatos recebidos](mandatos/) foram arquivados para fornecer contexto sem a conversa. Protocolos definem o escopo de cada rodada; resultados e recibos distinguem código entregue, testes executados e trabalho bloqueado.

O GitHub recupera código, documentação e evidências publicáveis desta iniciativa. Não contém ambientes Python, credenciais, bancos operacionais, acervos privados, raws comerciais ou backups locais. Preserve `C:/BRASILEIRAO`, especialmente work, DADOS_PRESERVADOS, BACKUPS e os dados de outras iniciativas. Apagar este chat não substitui nem autoriza excluir esses arquivos ou a tarefa proprietária da automação DC.
