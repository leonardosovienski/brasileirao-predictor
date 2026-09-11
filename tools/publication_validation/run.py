"""Run an explicit test allowlist without credentials, network or operational data."""

import json
import os
import socket
import sys
import threading
from pathlib import Path
from typing import Never
from urllib.parse import urlsplit
from urllib.request import url2pathname

REPO = Path(__file__).resolve().parents[2]


def main():
    out = Path(sys.argv[1]).resolve()
    if out == REPO or REPO.is_relative_to(out) or out.is_relative_to(REPO):
        raise ValueError("new_output_outside_checkout_required")
    out.mkdir(exist_ok=False)
    manifest = json.loads(Path(__file__).with_name("scope.json").read_text(encoding="utf-8"))
    tests = manifest["tests"]
    if (
        len(sys.argv) != 2
        or not tests
        or any(".." in item or Path(item.split("::")[0]).is_absolute() for item in tests)
    ):
        raise ValueError("reviewed_test_allowlist_required")
    for k in list(os.environ):
        if k.upper() not in {"SYSTEMROOT", "WINDIR", "PATH", "COMSPEC", "PATHEXT"}:
            del os.environ[k]
    os.environ.update(
        HOME=str(out),
        USERPROFILE=str(out),
        TMPDIR=str(out),
        TEMP=str(out),
        TMP=str(out),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        NUMBA_CACHE_DIR=str(out / "numba"),
        OMP_NUM_THREADS="2",
        OPENBLAS_NUM_THREADS="2",
        MKL_NUM_THREADS="2",
    )
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))
    os.chdir(out)
    blocked = []
    internal = threading.local()
    native_socketpair = socket.socketpair

    def local_socketpair(*args, **kwargs):
        internal.socketpair = True
        try:
            return native_socketpair(*args, **kwargs)
        finally:
            internal.socketpair = False

    socket.socketpair = local_socketpair
    allowed_public = {}

    def location(value):
        return Path(os.fsdecode(value)).resolve() if isinstance(value, str | bytes | os.PathLike) else None

    def deny(event, reason) -> Never:
        blocked.append({"event": event, "reason": reason})
        raise PermissionError(reason)

    def guard(event, args):
        if event.startswith(
            ("socket.connect", "socket.bind", "socket.getaddrinfo", "subprocess.", "os.system", "os.exec", "os.spawn")
        ):
            # CPython on Windows implements socketpair using an ephemeral
            # loopback listener. Only that trusted stdlib call may do so.
            local_pair = (
                getattr(internal, "socketpair", False)
                and event in {"socket.connect", "socket.bind"}
                and isinstance(args[1], tuple)
                and args[1][0] in {"127.0.0.1", "::1"}
            )
            if not local_pair:
                deny(event, "network_or_subprocess_forbidden")
        if event == "sqlite3.connect":
            db = str(args[0])
            if db.startswith("file:"):
                parsed = urlsplit(db)
                if parsed.netloc not in {"", "localhost"}:
                    deny(event, "remote_sqlite_uri_forbidden")
                target = url2pathname(parsed.path)
            else:
                target = db
            if target != ":memory:" and not Path(target).resolve().is_relative_to(out):
                deny(event, "only_synthetic_sqlite_inside_test_output")
        if event == "open":
            p = location(args[0])
            if p is None or p == Path(os.devnull).resolve():
                return
            mode, flags = args[1] or "", args[2] or 0
            writing = any(c in mode for c in "wax+") or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
            if writing and not p.is_relative_to(out):
                deny(event, "write_outside_test_output")
            if (
                p not in allowed_public
                and not p.is_relative_to(out)
                and (
                    p == REPO / "config.yaml"
                    or p.name == ".env"
                    or p.is_relative_to(Path("C:/BRASILEIRAO/DADOS_PRESERVADOS"))
                    or any(p.is_relative_to(REPO / d) for d in ("data", "reports", "research"))
                )
            ):
                deny(event, "private_or_protected_data_forbidden")
            if p.name.startswith(("evaluate_h14", "evaluate_h15", "evaluate_gate_a1", "settle_h9")):
                deny(event, "protected_evaluator_not_authorized")
        if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.rename"}:
            for value in args[:2] if event == "os.rename" else args[:1]:
                p = location(value)
                if p is not None and not p.is_relative_to(out):
                    deny(event, "mutation_outside_test_output")

    sys.addaudithook(guard)
    # The C-based HTTP client can bypass Python socket audit events.
    # Its tests may replace this with synthetic transport, never real network.
    import curl_cffi.requests

    def blocked_native_http(*args, **kwargs) -> Never:
        deny("curl_cffi.request", "native_network_forbidden")

    curl_cffi.requests.Session.request = blocked_native_http
    curl_cffi.requests.AsyncSession.request = blocked_native_http
    import pytest

    rc = pytest.main(
        [str(REPO / t) for t in tests]
        + [
            "-q",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(out / "tmp"),
            "--junitxml",
            str(out / "junit.xml"),
            "--tb=short",
        ]
    )
    (out / "isolation.json").write_text(
        json.dumps({"tests": tests, "blocked_attempts": blocked, "exit_code": rc}, indent=2), encoding="utf-8"
    )
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
