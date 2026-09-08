# Continuação da integração Docker — 08/09/2026

Foi corrigida uma falha adicional na configuração sintética do teste Compose.
A execução dos containers continua pendente: os dois endpoints locais do Docker
estão indisponíveis e a tentativa de diagnóstico administrativo foi cancelada
pelo Windows. Esta etapa não atesta build de imagens, integração Compose ou CI remoto.

## Correção e verificações concluídas

O arquivo VORP do harness anterior usava `replacement`, enquanto o carregador
`VorpStateService.StartAsync` exige `replacement_levels`. Isso permitiria passar
no parser YAML, mas impediria a inicialização correta do Worker. A nova cópia de
teste corrige a chave. O arquivo real `docker/vorp.json` e o Compose usado pelo CI
já estavam corretos; não foi necessária alteração no código da aplicação.

O novo projeto isolado passou no parser Compose, na verificação dos contratos das
fixtures e na criação/leitura de dois bancos exclusivamente sintéticos, usando
`init_compose_data` e `_load_params` reais. Não houve ajuste de modelo. Os 36
arquivos declarados no estado anterior foram conferidos; os 35 arquivos de
runtime/testes/configuração coincidem com a cópia isolada. O Markdown do contrato
é a exceção documental já declarada.

A primeira checagem da configuração normalizada esperava `create_host_path: false`
explícito; o Compose representa esse padrão como `bind: {}`. A checagem foi
corrigida, e a tentativa inicial permanece no registro. Isso não era um erro do
Compose. Esses recibos são verificações offline, não testes em containers.

A busca de produtores também foi concluída: não existe produtor interno real
esquecido em `lineups:*`. As publicações encontradas são testes legados; o smoke
já usa a inbox. Os capturadores SofaScore gravam arquivos/SQLite. Conectar um
provedor externo à inbox exige uma integração específica, não a migração de um
produtor existente neste repositório.

As evidências estão em `evidencias/work/compose_completion/` e
`evidencias/work/host_completion/PRODUCER_AUDIT.md`. Os recibos desta etapa e a
verificação dos arquivos protegidos e backups estão em `estado.json`.

## Bloqueio confirmado no Windows

Em 08/09/2026 às 12:26 UTC, o Windows informou:

- virtualização habilitada no firmware e SLAT disponível;
- `HypervisorPresent = false`;
- inicialização atual desde 06/09/2026;
- sessão de execução sem token de administrador.

Às 12:28 UTC, tanto `docker_engine` quanto `dockerDesktopLinuxEngine` estavam sem
pipe disponível e retornaram `Server: null`. As sondagens usaram endpoints locais
explícitos e configuração Docker vazia, sem credenciais ou mudança de contexto.

Foi solicitada uma única elevação normal do Windows, somente para diagnóstico.
`Start-Process -Verb RunAs` retornou “A operação foi cancelada pelo usuário”. O
helper elevado não iniciou e não produziu diagnóstico. A solicitação não foi
repetida. Não houve alteração de boot, BIOS, recursos do Windows,
serviços, reinicialização ou criação de containers nesta etapa.

## Ação necessária para concluir

É necessário conceder acesso administrativo para ler a configuração de boot.
Em um PowerShell aberto **como administrador**, o diagnóstico inicial é:

```powershell
bcdedit /enum '{current}'
Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
```

Somente se `hypervisorlaunchtype` estiver explicitamente `Off`, a correção
documentada é `bcdedit /set '{current}' hypervisorlaunchtype Auto`, seguida de
reinicialização. O valor ainda não foi lido; não se afirma que esse seja o reparo
necessário. Se os componentes já estiverem habilitados e o lançamento automático
ativo, será preciso investigar a falha de carregamento. A sequência segue a
[documentação Microsoft do WSL](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting#common-issues)
e os [requisitos de virtualização do Docker](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/topics/).

Depois que o Docker apresentar um Server Linux válido, o harness preparado permite
retomar build, inicialização, smoke, recuperação após falhas e limpeza somente dos
recursos do projeto de teste. Seu plano de execução permanece sem validação em
containers. O mercado é deliberadamente inerte: essa execução também não será
prova de um feed de preços operacional nem de lucro.

Nenhum resultado econômico, estudo encerrado, agenda, coorte ou arquivo protegido
foi alterado. Os testes Python/.NET aprovados na etapa anterior permanecem como
evidência daquela execução; não foram somados novamente como testes desta etapa.
