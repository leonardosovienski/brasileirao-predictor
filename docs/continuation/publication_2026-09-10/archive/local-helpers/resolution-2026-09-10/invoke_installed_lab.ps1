param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$Filter,
    [string]$SourceRepo = 'C:\BRASILEIRAO\brasileirao-predictor'
)
$taskLabRoot = 'C:\BRASILEIRAO\work\resolution-2026-09-10'
if ($Name -notmatch '^[a-z0-9-]+$') { throw 'Explicit new lab name required' }
& 'C:\BRASILEIRAO\work\resolution-2026-09-10\installed-cross-environment\venv\Scripts\python.exe' -X utf8 -I -B "$taskLabRoot\run_dotnet_installed.py" --output "$taskLabRoot\$Name" --repo $SourceRepo --server 'C:\BRASILEIRAO\work\implementacao-2026-09-10\software\redis-8.2.9\Redis-8.2.9-Windows-x64-msys2\redis-server.exe' --server-sha256 'f9bf66f93438ec461b6e32453e6c9a8dde2f8c93c1018d1b75aa38b113ba3f14' --dotnet 'C:\BRASILEIRAO\work\revisao-integral-2026-09-09\dotnet-sdk\dotnet.exe' --nuget-cache 'C:\BRASILEIRAO\work\revisao-integral-2026-09-09\nuget-packages' --test-filter $Filter
exit $LASTEXITCODE

