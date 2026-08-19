$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo ".venv\Scripts\predictor-ops.exe"
$python = Join-Path $repo ".venv\Scripts\python.exe"
$config = Join-Path $repo "jobs.market-research.example.json"
if (-not (Test-Path -LiteralPath $runner)) { throw "predictor-ops runner not found" }
if (-not (Test-Path -LiteralPath $python)) { throw "venv python not found" }
if (-not (Test-Path -LiteralPath $config)) { throw "jobs config not found" }

function Install-PredictorTask {
    param([string]$Name, [string]$Job, [object]$Trigger)
    $arguments = "run --config `"$config`" --job $Job --runtime-root `"$repo\data\runtime`""
    $action = New-ScheduledTaskAction -Execute $runner -Argument $arguments -WorkingDirectory $repo
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $Trigger -Settings $settings -Description "Brasileirao predictor COLLECTION_ONLY; capital disabled" -Force | Out-Null
}

function Install-ScriptTask {
    param([string]$Name, [string]$ScriptPath, [object]$Trigger, [string]$Description, [int]$TimeLimitMinutes = 10)
    $arguments = "`"$ScriptPath`""
    $action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $repo
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -ExecutionTimeLimit (New-TimeSpan -Minutes $TimeLimitMinutes)
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $Trigger -Settings $settings -Description $Description -Force | Out-Null
}

$collection = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours 6)
$readiness = New-ScheduledTaskTrigger -Daily -At "06:15"
Install-PredictorTask -Name "brasileirao-market-research" -Job "brasileirao-market-research-featured" -Trigger $collection
Install-PredictorTask -Name "brasileirao-prospective-readiness" -Job "brasileirao-prospective-readiness" -Trigger $readiness

# OPS-P0: coorte prospectiva H9 — nunca perder dado enquanto a pesquisa acontece.
$h9Emit = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 15)
$h9Closing = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(3) -RepetitionInterval (New-TimeSpan -Minutes 15)
$h9Settle = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(4) -RepetitionInterval (New-TimeSpan -Minutes 30)
$h9Backup = New-ScheduledTaskTrigger -Daily -At "05:00"
$h9Missed = New-ScheduledTaskTrigger -Daily -At "07:00"

Install-ScriptTask -Name "brasileirao-h9-emit" -ScriptPath (Join-Path $repo "scripts\emit_h9_shadow.py") -Trigger $h9Emit -Description "H9 shadow: funil de decisao (15min)"
Install-ScriptTask -Name "brasileirao-h9-closing" -ScriptPath (Join-Path $repo "scripts\record_h9_closing_snapshots.py") -Trigger $h9Closing -Description "H9 shadow: snapshots de fechamento (15min)"
Install-ScriptTask -Name "brasileirao-h9-settle" -ScriptPath (Join-Path $repo "scripts\settle_h9_shadow.py") -Trigger $h9Settle -Description "H9 shadow: liquidacao pos-jogo (30min)"
Install-ScriptTask -Name "brasileirao-h9-backup" -ScriptPath (Join-Path $repo "scripts\backup_h9_runtime.py") -Trigger $h9Backup -Description "H9 shadow: backup diario do ledger + integrity check" -TimeLimitMinutes 20
Install-ScriptTask -Name "brasileirao-h9-missed-window" -ScriptPath (Join-Path $repo "scripts\report_h9_missed_windows.py") -Trigger $h9Missed -Description "H9 shadow: alerta de jogos que deveriam ter entrado na janela e nao entraram" -TimeLimitMinutes 15

foreach ($legacy in "brasileirao-archival-collection", "brasileirao-closing-snapshot", "brasileirao-sombra-manha", "brasileirao-sombra-noite") {
    if (Get-ScheduledTask -TaskName $legacy -ErrorAction SilentlyContinue) {
        Disable-ScheduledTask -TaskName $legacy | Out-Null
    }
}

Get-ScheduledTask -TaskName "brasileirao-market-research", "brasileirao-prospective-readiness", `
    "brasileirao-h9-emit", "brasileirao-h9-closing", "brasileirao-h9-settle", "brasileirao-h9-backup", "brasileirao-h9-missed-window" |
    Select-Object TaskName, State
