"""Deny operational data and network other than the owned test endpoint."""

import os
import socket
import sys
import threading
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(os.environ["BRASILEIRAO_LAB_OUTPUT"]).resolve()
REPO = Path(os.environ["BRASILEIRAO_LAB_REPO"]).resolve()
sys.dont_write_bytecode = True
_internal = threading.local()
_socketpair = socket.socketpair


def local_pair(*args, **kwargs):
    _internal.pair = True
    try:
        return _socketpair(*args, **kwargs)
    finally:
        _internal.pair = False


socket.socketpair = local_pair


def path(value):
    return Path(os.fsdecode(value)).resolve() if isinstance(value, (str, bytes, os.PathLike)) else None


def guard(event, args):
    if event in {"socket.connect", "socket.bind"}:
        address = args[1]
        local = isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}
        if not (local and (getattr(_internal, "pair", False) or (event == "socket.connect" and address[1] == 26380))):
            raise PermissionError("lab_network_endpoint_forbidden")
    if event == "socket.getaddrinfo" and args[0] not in {"127.0.0.1", "::1"}:
        raise PermissionError("lab_dns_forbidden")
    if event.startswith(("subprocess.", "os.system", "os.exec", "os.spawn")):
        raise PermissionError("lab_python_subprocess_forbidden")
    if event == "sqlite3.connect":
        name = str(args[0])
        target = unquote(name[5:].split("?")[0]) if name.startswith("file:") else name
        if target != ":memory:" and not Path(target).resolve().is_relative_to(ROOT):
            raise PermissionError("lab_operational_database_forbidden")
    if event == "open":
        target = path(args[0])
        if target is None or str(target).lower() in {"nul", "\\\\.\\nul"}:
            return
        mode, flags = args[1] or "", args[2] or 0
        writing = any(c in mode for c in "wax+") or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
        if writing and not target.is_relative_to(ROOT):
            raise PermissionError("lab_write_outside_output")
        if not target.is_relative_to(ROOT) and (
            target.name == ".env"
            or target.is_relative_to(Path("C:/BRASILEIRAO/DADOS_PRESERVADOS"))
            or any(target.is_relative_to(REPO / d) for d in ("data", "research", "reports"))
        ):
            raise PermissionError("lab_protected_data_forbidden")
    if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.rename"}:
        for value in args[:2] if event == "os.rename" else args[:1]:
            target = path(value)
            if target is not None and not target.is_relative_to(ROOT):
                raise PermissionError("lab_mutation_outside_output")


sys.addaudithook(guard)
os.environ["BRASILEIRAO_LAB_GUARD_ACTIVE"] = "1"

if os.environ.get("BRASILEIRAO_LAB_DEBUG") == "1":

    def trace(frame, event, arg):
        if event == "exception" and frame.f_code.co_filename.endswith("hotpath_smoke.py"):
            print("LAB_EXCEPTION", frame.f_code.co_name, frame.f_lineno, arg[0].__name__, file=sys.stderr)
        return trace

    sys.settrace(trace)
