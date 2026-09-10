# Resultado das correções — RES-20260910

Foram implementadas correções nos componentes que sustentavam as 14 pendências, com regressões antes/depois, além de dez falhas adicionais encontradas na leitura. O mandato global ainda não está integralmente concluído: restam sete requisitos protegidos/externos no registro de 59 itens (52 validados). A leitura semântica dos 399 arquivos permitidos do inventário base está concluída; outros 59 permanecem restritos a contratos/metadados. Não se declara zero pendências.

O registro único é [REGISTROS.json](REGISTROS.json), com versão legível em [REGISTROS.md](REGISTROS.md). Os contratos e compatibilidade estão em [CONTRATOS.md](CONTRATOS.md). Fontes, falhas e testes estão em evidence/. A base desta etapa é main/3bda4c4b0abd9b94902f77509d7d211ac30e96f7; o SHA integrado e a restauração ficam no recibo C:/BRASILEIRAO/AUDITORIA/RESOLUCAO_2026-09-10.json.

## O que mudou

Carteira e replay passaram a reconciliar caixa, principal, custos, reservas e resultados pendentes. A materialização exige casa ofertante fixa excluída da referência, relógios válidos e contexto disponível. Curated v2 e envelopes de escalação preservam revisões/remoções e não recuperam estados antigos depois de suspensão. O gate estatístico bloqueia aprovação sem desenho e histórico de tentativas.

O Worker exige entradas de modelo com identidade, versão, Elo, posição e cobertura VORP; fallback demonstrativo passou a ser explícito. Feed vazio está desativado, mensagens comerciais precisam cumprir o contrato normalizado e o cache invalida preço suspenso, conflitante, antigo ou desconectado. A telemetria mantém ordem por T3 sem renovação indevida de TTL. O kernel tem health leve, validação numérica antes do JIT e concorrência limitada.

Importação histórica publica somente um novo DB íntegro; recuperação confere também o destino e rejeita links/junctions. Estatísticas de jogadores não inventam disponibilidade pré-jogo. Promoções exigem schema completo. Cobertura não aprova denominador vazio/arquivos ausentes. Odds exibidas são diagnóstico; comandos de aposta e alegações de janela validada foram retirados. Liquidação diagnóstica valida o jogo e o vetor de probabilidades, coordena escritores e conserva o primeiro recibo em retries.

## Validação e limites

336 casos Python distintos passaram nas suítes explícitas, sem contar repetições; detalhes em evidence/python-validation.json. Ruff, formato e Pyright passaram nos 41 arquivos Python alterados, incluindo pesquisa, testes e ferramentas que a configuração global normalmente exclui. A suíte .NET completa passou 160/160, sem skips, com restore locked/build warnaserror. Cobertura .NET: 86,91% de linhas e 81,90% de branches. O Redis portátil descartável foi encerrado. Não é homologação de produção.

Compose config passou para init-data/kernel/redis/worker com feed e modo sintético desabilitados por padrão. Não há engine Linux/WSL instalado neste host; containers e CI global da versão não foram executados. A aprovação de tipagem/testes delimitados não afirma a cobertura global Python. Sdist offline e wheel derivada passaram; 231 módulos conferidos byte a byte. Wheel instalada em venv separado sem PYTHONPATH, reutilizando explicitamente dependências RI. CLI help/health e novo ensaio entre processos passaram; Redis encerrado. O primeiro roteiro esperou indevidamente saída 1 sem configuração: o contrato retorna 2. Falha preservada e verificação correta separada em package-final-cli; não foi alterado o produto para satisfazer o roteiro.

Erros intermediários foram preservados: timeout antigo de causa desconhecida, cotação de fixture envelhecida durante inicialização, fsync em descritor somente leitura no Windows e diagnósticos de tipagem. O baseline odds-display-before importou o módulo legado que chama load_config; nenhum valor foi impresso, mas não se afirma ausência absoluta de acesso à configuração nessa reprodução. A correção removeu o efeito no import e o guard passou a bloquear config.yaml.

## Decisão econômica

A pergunta principal continua: existe oferta nominal observada simultaneamente com referência independente que sobreviva a custos e preenchimentos verificáveis? Ela tem prioridade porque um modelo bem calibrado não cria uma oferta executável. Não houve novo teste de desempenho nem seleção de variante nesta etapa; os estudos BE e negativos anteriores estão preservados.

Foi feita uma tentativa pública delimitada de catálogo de mercados, com 1 GET, sem credenciais, retries, ordens ou resultados: falhou com ConnectionError antes de obter resposta útil. Isso demonstra a falha dessa tentativa, não a inexistência de oportunidade. Cotações/capacidade/aceitação/custos pessoais continuam sem evidência suficiente; zero não substitui desconhecido.

A descoberta decisiva é a distância entre cálculo condicionado a full fill e lucro executável: corrigir a carteira e a informação temporal elimina aprovações indevidas, mas não fornece aceitação comercial. Trocar/tunar modelo perde prioridade enquanto essa entrada não existe. A próxima informação decisiva é o recibo de oferta nominal dentro do corte congelado, acompanhado de regras, capacidade e custos admissíveis. A captura DC mantém decisão em 11/09/2026 23:00 UTC, reserva20 e helpers intactos; a agenda não foi duplicada nem alterada. Capital permanece desabilitado.

## Trabalho que permanece

A lista evidence/semantic-remaining.json está vazia para o inventário permitido. Notas07 registram os últimos 70 testes lidos e seus limites; leitura não equivale a executar toda a suíte. Não executar fontes legacy que fazem consultas/treino no import. Corrigir dependências compartilhadas exige separar comprovadamente a operação protegida. Fonte comercial, estado legível da agenda, engine Linux e restauração operacional têm requisitos próprios ainda não satisfeitos. Essas limitações não foram convertidas em sucesso documental.

A wheel foi fechada com os mesmos 231 módulos Python atuais antes da atualização final dos relatórios. O sdist conserva a documentação do instante da construção; a entrega Git/ZIP acompanha estes relatórios mais recentes. Não se afirma igualdade do sdist com documentação editada posteriormente.

Na conferência final, o retry da CLI mostrava novo horário/hash apesar de preservar a linha anterior no ledger. Reproduzido com falha antes; agora stdout e run-log recebem exatamente o recibo persistido, sob a mesma trava. As 14 regressões de liquidação passaram após a correção.

Pacote atualizado após correção do retry: package-final-02. Comparação das wheels confirma que somente settle_live_prediction.py mudou desde o último ensaio entre processos; kernel/protocolo usados nesse ensaio permanecem byte idênticos. Build offline, instalação e CLIs do pacote atualizado passaram.
