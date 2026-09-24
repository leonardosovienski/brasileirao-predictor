"""Atomic writes and hashing shared by the research circuit (no silent repair)."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class Busy(RuntimeError):
    """Another live process holds the lock (released automatically if that process dies)."""


@contextmanager
def exclusive(path: Path) -> Iterator[None]:
    """Non-blocking exclusive OS lock on a persistent file; the OS releases it on process death."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise Busy(str(path.name)) from exc
        try:
            yield
        finally:
            handle.seek(0)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write(path: Path, content: bytes) -> None:
    """Write-then-rename in the same directory, fsync before the rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    """Strict JSON object: duplicate keys and NaN/Infinity are errors, never tolerated."""

    def pairs(items):
        out = {}
        for key, val in items:
            if key in out:
                raise ValueError(f"duplicate JSON key {key!r} in {Path(path).name}")
            out[key] = val
        return out

    def constant(name):
        raise ValueError(f"non-finite JSON constant {name} in {Path(path).name}")

    value = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {Path(path).name}")
    return value


__all__ = ["Busy", "atomic_write", "exclusive", "read_json_object", "sha256_file"]
