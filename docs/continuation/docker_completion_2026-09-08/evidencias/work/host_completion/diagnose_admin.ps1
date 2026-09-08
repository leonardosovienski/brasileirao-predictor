param([Parameter(Mandatory=$true)][string]$ReceiptDirectory)
$ErrorActionPreference = 'Stop'
$receiptRoot = [IO.Path]::GetFullPath($ReceiptDirectory)
$expectedRoot = 'C:\Users\Superleo13\Documents\Codex\2026-09-07\leia-e-execute-c-users-superleo13\work\host_completion\'
if (-not $receiptRoot.StartsWith($expectedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Receipt path is outside the task directory.' }
[IO.Directory]::CreateDirectory($receiptRoot) | Out-Null
$record = [ordered]@{ started_at_utc = [DateTime]::UtcNow.ToString('o'); read_only = $true; changes_performed = @(); status = 'RUNNING' }
function Save-Record {
    $record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $receiptRoot 'diagnosis.json') -Encoding UTF8
}
try {
    $record.elevated = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    Save-Record
    if (-not $record.elevated) { throw 'Administrator token was not granted.' }
    $record.computer = Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent
    $record.cpu = Get-CimInstance Win32_Processor | Select-Object VirtualizationFirmwareEnabled, SecondLevelAddressTranslationExtensions
    $record.os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, LastBootUpTime
    $bcdOutput = & "$env:SystemRoot\System32\bcdedit.exe" /enum '{current}' 2>&1
    $record.bcd_exit_code = $LASTEXITCODE
    $record.bcd_current = ($bcdOutput | Out-String).Trim()
    if ($record.bcd_exit_code -ne 0) { throw 'Unable to read the current boot entry.' }
    $launchMatch = [regex]::Match($record.bcd_current, '(?im)^hypervisorlaunchtype\s+(\S+)')
    $record.hypervisorlaunchtype = if ($launchMatch.Success) { $launchMatch.Groups[1].Value } else { 'NOT_EXPLICIT' }
    $record.features = @('Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform', 'Microsoft-Hyper-V-Hypervisor') | ForEach-Object {
        try { Get-WindowsOptionalFeature -Online -FeatureName $_ | Select-Object FeatureName, State, RestartRequired }
        catch { [PSCustomObject]@{ FeatureName = $_; Error = $_.Exception.Message } }
    }
    $record.reboot_pending = [ordered]@{
        servicing = Test-Path -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending'
        windows_update = Test-Path -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'
        pending_file_renames = $null -ne (Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -Name PendingFileRenameOperations -ErrorAction SilentlyContinue)
    }
    $record.services = Get-Service -Name 'com.docker.service', 'vmcompute', 'LxssManager', 'WslService' -ErrorAction SilentlyContinue | Select-Object Name, Status, StartType
    try {
        $record.bitlocker_system_volume = Get-BitLockerVolume -MountPoint $env:SystemDrive -ErrorAction Stop | Select-Object MountPoint, ProtectionStatus, VolumeStatus
    } catch { $record.bitlocker_query_error = $_.Exception.Message }
    $record.status = 'PASS'
} catch {
    $record.status = 'FAILED'
    $record.error = $_.Exception.Message
} finally {
    $record.finished_at_utc = [DateTime]::UtcNow.ToString('o')
    Save-Record
}
if ($record.status -ne 'PASS') { exit 1 }
exit 0
