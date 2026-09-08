# A opcao (b) foi autorizada pelo operador. Este script resolve somente
# o bloqueio de permissao do Windows nas duas tarefas H14/H15 existentes.
# Execute em PowerShell aberto como Administrador. Nao avalia coortes.
param([ValidateRange(1, 120)][int]$WaitMinutes = 95)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Abra PowerShell como Administrador e execute este arquivo novamente.'
}
$repo = 'C:\Users\Superleo13\projetos\brasileirao-predictor'
$expected = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'retomada_integridade.json') -Raw | ConvertFrom-Json
foreach ($property in $expected.protected_sha256.PSObject.Properties) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $repo $property.Name) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $property.Value) { throw ('Fonte protegida mudou; revisar antes de continuar: ' + $property.Name) }
}
$runner = Join-Path $repo 'brasileirao_scripts\run_passive_task.py'
if ((Get-FileHash -LiteralPath $runner -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected.wrapper_sha256) {
    throw 'O launcher mudou desde a validacao; revisar antes de continuar.'
}
$freshInput = $false
$deadline = [DateTimeOffset]::UtcNow.AddMinutes($WaitMinutes)
$heartbeatPath = Join-Path $repo 'data\runtime\passive\fixture-refresh\heartbeat.json'
do {
    $running = $false
    if (Test-Path -LiteralPath $heartbeatPath) {
        $heartbeat = Get-Content -LiteralPath $heartbeatPath -Raw | ConvertFrom-Json
        if ($heartbeat.job -ne 'fixture-refresh' -or $heartbeat.wrapper_sha256 -ne $expected.wrapper_sha256) {
            throw 'Heartbeat de infraestrutura incompativel com a preparacao.'
        }
        $running = $heartbeat.status -eq 'started'
        if ($heartbeat.status -eq 'finished' -and $null -ne $heartbeat.exit_code -and $heartbeat.exit_code -eq 0 -and $heartbeat.finished_at) {
            $age = [DateTimeOffset]::UtcNow - [DateTimeOffset]::Parse([string]$heartbeat.finished_at)
            if ($age.TotalHours -ge 0 -and $age.TotalHours -lt 12) {
                $logText = Get-Content -LiteralPath $heartbeat.log_path -Raw
                if ($logText -notmatch 'H9_INPUT_REFRESH_OK step=elo_cache' -or $logText -match ' falhou') {
                    throw 'Atualizacao de insumos tem falha ou nao concluiu todos os passos; revisar saude operacional.'
                }
                $freshInput = $true
            }
        }
    }
    if (-not $freshInput -and $running -and [DateTimeOffset]::UtcNow -lt $deadline) {
        Write-Progress -Activity 'Retomada H14/H15' -Status 'Aguardando a atualizacao inicial dos insumos e cache'
        Start-Sleep -Seconds 5
    } else { break }
} while (-not $freshInput)
Write-Progress -Activity 'Retomada H14/H15' -Completed
if (-not $freshInput) { throw 'Sem atualizacao operacional bem-sucedida nas ultimas 12h; conferir tarefas de insumos/cache.' }
$pythonw = Join-Path $repo '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw -PathType Leaf)) { throw 'pythonw.exe ausente.' }
$mapping = [ordered]@{'brasileirao-h14-persist'='h14-persist'; 'brasileirao-h15-persist'='h15-persist'}
$validatedTasks = @{}
foreach ($name in $mapping.Keys) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction Stop
    if ($task.State -eq 'Running') { throw ('Tarefa em execucao: ' + $name) }
    if ($task.Settings.MultipleInstances -ne 'IgnoreNew') { throw ('Concorrencia inesperada: ' + $name) }
    if (@($task.Triggers).Count -ne 1 -or $task.Triggers[0].Repetition.Interval -ne 'PT15M') {
        throw ('Cadencia diferente do contrato esperado: ' + $name)
    }
    $validatedTasks[$name] = $task
}
foreach ($name in $mapping.Keys) {
    $task = $validatedTasks[$name]
    $action = New-ScheduledTaskAction -Execute $pythonw -Argument ('-X utf8 -m brasileirao_scripts.run_passive_task ' + $mapping[$name]) -WorkingDirectory $repo
    $settings = $task.Settings
    $settings.ExecutionTimeLimit = 'PT20M'
    Set-ScheduledTask -TaskName $name -Action $action -Settings $settings -ErrorAction Stop | Out-Null
}
foreach ($name in $mapping.Keys) {
    Enable-ScheduledTask -TaskName $name -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $name -ErrorAction Stop
}
$receipt = [ordered]@{
    changed_at_utc = [DateTime]::UtcNow.ToString('o')
    action = 'ENABLE_EXISTING_H14_H15_PASSIVE_COLLECTION'
    scientific_evaluation = $false
    tasks = @(Get-ScheduledTask -TaskName @($mapping.Keys) | ForEach-Object {
        [ordered]@{name=$_.TaskName; state=[string]$_.State; enabled=$_.Settings.Enabled}
    })
}
$receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'retomada_h14_h15_administrador.json') -Encoding utf8
Write-Output 'H14/H15 habilitadas e acionadas. Isso confirma o agendamento; a conclusao da coleta aparece nos heartbeats operacionais.'
$receipt.tasks | ForEach-Object { [pscustomobject]$_ } | Format-Table
