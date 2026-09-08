# Reprodução isolada dos contratos do runtime

Não executar a suíte contra o repositório operacional. Não copiar `.env`, bancos, ledgers, caches de modelo ou resultados protegidos. Os comandos abaixo usam a base exata mais as fontes desta etapa, inclusive sem commit. Use uma pasta nova para `$checkRoot`.

```powershell
$repo = 'C:\Users\Superleo13\projetos\brasileirao-predictor'
$package = Join-Path $repo 'docs\continuation\runtime_contracts_2026-09-07'
$checkRoot = 'C:\Users\Superleo13\projetos\brasileirao-predictor-sessoes\2026-09-07\work\runtime-reproduction'
$python = Join-Path $repo '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $checkRoot) { throw 'Escolha uma pasta nova; nao sobrescrever uma reproducao existente.' }
New-Item -ItemType Directory -Path $checkRoot | Out-Null
$snapshot = Join-Path $checkRoot 'integration-repo'
$state = Get-Content -LiteralPath (Join-Path $package 'estado.json') -Raw | ConvertFrom-Json
git -C $repo worktree add --detach $snapshot $state.base_commit
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar worktree.' }
Copy-Item -LiteralPath (Join-Path $package 'validation_runner.py') -Destination $checkRoot
Copy-Item -LiteralPath (Join-Path $package 'guard') -Destination $checkRoot -Recurse
foreach ($entry in $state.changed_sha256.PSObject.Properties) {
    $source = Join-Path (Join-Path $package 'codigo') $entry.Name
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLower() -ne $entry.Value) { throw 'Fonte diverge do hash.' }
    $target = Join-Path $snapshot $entry.Name
    Copy-Item -LiteralPath $source -Destination $target
}
$runner = Join-Path $checkRoot 'validation_runner.py'
& $python $runner python_contracts -- $python -m pytest tests/test_kernel_protocol.py tests/test_kernel_runtime.py tests/test_redis_contract.py -q -p no:cacheprovider
& $python $runner dotnet_restore -- dotnet restore dotnet/LineupWorker.Tests/LineupWorker.Tests.csproj --locked-mode --ignore-failed-sources
& $python $runner dotnet_build -- dotnet build dotnet/LineupWorker/LineupWorker.csproj --configuration Release --no-restore --warnaserror
& $python $runner dotnet_unit -- dotnet test dotnet/LineupWorker.Tests/LineupWorker.Tests.csproj --configuration Release --no-restore --filter 'FullyQualifiedName!~WorkerRuntimeTests'
& $python $runner lint -- $python -m ruff check brasileirao_predictor/kernel_daemon.py tests/test_kernel_protocol.py
& $python $runner format -- $python -m ruff format --check brasileirao_predictor/kernel_daemon.py tests/test_kernel_protocol.py
& $python $runner types -- $python -m pyright brasileirao_predictor/kernel_daemon.py --pythonpath $python
& $python $runner compose_config -- docker compose config --format json
```

Conferir cada código de saída e os recibos em `$checkRoot/validation`. Os resultados esperados desta etapa são 119 testes Python e 46 .NET. Logs de configuração são de um checkout sem credenciais e contêm apenas defaults.

Quando o Docker estiver funcionando, iniciar apenas a integração descartável:

```powershell
& (Join-Path $package 'VALIDAR_REDIS_ISOLADO.ps1') -ValidationRoot $checkRoot -ReviewPython $python
```

Esse comando executa 1 teste Python Redis e os 13 WorkerRuntime. **Não foi executado com Docker disponível nesta etapa.** As portas 6380 e 16389 devem estar livres: os testes usam `FLUSHDB`, portanto nunca redirecionar para Redis existente. O script cria um Redis novo, sem volumes, e para somente esse container. Isso não substitui Compose E2E; para ele, usar nome de projeto exclusivo e recursos descartáveis, conforme os passos sintéticos em `.github/workflows/ci.yml`.

O runner depende do ambiente operacional preservado. Se ele deixar de existir, reconstruir as versões fixadas a partir de `pyproject.toml` e `uv.lock` em ambiente separado. Não atualizar dependências operacionais para igualar outro clone.
