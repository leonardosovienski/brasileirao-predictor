"""Own one disposable Redis process and test the unmodified public sources."""

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import redis


def main():
    parser = argparse.ArgumentParser()
    for name in ("output", "repo", "server", "dotnet", "nuget-cache"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--server-sha256", required=True)
    parser.add_argument("--cross-only", action="store_true")
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        raise ValueError("native_runner_is_Windows_only_use_CI_for_Linux")
    out, repo, server = args.output.resolve(), args.repo.resolve(), args.server.resolve()
    base = Path("C:/BRASILEIRAO").resolve()
    if not out.is_relative_to(base / "work") or out == base / "work" or not server.is_relative_to(base / "work"):
        raise ValueError("isolated_paths_inside_work_required")
    if hashlib.sha256(server.read_bytes()).hexdigest() != args.server_sha256:
        raise ValueError("server_binary_hash_mismatch")
    # Fail before starting or communicating with any server at an occupied port.
    with socket.socket() as probe:
        if os.name == "nt":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        probe.bind(("127.0.0.1", 26380))
    out.mkdir(exist_ok=False)
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper()
        in {
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "PATHEXT",
            "PROCESSOR_ARCHITECTURE",
            "NUMBER_OF_PROCESSORS",
            "PROGRAMFILES",
            "PROGRAMFILES(X86)",
            "PROGRAMW6432",
            "SYSTEMDRIVE",
        }
    }
    env["PATH"] = str(args.dotnet.resolve().parent) + os.pathsep + str(Path(env["SYSTEMROOT"]) / "System32")
    for key, folder in {
        "TEMP": "tmp",
        "TMP": "tmp",
        "USERPROFILE": "profile",
        "APPDATA": "appdata",
        "LOCALAPPDATA": "localappdata",
        "DOTNET_CLI_HOME": "dotnet-home",
        "NUGET_HTTP_CACHE_PATH": "nuget-http",
        "NUMBA_CACHE_DIR": "numba",
    }.items():
        (out / folder).mkdir(exist_ok=True)
        env[key] = str(out / folder)
    env.update(
        DOTNET_ROOT=str(args.dotnet.resolve().parent),
        NUGET_PACKAGES=str(args.nuget_cache.resolve()),
        DOTNET_CLI_TELEMETRY_OPTOUT="1",
        DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1",
        DOTNET_GENERATE_ASPNET_CERTIFICATE="false",
        DOTNET_NOLOGO="1",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1",
        BRASILEIRAO_LAB_OUTPUT=str(out),
        BRASILEIRAO_LAB_REPO=str(repo),
        PYTHONPATH=os.pathsep.join([str(Path(__file__).resolve().parent), str(repo)]),
        OMP_NUM_THREADS="2",
        OPENBLAS_NUM_THREADS="2",
        MKL_NUM_THREADS="2",
    )
    copy = out / "source"
    copy.mkdir()
    for name in ("dotnet", "contracts"):
        shutil.copytree(repo / name, copy / name, ignore=shutil.ignore_patterns("bin", "obj"))
    for name in ("global.json", "NuGet.Config"):
        if (repo / name).is_file():
            shutil.copyfile(repo / name, copy / name)
    receipt = {
        "server_path": str(server),
        "server_sha256": args.server_sha256,
        "runtime_scope": "disposable_community_Windows_build_not_production_homologation",
        "commands": [],
    }
    native = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    def command(argv, name, timeout):
        if process.poll() is not None or client.info("server")["run_id"] != receipt["run_id"]:
            raise RuntimeError("owned_redis_lost")
        with (out / (name + ".log")).open("wb") as log:
            child = subprocess.Popen(
                argv, cwd=copy, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=native
            )
            try:
                code = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                subprocess.run(
                    ["taskkill.exe", "/PID", str(child.pid), "/T", "/F"],
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=native,
                    check=False,
                )
                child.wait(timeout=15)
                code = 124
        receipt["commands"].append({"name": name, "argv": [str(x) for x in argv], "exit_code": code})
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(name, code, flush=True)
        return code

    with (out / "redis.log").open("wb") as log:
        process = subprocess.Popen(
            [
                str(server),
                "--bind",
                "127.0.0.1",
                "--port",
                "26380",
                "--maxclients",
                "128",
                "--protected-mode",
                "yes",
                "--save",
                "",
                "--appendonly",
                "no",
                "--dir",
                ".",
                "--daemonize",
                "no",
            ],
            cwd=out,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=native,
        )
        client = redis.Redis(host="127.0.0.1", port=26380, socket_timeout=2, socket_connect_timeout=2)
        receipt["pid"] = process.pid
        try:
            for _ in range(50):
                if process.poll() is not None:
                    raise RuntimeError("owned_server_exited")
                # Check Windows owner before the first connection, including a port race.
                netstat = subprocess.run(
                    ["netstat.exe", "-ano", "-p", "TCP"],
                    capture_output=True,
                    text=True,
                    env=env,
                    creationflags=native,
                    check=True,
                ).stdout
                rows = [
                    line.split() for line in netstat.splitlines() if "127.0.0.1:26380 " in line and "LISTENING" in line
                ]
                if rows:
                    if len(rows) != 1 or int(rows[0][-1]) != process.pid:
                        raise RuntimeError("endpoint_owned_by_another_process")
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("owned_server_did_not_listen")
            info = client.info("server")
            receipt.update(
                run_id=info["run_id"], redis_version=info["redis_version"], redis_process_id=info["process_id"]
            )
            env.update(LINEUP_TEST_REDIS_URL="redis://127.0.0.1:26380/14", LINEUP_TEST_REDIS_RUN_ID=info["run_id"])
            import sys

            if not args.cross_only:
                command([sys.executable, str(Path(__file__).with_name("python_tests.py"))], "python-integration", 240)
            if args.diagnostics:
                env["BRASILEIRAO_LAB_DEBUG"] = "1"
            env.update(
                LINEUP_TEST_REDIS_URL="redis://127.0.0.1:26380/15",
                LINEUP_E2E_REDIS_URL="redis://127.0.0.1:26380/13",
                LINEUP_E2E_REDIS_RUN_ID=info["run_id"],
                LINEUP_E2E_PYTHON=sys.executable,
                LINEUP_E2E_KERNEL_SCRIPT=str(Path(__file__).with_name("kernel_synthetic.py")),
            )
            project = "dotnet/LineupWorker.Tests/LineupWorker.Tests.csproj"
            if command([str(args.dotnet), "restore", project, "--locked-mode"], "dotnet-restore", 180) == 0:
                if (
                    command(
                        [str(args.dotnet), "build", project, "-c", "Release", "--no-restore", "--warnaserror"],
                        "dotnet-build",
                        180,
                    )
                    == 0
                ):
                    command(
                        [
                            str(args.dotnet),
                            "test",
                            project,
                            "-c",
                            "Release",
                            "--no-restore",
                            "--no-build",
                            "--logger",
                            "trx",
                            "--collect:XPlat Code Coverage",
                            "--results-directory",
                            str(out / "dotnet-results"),
                        ]
                        + (["--filter", "FullyQualifiedName~KernelCrossProcessTests"] if args.cross_only else []),
                        "dotnet-test",
                        240,
                    )
        finally:
            if process.poll() is None:
                # Terminate only our process; never SHUTDOWN an unverified endpoint.
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            client.close()
            receipt["server_stopped"] = process.poll() is not None
            (out / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return (
        0
        if len(receipt["commands"]) == (3 if args.cross_only else 4)
        and all(c["exit_code"] == 0 for c in receipt["commands"])
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
