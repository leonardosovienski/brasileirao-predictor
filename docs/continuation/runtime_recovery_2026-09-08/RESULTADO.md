# Correções das pendências de recuperação e integração

Esta etapa fecha as falhas de software encontradas na recuperação de eventos,
resultados e sinais. A execução Docker/Compose continua bloqueada pelo ambiente
Windows e está identificada separadamente. Não se declara que todas as condições
de produção foram satisfeitas.

## O que mudou

- **Escalação perdida antes do registro:** a entrada canônica agora é uma Redis
  Stream. O Worker confirma somente após tratar o evento; reinício, cancelamento
  e falhas além de três tentativas preservam trabalho recuperável. O produtor
  recusa novas entradas quando a capacidade chega a 10.000, sem apagar pendências.
- **Previsão pronta sem notificação:** conclusão e índice de resultados prontos
  são gravados juntos. O consumidor consulta o índice, inclusive ao iniciar,
  durante a validade original da previsão. Um aviso perdido não exige novo cálculo.
- **Sinal perdido por ausência de assinante:** um lote aceito fica na outbox Redis,
  além do aviso Pub/Sub. Repetições não criam outro lote. A retenção é de 10.000
  lotes e não prolonga o prazo econômico. Não foi criado executor de apostas.
- **Healthcheck aprovando Worker morto:** o comando deixou de verificar apenas
  PING. Agora exige os loops de entrada e de consumo ativos, com TTL, sessão e
  instância correspondentes. Uma sessão antiga não renova nem remove a nova.
- **CLI Python ocultando falha:** a execução por `python -m` passou a propagar
  o retorno do healthcheck ao sistema operacional. Antes ela podia encerrar com
  sucesso mesmo quando a função de verificação retornava falha.
- **Escalação parcial marcada como completa:** o Worker exige 11 titulares
  distintos e valida identidade, lado e jogadores. A inbox recusa mensagens
  inválidas, antigas ou muito futuras, com diagnóstico sem ecoar o payload.
- **Falha de Redis derrubando o watchdog:** o acompanhamento é preservado para
  nova tentativa. A parada também remove a assinatura legada, e o Worker aguarda
  o VORP estar pronto antes de processar.
- **Watchdog esquecido após reinício:** prazo e índice de partidas incompletas
  passaram a ser persistidos junto do registro. A nova instância recupera o
  acompanhamento mesmo depois da confirmação e remoção da entrada original.
  Correções posteriores não renovam o prazo; conclusão e fallback limpam o índice
  com comparação do estado vigente.
- **Configuração Redis incorreta:** o cliente .NET passou a respeitar o usuário
  ACL da URL e a rejeitar um banco inválido em vez de selecionar silenciosamente
  o banco zero.
- **Build e CI:** os Dockerfiles passaram a usar os locks existentes; o contexto
  de build exclui bancos e segredos; o CI usa projeto Compose exclusivo por
  execução, espera saúde e restringe a limpeza aos recursos desse projeto.

## Evidência e validação

| Verificação | Resultado |
| --- | --- |
| Unitários Python dirigidos | 154 passaram: 139 do kernel, 12 do smoke e 3 do produtor da inbox |
| Integrações Python com Redis real | 30 passaram: 24 do kernel, 3 da capacidade/repetição/tipo da inbox e 3 da CLI em subprocesso |
| Suíte .NET final | 109 passaram; o único skip era o caso entre processos, executado separadamente |
| .NET/Python entre processos | 1 passou, sem skips; recupera o aviso inicial perdido e confirma deduplicação |
| Host .NET completo com kernel Python | Passou: inicialização real via Program/DI, dois smokes pela stream e healthchecks após parada abrupta |
| Cobertura .NET final | 839/969 linhas (86,58%); 350/426 ramos (82,15%); ambos os limites existentes de 80% passaram |
| Build .NET Release | Passou com recompilação completa e warnings como erros |
| Ruff, formato e Pyright dirigidos | Passaram; Pyright do smoke/produtor verificou dois arquivos, além da verificação dos módulos do kernel |
| Configuração Docker/CI | Exports travados, parser do Compose e política de contexto passaram; containers não executados |

Essas contagens distinguem testes unitários, integração e execução completa; não
representam uma nova execução de toda a suíte Python ou um backtest. A última
alteração no kernel foi a propagação do código de saída do módulo, verificada
pelos três testes novos da CLI e pela repetição do teste de hosts completos.

Os recibos finais e suas contagens estão em `estado.json`. Há reprodução da falha
anterior e correção aprovada para o aviso de resultado perdido e para o healthcheck
que passava sem Worker. Testes reais também verificam falhas de ACL, expiração,
repetição, recuperação da entrada e preservação da fila cheia.

Os testes usaram Redis 8.2.1 compilado da fonte oficial em uma distro WSL1 própria,
com porta e run_id conferidos, além de um checkout isolado. Python recebeu ambiente
por lista permitida e bloqueio de rede externa. As integrações utilizaram dados
sintéticos; o teste do daemon substitui apenas o carregamento de parâmetros por
uma tupla sintética. Não lê parâmetros ou resultados do banco operacional.

O teste do host usa um endpoint de mercado deliberadamente inerte. Ele verifica
inicialização, cálculo, entrada e saúde; a emissão de sinais com preços sintéticos
é verificada pelo teste separado entre processos. Nenhum dos dois atesta um feed
de preços operacional. Ao terminar, o Redis de teste foi encerrado e sua distro
removida às 04:41:33 UTC; a porta 26380 deixou de aceitar conexões.

Tentativas intermediárias permanecem nos recibos. O primeiro teste de hosts falhou
porque seu harness omitiu uma variável exigida pelo processo sintético; o segundo
expôs a falha real do código de saída Python. A reprodução independente dessa
falha exigiu heartbeat comprovadamente ausente antes da edição. Execuções que
deselecionaram todos os testes não contam como aprovação ou reprodução de bug.

Os arquivos protegidos, estudos encerrados e backups anteriores são conferidos
por SHA-256. Nenhum fit, backtest ou ajuste econômico foi repetido. Os resultados
financeiros anteriores continuam válidos como registros daquelas execuções;
estas correções não demonstram lucro nem autorizam capital real.

## Pendência do computador

Docker Desktop foi iniciado em processo comum, mas o engine não ficou disponível.
O Windows informa virtualização habilitada no firmware e hipervisor ausente nesta
inicialização. A tentativa isolada de WSL2 voltou a falhar com
`HCS_E_HYPERV_NOT_INSTALLED`; a consulta à configuração de boot recebeu acesso
negado. Isso não demonstra que a BIOS esteja desabilitada.

Para avançar, é necessário diagnóstico em PowerShell elevado. Primeiro consultar
`bcdedit /enum | findstr -i hypervisorlaunchtype`; se o resultado for `Off`, a
orientação documentada é habilitar o lançamento do hipervisor e reiniciar. Sem
esse resultado, não se afirma que alterar esse valor seja a solução. Recursos
ativados e reinício pendente também precisam ser verificados. A sequência e os
recibos estão em `evidencias/work/pending_closure/ENVIRONMENT.md`, com referências
à [documentação Microsoft](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting#common-issues).

Não houve alteração de boot, BIOS ou recursos do Windows, nem reinicialização.
O Compose sintético foi preparado e validado pelo parser, com volumes próprios,
rede interna e ambiente vazio. Build, inicialização dos containers e CI remoto
ainda não foram executados. Verificação local de configuração não substitui isso.

## Limites do contrato

Produtores devem migrar para `lineup:v2:inbox` para obter recuperação; o canal
legado `lineups:*` continua compatível e volátil. Uma escrita que o Redis não
aceitou precisa ser reenviada pelo produtor. A resistência a perda de estado do
servidor depende da persistência Redis configurada.

Previsões vencidas continuam sendo recusadas. A outbox permite recuperar registros
enquanto retidos; consumidores externos devem conferir versão vigente e prazo
antes de usar um sinal. Não existe garantia de execução financeira exatamente
uma vez. Disponibilidade do provedor e autenticidade do relógio declarado não
podem ser fabricadas pelo sistema. Essas são fronteiras explícitas, não resultados
econômicos novos nem uma declaração de implantação.

Os detalhes do contrato atual estão na cópia `codigo/contracts/redis-protocol-v2.md`.
Os checkpoints e relatórios antigos foram preservados como histórico.
