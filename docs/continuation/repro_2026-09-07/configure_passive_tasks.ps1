$ErrorActionPreference='Stop'
$operationRoot='C:\Users\Superleo13\projetos\brasileirao-predictor'
$pythonWindowless=Join-Path $operationRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonWindowless)) { throw 'pythonw missing' }
$mapping=[ordered]@{
    'brasileirao-h14-persist'=@('h14-persist',20)
    'brasileirao-h15-persist'=@('h15-persist',20)
    'brasileirao-h9-fixture-refresh'=@('fixture-refresh',95)
    'brasileirao-model-update'=@('model-update',35)
    'brasileirao-a1-collect'=@('a1-collect',10)
    'brasileirao-a1-discover'=@('a1-discover',10)
    'brasileirao-a1-metrics'=@('a1-metrics',10)
}
foreach ($name in $mapping.Keys) {
    $task=Get-ScheduledTask -TaskName $name
    if ($task.State -ne 'Disabled') { throw ('Expected disabled before configuring: '+$name) }
    if ($task.Settings.MultipleInstances -ne 'IgnoreNew') { throw 'Expected IgnoreNew' }
    $job=$mapping[$name][0]
    $action=New-ScheduledTaskAction -Execute $pythonWindowless -Argument ('-X utf8 -m brasileirao_scripts.run_passive_task '+$job) -WorkingDirectory $operationRoot
    $settings=$task.Settings
    $settings.ExecutionTimeLimit='PT'+$mapping[$name][1]+'M'
    Set-ScheduledTask -TaskName $name -Action $action -Settings $settings | Out-Null
}
Get-ScheduledTask -TaskName @($mapping.Keys) | ForEach-Object {
    [pscustomobject]@{name=$_.TaskName;state=[string]$_.State;execute=$_.Actions.Execute;arguments=$_.Actions.Arguments;interval=($_.Triggers.Repetition.Interval -join ',');timeout=$_.Settings.ExecutionTimeLimit}
} | ConvertTo-Json -Depth 3
