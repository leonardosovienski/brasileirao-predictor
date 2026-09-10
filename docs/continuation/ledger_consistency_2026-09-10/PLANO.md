# LGC-20260910: consistência do registro manual

Base: main/c2fd45675cf84cf6ba4ed637a111eaf5d6ba74ac, limpa após restauração CLO verificada.
Esta etapa implementa o item de integridade remanescente do ledger, identificado em CLO.
Não é novo estudo de desempenho. Hipóteses BE, orçamento público CPL e captura DC permanecem congelados.

Problemas a reproduzir antes de corrigir: duas liquidações concorrentes do mesmo ID; leitura dupla no mesmo saldo; JSON/valores bancários inválidos aceitos; concatenação após última linha sem terminador; contrato de liquidação inválido; placar invertido registrado sob mando errado; teto NaN; exposição a rótulo falso de validação no CLI.

Decisão: serializar escritores cooperantes com trava de arquivo do sistema operacional, sem espera nem renovação de claims. Trava dedicada ao livro manual, em arquivo lateral persistente, sem tocar H14/H15/H9/A1. Arquivos operacionais não serão abertos. Fsync em apêndices; usar um snapshot do livro para o saldo. Importações inválidas recusadas, bytes históricos preservados. Conflito de escritores falha explicitamente e pode ser repetido pelo operador após término da outra escrita.

Prova esperada: regressões sintéticas antes/depois, concorrência determinística com duas threads e laboratório separado com processos filhos restritos, verificação dos demais testes de ledger, formato/lint/tipagem e pacote instalado. Cópias, logs, ambientes e relatórios em C:/BRASILEIRAO. Não executar suite de coortes, acesso de rede, Redis, banco operacional ou submissão financeira. A correção não verifica autenticidade do relato, custos pessoais nem disponibilidade comercial. Parar esta etapa após corrigir e validar os casos delimitados; cobertura geral continua registrada separadamente.
