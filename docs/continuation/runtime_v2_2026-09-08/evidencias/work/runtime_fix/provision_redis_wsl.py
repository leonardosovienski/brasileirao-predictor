"""Provision only a newly named disposable WSL environment for Redis tests."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import tarfile
import time
import urllib.request

BASE = Path(__file__).resolve().parent / "redis_env_review_runtime"
LOGS = BASE / "receipts"
DISTRO = "codex-brasileirao-redis-20260908"
ALPINE = "https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86_64/alpine-minirootfs-3.22.5-x86_64.tar.gz"
REDIS = "https://download.redis.io/releases/redis-8.2.1.tar.gz"
REDIS_HASHES = "https://raw.githubusercontent.com/redis/redis-hashes/master/README"
ALLOW = {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS", "OS", "HOMEDRIVE", "HOMEPATH"}
ENV = {key: value for key, value in os.environ.items() if key.upper() in ALLOW}
ENV.update({"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"})
PORT = 26380


def write(name, value):
    BASE.mkdir(parents=True, exist_ok=True)
    with (BASE / name).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def decode(raw):
    return raw.decode("utf-16-le" if b"\x00" in raw[:200] else "utf-8", errors="replace").lstrip("\ufeff")


def run(name, command, timeout=45, input_bytes=None):
    LOGS.mkdir(parents=True, exist_ok=True)
    receipt = {"started_at_utc": datetime.now(UTC).isoformat(), "command": command, "environment_allowlist": True,
               "distro": DISTRO if DISTRO in command else None, "existing_services_modified": False}
    started = time.monotonic()
    try:
        completed = subprocess.run(command, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   timeout=timeout, env=ENV, creationflags=subprocess.CREATE_NO_WINDOW)
        output = decode(completed.stdout)
        receipt["exit_code"] = completed.returncode
    except subprocess.TimeoutExpired as exc:
        output = decode(exc.stdout or b"")
        receipt.update({"exit_code": 124, "timeout": True})
    receipt["seconds"] = time.monotonic() - started
    if input_bytes is not None:
        receipt["stdin_sha256"] = hashlib.sha256(input_bytes).hexdigest()
    with (LOGS / f"{name}.log").open("x", encoding="utf-8") as handle:
        handle.write(output)
    with (LOGS / f"{name}.json").open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
    print(json.dumps(receipt), flush=True)
    print(output[-3000:], flush=True)
    return receipt["exit_code"], output


def download(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=40) as response:
        return response.read()


def inventory():
    for name, args in (("docker_version", ["docker.exe", "version", "--format", "json"]),
                       ("wsl_list", ["wsl.exe", "--list", "--verbose"]),
                       ("wsl_status", ["wsl.exe", "--status"]),
                       ("dotnet_sdks", ["dotnet.exe", "--list-sdks"])):
        run(name, args)


def prepare():
    code, listed = run("wsl_before_import", ["wsl.exe", "--list", "--quiet"])
    if code or DISTRO in listed.splitlines():
        raise RuntimeError("new distro name unavailable; existing instances will not be touched")
    expected_file = download(ALPINE + ".sha256")
    expected = expected_file.decode("ascii").split()[0]
    raw = download(ALPINE)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise RuntimeError("official Alpine checksum mismatch")
    rootfs = BASE / "alpine-minirootfs-3.22.5-x86_64.tar.gz"
    with rootfs.open("xb") as handle:
        handle.write(raw)
    write("source_downloads.json", {"rootfs_url": ALPINE, "checksum_url": ALPINE + ".sha256",
                                   "sha256": actual, "bytes": len(raw), "verified_official_checksum": True})
    # Append a config only to this new tar; host drives and Windows interop are disabled.
    configured = BASE / "alpine-isolated.tar"
    with configured.open("xb") as handle:
        handle.write(gzip.decompress(raw))
    settings = b"[automount]\nenabled=false\n[interop]\nenabled=false\nappendWindowsPath=false\n"
    with tarfile.open(configured, "a") as archive:
        entry = tarfile.TarInfo("etc/wsl.conf")
        entry.size, entry.mode = len(settings), 0o644
        archive.addfile(entry, io.BytesIO(settings))
    installation = BASE / "distro"
    installation.mkdir(exist_ok=False)
    write("creation_intent.json", {"distro": DISTRO, "installation": str(installation.resolve()),
                                  "source_sha256": actual, "configured_tar_sha256": hashlib.sha256(configured.read_bytes()).hexdigest(),
                                  "host_drive_automount": False, "windows_interop": False,
                                  "cleanup_only_this_created_distro": True})
    code, _ = run("wsl_import", ["wsl.exe", "--import", DISTRO, str(installation), str(configured), "--version", "2"], timeout=55)
    if code:
        raise RuntimeError("WSL import failed; inspect receipt before further actions")
    write("created.json", {"distro": DISTRO, "installation": str(installation.resolve()), "created_at_utc": datetime.now(UTC).isoformat()})
    code, _ = run("wsl_boot", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/sh", "-c", "uname -a; cat /etc/alpine-release; cat /etc/wsl.conf; test ! -d /mnt/c/Users"], timeout=45)
    if code:
        raise RuntimeError("isolated WSL boot failed")


def build():
    created = json.loads((BASE / "created.json").read_text(encoding="utf-8"))
    if created["distro"] != DISTRO:
        raise RuntimeError("ownership mismatch")
    hashes = download(REDIS_HASHES).decode("utf-8")
    candidates = [line.split() for line in hashes.splitlines() if "redis-8.2.1.tar.gz" in line and "sha256" in line]
    if len(candidates) != 1:
        raise RuntimeError("official Redis checksum missing or ambiguous")
    expected = next(part for part in candidates[0] if len(part) == 64 and all(c in "0123456789abcdef" for c in part))
    raw = download(REDIS)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError("official Redis checksum mismatch")
    with (BASE / "redis-8.2.1.tar.gz").open("xb") as handle:
        handle.write(raw)
    write("redis_source.json", {"url": REDIS, "checksum_url": REDIS_HASHES, "sha256": expected, "bytes": len(raw)})
    code, _ = run("build_dependencies", ["wsl.exe", "-d", DISTRO, "--exec", "/sbin/apk", "add", "--no-cache", "build-base", "linux-headers"], timeout=180)
    if code:
        raise RuntimeError("isolated build dependencies failed")
    code, _ = run("source_extract", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/tar", "-xz", "-C", "/opt"], timeout=45, input_bytes=raw)
    if code:
        raise RuntimeError("source extraction failed")
    code, _ = run("redis_build", ["wsl.exe", "-d", DISTRO, "--exec", "/usr/bin/make", "-C", "/opt/redis-8.2.1", "-j2", "MALLOC=libc", "BUILD_TLS=no"], timeout=480)
    if code:
        raise RuntimeError("Redis source build failed")
    run("redis_version", ["wsl.exe", "-d", DISTRO, "--exec", "/opt/redis-8.2.1/src/redis-server", "--version"])


def prepare_wsl1():
    code, listed = run("wsl_before_wsl1_import", ["wsl.exe", "--list", "--quiet"])
    if code or DISTRO in listed.splitlines():
        raise RuntimeError("new distro name unavailable; existing instances will not be touched")
    installation = BASE / "distro-wsl1"
    installation.mkdir(exist_ok=False)
    configured = BASE / "alpine-isolated.tar"
    write("creation_intent_wsl1.json", {"distro": DISTRO, "installation": str(installation.resolve()),
                                      "wsl_version": 1, "configured_tar_sha256": hashlib.sha256(configured.read_bytes()).hexdigest(),
                                      "host_drive_automount": False, "windows_interop": False,
                                      "cleanup_only_this_created_distro": True})
    code, _ = run("wsl1_import", ["wsl.exe", "--import", DISTRO, str(installation), str(configured), "--version", "1"], timeout=55)
    if code:
        raise RuntimeError("WSL1 import failed; no global feature will be enabled")
    write("created.json", {"distro": DISTRO, "installation": str(installation.resolve()), "wsl_version": 1,
                           "created_at_utc": datetime.now(UTC).isoformat()})
    code, _ = run("wsl1_boot", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/sh", "-c", "uname -a; cat /etc/alpine-release; cat /etc/wsl.conf; test ! -d /mnt/c/Users"], timeout=45)
    if code:
        raise RuntimeError("isolated WSL1 boot failed")


def build_official_github():
    created = json.loads((BASE / "created.json").read_text(encoding="utf-8"))
    if created["distro"] != DISTRO:
        raise RuntimeError("ownership mismatch")
    commit = "cd0b12938b6c99978440c6f7e44e34d7ff0aa537"
    url = f"https://codeload.github.com/redis/redis/tar.gz/{commit}"
    raw = download(url)
    tagged = (BASE / "redis-github-8.2.1.tar.gz").read_bytes()
    def tree(blob):
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
            return {member.name.split("/", 1)[1]: hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                    for member in archive if member.isfile()}
    if tree(raw) != tree(tagged):
        raise RuntimeError("official tag and pinned release commit have different contents")
    with (BASE / "redis-8.2.1-commit.tar.gz").open("xb") as handle:
        handle.write(raw)
    write("redis_source_github.json", {"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                                      "release": "8.2.1", "commit": commit,
                                      "official_release_url": "https://github.com/redis/redis/releases/tag/8.2.1",
                                      "tag_archive_sha256": hashlib.sha256(tagged).hexdigest(), "tag_tree_equals_commit_tree": True,
                                      "distribution_tarball_download": "HTTP 403; not used"})
    code, _ = run("build_dependencies", ["wsl.exe", "-d", DISTRO, "--exec", "/sbin/apk", "add", "--no-cache", "build-base", "linux-headers"], timeout=180)
    if code:
        raise RuntimeError("isolated build dependencies failed")
    code, _ = run("source_extract", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/tar", "-xz", "-C", "/opt"], timeout=45, input_bytes=tagged)
    if code:
        raise RuntimeError("source extraction failed")
    code, _ = run("redis_build", ["wsl.exe", "-d", DISTRO, "--exec", "/usr/bin/make", "-C", "/opt/redis-8.2.1", "-j2", "MALLOC=libc", "BUILD_TLS=no"], timeout=480)
    if code:
        raise RuntimeError("Redis source build failed")
    run("redis_version", ["wsl.exe", "-d", DISTRO, "--exec", "/opt/redis-8.2.1/src/redis-server", "--version"])


def redis_commands(*commands):
    def read_resp(stream):
        line = stream.readline()
        if not line:
            return None
        kind, value = line[:1], line[1:-2]
        if kind == b"-":
            raise RuntimeError(value.decode())
        if kind == b"+":
            return value.decode()
        if kind == b":":
            return int(value)
        if kind == b"$":
            count = int(value)
            if count == -1:
                return None
            result = stream.read(count)
            if stream.read(2) != b"\r\n":
                raise RuntimeError("invalid RESP terminator")
            return result.decode()
        if kind == b"*":
            return [read_resp(stream) for _ in range(int(value))]
        raise RuntimeError("unknown RESP reply")
    results = []
    with socket.create_connection(("127.0.0.1", PORT), timeout=3) as connection:
        stream = connection.makefile("rb")
        for command in commands:
            parts = [str(part).encode() for part in command]
            packet = f"*{len(parts)}\r\n".encode() + b"".join(f"${len(part)}\r\n".encode() + part + b"\r\n" for part in parts)
            connection.sendall(packet)
            results.append(read_resp(stream))
    return results


def server_info():
    ping, info = redis_commands(("PING",), ("INFO", "server"))
    if ping != "PONG":
        raise RuntimeError("Redis PING failed")
    return dict(line.split(":", 1) for line in info.splitlines() if ":" in line and not line.startswith("#"))


def start(resume_config=False):
    created = json.loads((BASE / "created.json").read_text(encoding="utf-8"))
    if created["distro"] != DISTRO:
        raise RuntimeError("ownership mismatch")
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        probe.bind(("127.0.0.1", PORT))
    if resume_config:
        intent = json.loads((BASE / "start_intent.json").read_text(encoding="utf-8"))
        if intent["distro"] != DISTRO or intent["port"] != PORT:
            raise RuntimeError("resume ownership mismatch")
        code, _ = run("redis_config_absent_retry", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/busybox", "test", "!", "-e", "/opt/redis-test/redis.conf"])
        if code:
            raise RuntimeError("configuration already exists")
    else:
        write("start_intent.json", {"port": PORT, "exclusive_windows_bind_succeeded": True,
                                   "bind": "127.0.0.1", "databases": 16, "persistence": False,
                                   "distro": DISTRO, "directory": "/opt/redis-test"})
        code, _ = run("redis_directory", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/mkdir", "/opt/redis-test"])
        if code:
            raise RuntimeError("refusing existing Redis directory")
    config = (f"bind 127.0.0.1\nport {PORT}\nprotected-mode yes\ndaemonize yes\n"
              "pidfile /opt/redis-test/redis.pid\nlogfile /opt/redis-test/redis.log\n"
              "dir /opt/redis-test\ndatabases 16\nsave \"\"\nappendonly no\n"
              "maxmemory 128mb\nmaxmemory-policy noeviction\n").encode()
    code, _ = run("redis_config_retry" if resume_config else "redis_config", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/busybox", "tee", "/opt/redis-test/redis.conf"], input_bytes=config)
    if code:
        raise RuntimeError("Redis configuration write failed")
    code, _ = run("redis_start", ["wsl.exe", "-d", DISTRO, "--exec", "/opt/redis-8.2.1/src/redis-server", "/opt/redis-test/redis.conf"])
    if code:
        raise RuntimeError("new Redis process failed to start")
    code, pid = run("redis_pid", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/cat", "/opt/redis-test/redis.pid"])
    if code:
        raise RuntimeError("Redis PID missing")
    info = server_info()
    if info["process_id"] != pid.strip() or info["redis_version"] != "8.2.1":
        raise RuntimeError("Windows endpoint does not match newly started Redis")
    config_read = redis_commands(("CONFIG", "GET", "dir", "bind", "port", "databases", "save", "appendonly"))[0]
    settings = dict(zip(config_read[::2], config_read[1::2]))
    if settings != {"dir": "/opt/redis-test", "bind": "127.0.0.1", "port": str(PORT), "databases": "16", "save": "", "appendonly": "no"}:
        raise RuntimeError("Redis settings mismatch")
    empty = redis_commands(("SELECT", 14), ("DBSIZE",), ("SELECT", 15), ("DBSIZE",))
    if empty != ["OK", 0, "OK", 0]:
        raise RuntimeError("new test databases are not empty")
    receipt = {"ready_at_utc": datetime.now(UTC).isoformat(), "distro": DISTRO,
               "redis_version": info["redis_version"], "run_id": info["run_id"], "process_id": info["process_id"],
               "python_url": f"redis://127.0.0.1:{PORT}/14", "dotnet_url": f"redis://127.0.0.1:{PORT}/15",
               "verified_from_windows": True, "config": settings, "db14_initial_size": 0, "db15_initial_size": 0,
               "ownership": "new instance; not an existing endpoint"}
    write("ready.json", receipt)
    print(json.dumps(receipt), flush=True)


def cleanup():
    created = json.loads((BASE / "created.json").read_text(encoding="utf-8"))
    ready = json.loads((BASE / "ready.json").read_text(encoding="utf-8"))
    installation = Path(created["installation"]).resolve()
    if created["distro"] != DISTRO or ready["distro"] != DISTRO or not installation.is_relative_to(BASE.resolve()):
        raise RuntimeError("cleanup ownership or installation boundary mismatch")
    info = server_info()
    if info["run_id"] != ready["run_id"] or info["process_id"] != ready["process_id"]:
        raise RuntimeError("refusing to stop a different Redis process")
    code, recorded_pid = run("redis_pid_before_cleanup", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/cat", "/opt/redis-test/redis.pid"])
    if code or recorded_pid.strip() != info["process_id"]:
        raise RuntimeError("owned distro PID does not match Windows endpoint")
    database_sizes = {str(database): redis_commands(("SELECT", database), ("DBSIZE",))[1]
                      for database in (12, 13, 14, 15)}
    write("cleanup_intent.json", {"at_utc": datetime.now(UTC).isoformat(), "distro": DISTRO,
                                 "verified_installation": str(installation), "run_id": info["run_id"],
                                 "verified_process_id": info["process_id"], "synthetic_database_sizes": database_sizes,
                                 "other_distributions_or_services_touched": False})
    run("redis_log_before_cleanup", ["wsl.exe", "-d", DISTRO, "--exec", "/bin/cat", "/opt/redis-test/redis.log"])
    try:
        reply = redis_commands(("SHUTDOWN", "NOSAVE"))
        shutdown_status = {"connection_closed_after_shutdown": reply == [None], "reply": reply}
    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, EOFError) as exc:
        shutdown_status = {"connection_closed_after_shutdown": True, "closure_exception": type(exc).__name__}
    write("shutdown.json", shutdown_status | {"run_id_verified_before_shutdown": info["run_id"], "command": "SHUTDOWN NOSAVE"})
    code, _ = run("own_wsl_terminate", ["wsl.exe", "--terminate", DISTRO])
    if code:
        raise RuntimeError("own distro terminate failed; inspect receipt")
    code, _ = run("own_wsl_unregister", ["wsl.exe", "--unregister", DISTRO], timeout=55)
    if code:
        raise RuntimeError("own distro unregister failed; inspect receipt")
    code, listed = run("wsl_after_cleanup", ["wsl.exe", "--list", "--verbose"])
    if code or DISTRO in listed:
        raise RuntimeError("own distro remains registered")
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(("127.0.0.1", PORT)) == 0:
            raise RuntimeError("the test port still accepts connections after owned distro removal")
    write("cleaned.json", {"at_utc": datetime.now(UTC).isoformat(), "distro_removed": DISTRO,
                          "port_no_longer_accepts_connections": PORT, "source_archives_and_receipts_preserved": True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inventory", "prepare", "prepare-wsl1", "build", "build-github", "start", "resume-config", "cleanup"))
    args = parser.parse_args()
    {"inventory": inventory, "prepare": prepare, "prepare-wsl1": prepare_wsl1, "build": build, "build-github": build_official_github, "start": start, "resume-config": lambda: start(True), "cleanup": cleanup}[args.action]()


if __name__ == "__main__":
    main()
