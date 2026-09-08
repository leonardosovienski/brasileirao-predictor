param(
    [Parameter(Mandatory=$true)][string]$ValidationRoot,
    [string]$ReviewPython = 'C:\Users\Superleo13\projetos\brasileirao-predictor\.venv\Scripts\python.exe'
)
$ErrorActionPreference = 'Stop'
$reviewRoot = (Resolve-Path -LiteralPath $ValidationRoot).Path
$reviewRepo = Join-Path $reviewRoot 'integration-repo'
$reviewRunner = Join-Path $reviewRoot 'validation_runner.py'
$reviewGuard = Join-Path $reviewRoot 'guard\sitecustomize.py'
foreach ($reviewRequired in @($reviewRepo, $reviewRunner, $reviewGuard, $ReviewPython)) {
    if (-not (Test-Path -LiteralPath $reviewRequired)) { throw "Preparacao isolada ausente: $reviewRequired" }
}
$reviewLive = [IO.Path]::GetFullPath('C:\Users\Superleo13\projetos\brasileirao-predictor')
if ($reviewRepo.StartsWith($reviewLive + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'O checkout de teste deve ficar fora do repositorio operacional.'
}
if (Test-Path -LiteralPath (Join-Path $reviewRepo '.env')) { throw 'Checkout com .env nao pode ser usado.' }
$reviewDocker = (Get-Command docker -ErrorAction Stop).Source
foreach ($reviewPort in @(6380, 16389)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $reviewPort -ErrorAction SilentlyContinue) {
        throw "Porta $reviewPort ocupada. Nenhum servico existente sera interrompido."
    }
}
# Este host retornou exit 0 e versao vazia com daemon ausente: exigir versao real.
$reviewVersionJson = & $reviewDocker info --format '{{json .ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker indisponivel; nenhuma integracao executada.' }
try { $reviewVersion = $reviewVersionJson | ConvertFrom-Json } catch { $reviewVersion = '' }
if ($reviewVersion -notmatch '^\d+\.\d+') { throw 'Docker indisponivel; nenhuma integracao executada.' }
$reviewContainer = 'brasileirao-contracts-' + [guid]::NewGuid().ToString('N').Substring(0, 12)
$reviewCreated = $false
try {
    $reviewId = & $reviewDocker run --detach --rm --name $reviewContainer `
        --label 'codex.review=runtime-contracts-20260907' `
        --publish '127.0.0.1:6380:6379' --publish '127.0.0.1:16389:6379' `
        redis:8.2.1-alpine3.22 redis-server --appendonly no
    if ($LASTEXITCODE -ne 0 -or $reviewId -notmatch '^[0-9a-f]{64}$') { throw 'Falha ao criar Redis isolado.' }
    $reviewCreated = $true
    $reviewReady = $false
    for ($reviewAttempt = 0; $reviewAttempt -lt 30; $reviewAttempt++) {
        $reviewPing = & $reviewDocker exec $reviewContainer redis-cli ping
        if ($LASTEXITCODE -eq 0 -and $reviewPing -eq 'PONG') { $reviewReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $reviewReady) { throw 'Redis isolado nao respondeu no prazo.' }
    & $ReviewPython $reviewRunner redis_integration -- $ReviewPython -m pytest tests/test_redis_integration.py -q -o addopts= -m integration -p no:cacheprovider
    $reviewPythonExit = $LASTEXITCODE
    & $ReviewPython $reviewRunner dotnet_redis -- dotnet test dotnet/LineupWorker.Tests/LineupWorker.Tests.csproj --configuration Release --no-restore --filter 'FullyQualifiedName~WorkerRuntimeTests'
    $reviewDotnetExit = $LASTEXITCODE
    if ($reviewPythonExit -ne 0 -or $reviewDotnetExit -ne 0) { throw "Integracao falhou: Python=$reviewPythonExit; .NET=$reviewDotnetExit" }
    Write-Output 'Integracoes Redis passaram. Compose E2E e vantagem economica continuam fora deste teste.'
}
finally {
    if ($reviewCreated) { & $reviewDocker stop --time 10 $reviewContainer | Out-Null }
}
