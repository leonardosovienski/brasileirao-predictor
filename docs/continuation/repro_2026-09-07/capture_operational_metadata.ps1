$ErrorActionPreference = 'Stop'
$taskRepo = 'C:\Users\Superleo13\projetos\brasileirao-predictor'
$outputRoot = 'C:\Users\Superleo13\Documents\Codex\2026-09-07\le\outputs'
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$taskRows = @(Get-ScheduledTask -TaskName 'brasileirao-*' | ForEach-Object {
    $info = Get-ScheduledTaskInfo -TaskName $_.TaskName
    [ordered]@{
        name = $_.TaskName
        state = [string]$_.State
        working_directory = @($_.Actions.WorkingDirectory)
        last_run = $(if ($info.LastRunTime) { $info.LastRunTime.ToString('o') } else { $null })
        last_task_result = $info.LastTaskResult
        next_run = $(if ($info.NextRunTime) { $info.NextRunTime.ToString('o') } else { $null })
    }
})
$snapshotFiles = @(Get-ChildItem -LiteralPath (Join-Path $taskRepo 'data\odds_snapshots') -File | ForEach-Object {
    [ordered]@{name=$_.Name; bytes=$_.Length; last_write_utc=$_.LastWriteTimeUtc.ToString('o')}
})
$database = Get-Item -LiteralPath (Join-Path $taskRepo 'data\matches.db')
$ledgerFiles = @('h14_serving_vs_climatologia.jsonl','h15_refit10_vs_100.jsonl') | ForEach-Object {
    $itemPath = Join-Path $taskRepo ('data\research\' + $_)
    if (Test-Path -LiteralPath $itemPath) {
        $item = Get-Item -LiteralPath $itemPath
        [ordered]@{name=$item.Name; exists=$true; bytes=$item.Length; last_write_utc=$item.LastWriteTimeUtc.ToString('o')}
    } else {
        [ordered]@{name=$_; exists=$false}
    }
}
$report = [ordered]@{
    schema_version='brasileirao-validation-operational-metadata/1'
    observed_at_utc=[DateTime]::UtcNow.ToString('o')
    measurement_scope='Filesystem metadata and Windows task state only. No database, snapshot, result, credential or cohort contents opened.'
    operational_repository=$taskRepo
    operational_head=(& git -C $taskRepo rev-parse HEAD)
    audit_head='02b8d88fa0b15ba28565351848a9737b2edcda48'
    task_count=$taskRows.Count
    disabled_task_count=@($taskRows | Where-Object { $_.state -eq 'Disabled' }).Count
    tasks=$taskRows
    database=[ordered]@{exists=$true; bytes=$database.Length; last_write_utc=$database.LastWriteTimeUtc.ToString('o')}
    a1_snapshot_files=$snapshotFiles
    protected_ledger_metadata=@($ledgerFiles)
    warning='A task LastTaskResult of zero does not prove coverage, collection continuity or scientific validity. Filenames and timestamps do not prove row contents.'
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputRoot 'estado_operacional_observado.json') -Encoding utf8
$report | Select-Object observed_at_utc,task_count,disabled_task_count,database,a1_snapshot_files,protected_ledger_metadata | ConvertTo-Json -Depth 5
