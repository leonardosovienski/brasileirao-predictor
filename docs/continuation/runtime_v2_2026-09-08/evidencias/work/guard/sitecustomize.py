"""Contain Python checks: no live files outside dependencies, no external sockets."""
import os
from pathlib import Path
import sys

LIVE = Path("C:/Users/Superleo13/projetos/brasileirao-predictor").resolve()


def protected(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        return False
    value = Path(os.fsdecode(path)).resolve()
    return value.is_relative_to(LIVE) and not value.is_relative_to(LIVE / ".venv")


def audit(event, args):
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
            raise PermissionError("External network disabled for isolated validation")
    elif event == "open" and protected(args[0]):
        raise PermissionError("Validation cannot access the operational checkout")
    elif event in ("os.remove", "os.rmdir", "os.mkdir") and protected(args[0]):
        raise PermissionError("Validation cannot mutate the operational checkout")
    elif event in ("os.rename", "os.replace") and any(protected(p) for p in args[:2]):
        raise PermissionError("Validation cannot move operational checkout files")


sys.addaudithook(audit)
