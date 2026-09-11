param([string]$Attempt='02')
$ErrorActionPreference='Continue'
$riRoot=$PSScriptRoot
Get-ChildItem Env: | Where-Object {$_.Name -notin @('SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT','PROCESSOR_ARCHITECTURE','NUMBER_OF_PROCESSORS','ProgramFiles','ProgramFiles(x86)','ProgramW6432','ProgramData','ALLUSERSPROFILE','SystemDrive')} | ForEach-Object {Remove-Item -LiteralPath ('Env:'+ $_.Name)}
$env:DOTNET_ROOT=Join-Path $riRoot 'dotnet-sdk'
$env:DOTNET_CLI_HOME=Join-Path $riRoot 'dotnet-home'
$env:APPDATA=Join-Path $riRoot 'dotnet-appdata'
$env:LOCALAPPDATA=Join-Path $riRoot 'dotnet-localappdata'
$env:USERPROFILE=Join-Path $riRoot 'dotnet-profile'
$env:NUGET_PACKAGES=Join-Path $riRoot 'nuget-packages'
$env:NUGET_HTTP_CACHE_PATH=Join-Path $riRoot 'nuget-http-cache'
$env:TEMP=Join-Path $riRoot 'dotnet-tmp'
$env:TMP=$env:TEMP
@($env:APPDATA,$env:LOCALAPPDATA,$env:USERPROFILE,$env:TEMP) | ForEach-Object {New-Item -ItemType Directory -Path $_ -Force | Out-Null}
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE='false'
$env:DOTNET_NOLOGO='1'
$env:PATH=$env:DOTNET_ROOT+';'+$env:PATH
Set-Location -LiteralPath (Join-Path $riRoot 'dotnet-work')
$restore=Join-Path $riRoot ('dotnet-restore-'+$Attempt+'.log')
$build=Join-Path $riRoot ('dotnet-build-'+$Attempt+'.log')
$test=Join-Path $riRoot ('dotnet-test-'+$Attempt+'.log')
if((Test-Path $restore) -or (Test-Path $build) -or (Test-Path $test)){throw 'Use another attempt id; preserve receipts.'}
& "$env:DOTNET_ROOT\dotnet.exe" restore dotnet/LineupWorker.Tests/LineupWorker.Tests.csproj --locked-mode --configfile "$riRoot\NuGet.Config" *> $restore
if($LASTEXITCODE -ne 0){Get-Content $restore -Tail 40; exit $LASTEXITCODE}
& "$env:DOTNET_ROOT\dotnet.exe" build dotnet/LineupWorker/LineupWorker.csproj --configuration Release --no-restore --warnaserror *> $build
if($LASTEXITCODE -ne 0){Get-Content $build -Tail 40; exit $LASTEXITCODE}
& "$env:DOTNET_ROOT\dotnet.exe" test dotnet/LineupWorker.Tests/LineupWorker.Tests.csproj --configuration Release --no-restore --collect:'XPlat Code Coverage' --results-directory "$riRoot\dotnet-test-results-$Attempt" *> $test
$code=$LASTEXITCODE
Get-Content $test -Tail 35
exit $code
