"""Strict explicit-file I/O and receipts for isolated offline research runs."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = "price-strength-artifacts/v1"
_RESERVED_NAMES = {"manifest.json", "failure.json"}


def _input_path(path: Path) -> Path:
    resolved = Path(path).resolve()
    if resolved.is_relative_to((REPOSITORY_ROOT / "data").resolve()):
        raise ValueError("offline research inputs cannot be inside repository data")
    if not resolved.is_file():
        raise ValueError("input must be an explicit existing file")
    return resolved


def _output_path(path: Path) -> Path:
    resolved = Path(path).resolve()
    root = REPOSITORY_ROOT.resolve()
    if resolved == root or resolved.is_relative_to((root / "data").resolve()):
        raise ValueError("output cannot be the repository root or inside repository data")
    if any(part.casefold() == ".git" for part in resolved.parts):
        raise ValueError("output cannot be inside Git metadata")
    if resolved.exists() or Path(path).is_symlink():
        raise FileExistsError("output directory must not already exist")
    return resolved


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise ValueError("non-finite JSON number is not allowed")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON number is not allowed")
    return parsed


def _decode(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_reject_constant, parse_float=_finite_float)


def read_json(path: Path) -> dict:
    """Read one explicit UTF-8 JSON object without coercion or nonstandard JSON."""
    return cast(dict, read_hashed(path, jsonl=False)[0])


def read_jsonl(path: Path) -> list[dict]:
    """Read explicit JSONL; every line, including blank lines, must be an object."""
    return cast(list[dict], read_hashed(path, jsonl=True)[0])


def read_hashed(path: Path, *, jsonl: bool) -> tuple[dict | list[dict], str]:
    """Parse and hash the same bytes from one guarded read of an explicit file."""
    content = _input_path(path).read_bytes()
    text = content.decode("utf-8", errors="strict")
    fingerprint = hashlib.sha256(content).hexdigest()
    if not jsonl:
        value = _decode(text)
        if not isinstance(value, dict):
            raise ValueError("JSON input must be an object")
        return value, fingerprint
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()  # A final newline is not an additional JSONL record.
    rows: list[dict] = []
    for number, line in enumerate(lines, start=1):
        try:
            value = _decode(line)
            if not isinstance(value, dict):
                raise ValueError("JSONL rows must be objects")
        except ValueError as exc:
            raise ValueError(f"invalid JSONL object at line {number}: {exc}") from None
        rows.append(value)
    return rows, fingerprint


def _validate_keys(value: Any) -> None:
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        for child in value.values():
            _validate_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_keys(child)


def _json_bytes(value: Any) -> bytes:
    _validate_keys(value)
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _artifact_bytes(name: str, value: object) -> bytes:
    if (
        not isinstance(name, str)
        or not name
        or any(character in name for character in "/\\:")
        or name != Path(name).name
        or Path(name).suffix not in {".json", ".jsonl"}
        or name.casefold() in _RESERVED_NAMES
    ):
        raise ValueError("artifact name must be a simple, non-reserved .json or .jsonl filename")
    if name.endswith(".jsonl"):
        if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
            raise ValueError("JSONL artifacts must be lists of objects")
        _validate_keys(value)
        return "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
            for row in value
        ).encode("utf-8")
    return _json_bytes(value)


def _digest(content: bytes) -> dict[str, str | int]:
    return {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def _source_hashes() -> dict[str, dict[str, str | int]]:
    package = PACKAGE_ROOT.resolve()
    sources: dict[str, dict[str, str | int]] = {}
    for path in sorted(package.rglob("*.py")):
        resolved = path.resolve()
        if not resolved.is_relative_to(package):
            raise ValueError("research source cannot resolve outside its package")
        resolved = _input_path(resolved)
        sources[path.relative_to(package).as_posix()] = _digest(resolved.read_bytes())
    return sources


def write_artifacts(output_dir: Path, *, inputs: dict[str, Path], artifacts: dict[str, object], metadata: dict) -> dict:
    """Create a new run directory; publish COMPLETE only after all writes succeed.

    Pass read_hashed() fingerprints as metadata["input_hashes_used"] to reject
    input changes after calculation. No operational data paths, configuration,
    or credentials are inferred.
    """
    destination = _output_path(output_dir)
    input_paths = {name: _input_path(path) for name, path in inputs.items()}
    _validate_keys(inputs)
    serialized = {name: _artifact_bytes(name, value) for name, value in artifacts.items()}
    if len({name.casefold() for name in artifacts}) != len(artifacts):
        raise ValueError("artifact filenames must be distinct ignoring case")
    _json_bytes(metadata)
    # Validation and serialization precede creation; existing files are never opened for writing.
    destination.mkdir(parents=True, exist_ok=False)
    try:
        input_records = {
            name: {"path": str(path), **_digest(path.read_bytes())} for name, path in sorted(input_paths.items())
        }
        if "input_hashes_used" in metadata:
            expected = metadata["input_hashes_used"]
            if not isinstance(expected, dict) or set(expected) != set(input_records):
                raise ValueError("input_hashes_used must cover exactly the supplied inputs")
            if any(expected[name] != record["sha256"] for name, record in input_records.items()):
                raise ValueError("input content changed after it was read for calculation")
        sources = _source_hashes()
        artifact_records = {}
        for name, content in sorted(serialized.items()):
            with (destination / name).open("xb") as handle:
                handle.write(content)
            artifact_records[name] = _digest(content)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "status": "COMPLETE",
            "inputs": input_records,
            "source_code": sources,
            "artifacts": artifact_records,
            "metadata": metadata,
        }
        pending_manifest = destination / ".manifest.pending"
        with pending_manifest.open("xb") as handle:
            handle.write(_json_bytes(manifest))
        # A failed/partial write must not leave a valid COMPLETE receipt. Hard-link
        # publication is atomic and refuses an existing target on Windows and POSIX.
        os.link(pending_manifest, destination / "manifest.json")
    except Exception as exc:
        try:
            with (destination / "failure.json").open("xb") as handle:
                handle.write(
                    _json_bytes(
                        {"schema_version": SCHEMA_VERSION, "status": "FAILED", "error_type": type(exc).__name__}
                    )
                )
        except OSError:
            pass
        raise
    try:
        pending_manifest.unlink()
    except OSError:
        pass  # All artifacts and the complete receipt are already published.
    return manifest
