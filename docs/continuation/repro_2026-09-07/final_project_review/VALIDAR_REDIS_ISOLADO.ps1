# Execute depois de iniciar o Docker Desktop (pode exigir PowerShell como Administrador).
# Usa somente o checkout de teste e um Redis descartavel, sem volumes nem banco real.
$ErrorActionPreference = 'Stop'
$reviewRoot = 'C:\Users\Superleo13\Documents\Codex\2026-09-07\le\work\final_project_review'
$reviewPython = 'C:\Users\Superleo13\projetos\brasileirao-predictor\.venv\Scripts\python.exe'
$reviewDockerCmd = (Get-Command docker -ErrorAction Stop).Source
$reviewContainer = 'brasileirao-review-' + [guid]::NewGuid().ToString('N').Substring(0, 12)
$reviewCreated = $false

foreach ($reviewPort in @(6380, 16389)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $reviewPort -ErrorAction SilentlyContinue) {
        throw "Porta $reviewPort ocupada. Nenhum servico existente sera interrompido."
    }
}
& $reviewDockerCmd info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker indisponivel. Inicie o Docker Desktop e repita.' }
try {
    & $reviewDockerCmd run --detach --rm --name $reviewContainer --label 'codex.review=brasileirao-final-20260907' `
        --publish '127.0.0.1:6380:6379' --publish '127.0.0.1:16389:6379' `
        redis:8.2.1-alpine3.22 redis-server --appendonly no
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar Redis isolado.' }
    $reviewCreated = $true
    $reviewReady = $false
    for ($reviewAttempt = 0; $reviewAttempt -lt 30; $reviewAttempt++) {
        $reviewPing = & $reviewDockerCmd exec $reviewContainer redis-cli ping
        if ($LASTEXITCODE -eq 0 -and $reviewPing -eq 'PONG') { $reviewReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $reviewReady) { throw 'Redis isolado nao respondeu no prazo.' }
    & $reviewPython "$reviewRoot\run_check.py" redis_integration -- $reviewPython -m pytest tests/test_redis_integration.py -q -o addopts= -m integration -p no:cacheprovider
    $reviewPythonExit = $LASTEXITCODE
    & $reviewPython "$reviewRoot\run_check.py" dotnet_redis -- dotnet test dotnet/LineupWorker.Tests/LineupWorker.Tests.csproj --configuration Release --no-restore --filter 'FullyQualifiedName~WorkerRuntimeTests' --logger 'trx;LogFileName=dotnet_redis.trx' --results-directory "$reviewRoot\dotnet_results"
    $reviewDotnetExit = $LASTEXITCODE
    if ($reviewPythonExit -ne 0 -or $reviewDotnetExit -ne 0) {
        throw "Integracao falhou: Python=$reviewPythonExit; .NET=$reviewDotnetExit. Consulte os logs em $reviewRoot."
    }
    Write-Output 'Integracao Redis Python/.NET aprovada. Isso nao demonstra lucro nem substitui o E2E Compose completo.'
}
finally {
    if ($reviewCreated) { & $reviewDockerCmd stop --time 10 $reviewContainer | Out-Null }
}
