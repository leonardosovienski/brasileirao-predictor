$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo ".venv\Scripts\predictor-ops.exe"
$config = Join-Path $repo "jobs.market-research.example.json"
if (-not (Test-Path -LiteralPath $runner)) { throw "predictor-ops runner not found" }
if (-not (Test-Path -LiteralPath $config)) { throw "jobs config not found" }

function Install-PredictorTask {
    param([string]$Name, [string]$Job, [object]$Trigger)
    $arguments = "run --config `"$config`" --job $Job --runtime-root `"$repo\data\runtime`""
    $action = New-ScheduledTaskAction -Execute $runner -Argument $arguments -WorkingDirectory $repo
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $Trigger -Settings $settings -Description "Brasileirao predictor COLLECTION_ONLY; capital disabled" -Force | Out-Null
}

$collection = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours 6)
$readiness = New-ScheduledTaskTrigger -Daily -At "06:15"
Install-PredictorTask -Name "brasileirao-market-research" -Job "brasileirao-market-research-featured" -Trigger $collection
Install-PredictorTask -Name "brasileirao-prospective-readiness" -Job "brasileirao-prospective-readiness" -Trigger $readiness

foreach ($legacy in "brasileirao-archival-collection", "brasileirao-closing-snapshot", "brasileirao-sombra-manha", "brasileirao-sombra-noite") {
    if (Get-ScheduledTask -TaskName $legacy -ErrorAction SilentlyContinue) {
        Disable-ScheduledTask -TaskName $legacy | Out-Null
    }
}

Get-ScheduledTask -TaskName "brasileirao-market-research", "brasileirao-prospective-readiness" |
    Select-Object TaskName, State
