$ErrorActionPreference = 'Stop'
$record = [ordered]@{
    captured_at_utc = [DateTime]::UtcNow.ToString('o')
    scope = 'Read-only host checks after cancelled UAC; no retry of elevation'
    elevated = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    computer = Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent
    cpu = Get-CimInstance Win32_Processor | Select-Object VirtualizationFirmwareEnabled, SecondLevelAddressTranslationExtensions
    os = Get-CimInstance Win32_OperatingSystem | Select-Object Version, BuildNumber, LastBootUpTime
    changes_performed = @()
    restart_performed = $false
}
$record.services = Get-Service -Name 'com.docker.service','vmcompute','WslService' -ErrorAction SilentlyContinue | ForEach-Object { [ordered]@{ name = $_.Name; status = $_.Status.ToString(); start_type = $_.StartType.ToString() } }
$record.elevation_attempt = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'admin_diagnosis_20260908T1223/launch.json') -Raw | ConvertFrom-Json
$record | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'preflight.json') -Encoding UTF8
$record | ConvertTo-Json -Depth 10
