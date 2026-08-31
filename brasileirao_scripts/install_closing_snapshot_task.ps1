param([switch]$RunNow)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = (Get-Command python).Source
$entrypoint = Join-Path $projectRoot "brasileirao_scripts\record_closing_snapshots.py"
$taskName = "brasileirao-closing-snapshot"

if (-not (Test-Path -LiteralPath $entrypoint -PathType Leaf)) {
    throw "Entrypoint nao encontrado: $entrypoint"
}

# Horarios locais (UTC-3) escolhidos para cair logo antes dos apitos tipicos do
# Brasileirao (19:00 / 21:30 / 22:30 UTC). O script se auto-protege: fora da
# janela de 4h antes de um apito ele sai sem gastar cota da The Odds API.
$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument ('-X utf8 "' + $entrypoint + '"') `
    -WorkingDirectory $projectRoot
$triggers = @(
    (New-ScheduledTaskTrigger -Daily -At "15:45"),
    (New-ScheduledTaskTrigger -Daily -At "18:15"),
    (New-ScheduledTaskTrigger -Daily -At "19:15")
)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers `
    -Settings $settings -Principal $principal `
    -Description "Snapshot do bookmaker perto do apito para o fechamento do CLV; NAO emite pick" `
    -Force | Out-Null

if ($RunNow) { Start-ScheduledTask -TaskName $taskName }
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName $taskName | Select-Object LastRunTime, LastTaskResult, NextRunTime
