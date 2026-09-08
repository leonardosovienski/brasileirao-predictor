"""Read-only local-engine probes with separate immutable receipts."""
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).resolve().parent / "environment_review"
ALLOWED = {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS", "OS", "HOMEDRIVE", "HOMEPATH"}
ENV = {key: value for key, value in os.environ.items() if key.upper() in ALLOWED}


def decode(raw):
    return raw.decode("utf-16-le" if b"\0" in raw[:200] else "utf-8", errors="replace").lstrip("\ufeff")


def run(name, command, timeout=30, read_only=True):
    BASE.mkdir(exist_ok=True)
    if (BASE / (name + ".json")).exists() or (BASE / (name + ".log")).exists():
        raise FileExistsError("immutable receipt already exists: " + name)
    started = time.monotonic()
    receipt = {"started_at_utc": datetime.now(UTC).isoformat(), "command": command, "environment_allowlist": True,
               "read_only": read_only, "external_credentials_removed": True}
    try:
        result = subprocess.run(command, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        output, receipt["exit_code"] = decode(result.stdout), result.returncode
    except subprocess.TimeoutExpired as exc:
        output, receipt["exit_code"] = decode(exc.stdout or b""), 124
        receipt["timeout"] = True
    receipt["seconds"] = time.monotonic() - started
    with (BASE / (name + ".log")).open("x", encoding="utf-8") as handle:
        handle.write(output)
    with (BASE / (name + ".json")).open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
    print(json.dumps(receipt), flush=True)
    print(output[-6000:], flush=True)
    return receipt["exit_code"], output


def main():
    ps = lambda command: ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command]
    commands = [
        ("initial_docker_version", ["docker.exe", "-H", "npipe:////./pipe/docker_engine", "version", "--format", "json"]),
        ("initial_docker_contexts", ["docker.exe", "context", "ls", "--format", "json"]),
        ("initial_wsl_distros", ["wsl.exe", "--list", "--verbose"]),
        ("initial_wsl_status", ["wsl.exe", "--status"]),
        ("initial_hypervisor", ps("Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent | ConvertTo-Json -Compress")),
        ("initial_cpu_virtualization", ps("Get-CimInstance Win32_Processor | Select-Object VirtualizationFirmwareEnabled,SecondLevelAddressTranslationExtensions,VMMonitorModeExtensions | ConvertTo-Json -Compress")),
        ("initial_optional_features", ps("Get-CimInstance Win32_OptionalFeature -Filter \"Name='VirtualMachinePlatform' OR Name='Microsoft-Windows-Subsystem-Linux' OR Name='Microsoft-Hyper-V-All'\" | Select-Object Name,InstallState | ConvertTo-Json -Compress")),
        ("initial_services", ps("Get-Service -Name com.docker.service,LxssManager,vmcompute -ErrorAction SilentlyContinue | Select-Object Name,Status,StartType | ConvertTo-Json -Compress")),
        ("initial_docker_processes", ps("Get-Process -Name 'Docker Desktop','com.docker.backend','com.docker.build' -ErrorAction SilentlyContinue | Select-Object ProcessName,Id | ConvertTo-Json -Compress")),
    ]
    for name, command in commands:
        run(name, command)


if __name__ == "__main__":
    main()
