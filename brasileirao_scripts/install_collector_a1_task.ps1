param([switch]$RunNow)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$uvExe = (Get-Command uv).Source
$collector = Join-Path $projectRoot "brasileirao_scripts\collect_odds_a1.py"
$metrics = Join-Path $projectRoot "brasileirao_scripts\collector_daily_metrics.py"

$persistedKey = [Environment]::GetEnvironmentVariable("ODDSPAPI_KEY", "User")
if (-not $persistedKey) {
    throw "ODDSPAPI_KEY ausente no ambiente do usuario. Confirme uma chave NOVA/rotacionada."
}

function Register-A1Task($name, $arguments, $triggers, $description) {
    $action = New-ScheduledTaskAction -Execute $uvExe -Argument $arguments -WorkingDirectory $projectRoot
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Settings $settings `
        -Principal $principal -Description $description -Force | Out-Null
    if ($RunNow) { Start-ScheduledTask -TaskName $name }
}

$collectTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 3650)
$discoverTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "06:00"
$metricsTrigger = New-ScheduledTaskTrigger -Daily -At "23:55"

Register-A1Task "brasileirao-a1-collect" ('run python "' + $collector + '" --collect') @($collectTrigger) `
    "A1 econômico: captura PIT shadow; nunca emite pick"
Register-A1Task "brasileirao-a1-discover" ('run python "' + $collector + '" --discover') @($discoverTrigger) `
    "A1 econômico: descoberta semanal de fixtures"
Register-A1Task "brasileirao-a1-metrics" ('run python "' + $metrics + '"') @($metricsTrigger) `
    "A1: métricas diárias REHEARSAL_ONLY"

Get-ScheduledTask -TaskName "brasileirao-a1-*" | Select-Object TaskName, State
