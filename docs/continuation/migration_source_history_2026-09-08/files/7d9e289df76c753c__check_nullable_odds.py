"""Prove the null-odds regression against baseline, then restore the patch."""
from pathlib import Path
import subprocess
import sys

work = Path(__file__).resolve().parent
repo = work / "integration-repo"
target = repo / "dotnet/LineupWorker/Models/KernelContracts.cs"
patched = target.read_bytes()
try:
    baseline = subprocess.check_output(
        ["git", "show", "HEAD:dotnet/LineupWorker/Models/KernelContracts.cs"], cwd=repo
    )
    target.write_bytes(baseline)
    result = subprocess.run(
        [sys.executable, str(work / "validation_runner.py"),
         "dotnet_nullable_odds_red", "--", "dotnet", "test",
         "dotnet/LineupWorker.Tests/LineupWorker.Tests.csproj", "--no-restore",
         "--filter", "FullyQualifiedName~RedisProtocolTests"],
        check=False,
    )
finally:
    target.write_bytes(patched)
raise SystemExit(result.returncode)
