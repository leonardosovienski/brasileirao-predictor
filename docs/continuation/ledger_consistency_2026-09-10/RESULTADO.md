# Consistência do livro-caixa — LGC-20260910

Base main/c2fd45675cf84cf6ba4ed637a111eaf5d6ba74ac. Corrigidos os três grupos LGC do [registro central](REGISTROS.md), com 21 regressões reproduzidas antes e **95 testes aprovados, zero falhas/skips**, na execução final. **O mandato integral permanece aberto; lucro executável não foi demonstrado.**

A gravação cooperante tem exclusão entre processos e threads. O apêndice preserva o histórico e força flush/fsync. O saldo usa uma única leitura reconciliada de apostas; entradas bancárias inválidas são recusadas. Corrigidos mando do placar, dependência indevida de linha legada, contratos importados, teto não finito e rótulo de validação no CLI.

Técnica: pronta somente no escopo testado do livro manual em filesystem local Windows; sistema global não pronto. Ruff, formato e Pyright passaram nos três arquivos Python. Wheel/sdist construídos offline e instalação/CLI verificadas. Os 275 testes Python, 27 Redis e 127 .NET do checkpoint CLO são evidência anterior distinta; .NET/Redis não foram alterados nem repetidos nesta etapa.

Dados: parciais/insuficientes para execução comercial. Nenhum dado de jogo, preço real ou quota foi consumido nesta etapa. H14/H15/H9/A1, helper DC e bases operacionais não foram acessados/modificados. Inventário cumulativo: 456 arquivos; profundidades {'inventory_static_or_targeted_review_only': 287, 'protected_contract_only_no_execution': 59, 'semantic_read_with_recorded_findings': 110}. Inventário continua distinto de revisão semântica integral.

Economia: não mensurável como lucro executável. A decisão BE/CPL permanece congelada. O resultado hipotético de +4,6376u dependia de máximos anônimos e preenchimento de todas as pernas; o modelo de gols perdeu 99,60u. Correção de contabilidade não transforma esses resultados em apostas aceitas ou em lucro futuro.

As primeiras falhas estão preservadas: antes, 21 falhas/2 passagens; primeiro lote após correção, 94 passagens/1 falha por fixture de reordenação sem line/period. A fixture recebeu o contrato ou15/1,5/FT, mantendo a asserção sobre ID e exposição. O primeiro laboratório de processos recusou PID do launcher diferente do interpretador; o segundo usa o executável base, confirmou identidade do filho, exclusão entre processos e liberação automática da trava após seu encerramento. Nenhum processo operacional foi encerrado.

O isolamento final bloqueou três tentativas de subprocesso e uma de socket.bind antes de executarem; nenhuma foi liberada para fazer os testes passarem. O laboratório de processos é separado, restrito a filhos próprios, sem dados ou serviços operacionais. Os ramos POSIX das travas não foram executados neste Windows.

Limites: não há transação entre o livro bancário e o de apostas; leitores usam um snapshot de cada arquivo. Escritores externos que ignoram a trava, hardlinks distintos e filesystems remotos não foram homologados. Falha parcial de disco é recusada pela leitura estrita e exige reconciliação, não recuperação automática. Unidade histórica, câmbio, custos, cronologia dos fluxos no drawdown e autenticidade do relato continuam sem certificação. Importação sem contrato completo falha e não é reescrita.

Nenhuma API, automação, aposta ou experimento de desempenho novo foi executado. A próxima informação econômica decisiva continua sendo preço nominal simultâneo, estado/revisão e condições verificáveis de preenchimento/custos. A captura DC congelada de 11/09/2026 23:00 UTC trata somente sua dupla e não valida a carteira de três pernas. Os 14 itens econômicos e a descoberta que alterou a decisão permanecem em [CLO/RESULTADO](../closeout_2026-09-10/RESULTADO.md), sem revisão dos resultados BE.

Integração/restauração: C:/BRASILEIRAO/AUDITORIA/CONSISTENCIA_LEDGER_2026-09-10.json. [Continuação](PROXIMO_PROMPT.md), [mapa](MAPA_SISTEMA.md) e [reprodução](REPRODUZIR.md).
