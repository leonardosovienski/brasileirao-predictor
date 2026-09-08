"""Derive a data/config ZIP from explicit names; never execute/read semantic payloads.

The filename policy guards an explicit reviewed plan. It cannot establish whether
arbitrary text/serialized data contains code. Nested ZIPs receive metadata audits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import tempfile
import unicodedata
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

if __package__:
    from .verify_archive import verify
else:
    from verify_archive import verify

MANIFEST = "MANIFESTO_SHA256.json"
PLAN_ENTRY = "MIGRATION_SELECTION_PLAN.json"
EXCLUSIONS_ENTRY = "MIGRATION_EXCLUSIONS.json"
CHUNK = 1024 * 1024
MAX_METADATA_BYTES = 64 * CHUNK
MAX_NESTED_ZIP_BYTES = 256 * CHUNK
MAX_NESTED_ENTRIES = 100_000
MAX_NESTED_EXPANDED_BYTES = 4 * 1024 * CHUNK
MAX_NESTED_DEPTH = 3
BLOCKED_PARTS = {".git", ".github", ".venv", "venv", "__pycache__", "node_modules", "bin", "obj"}
BLOCKED_SUFFIXES = {
    ".py",
    ".pyw",
    ".pyi",
    ".pyc",
    ".pyo",
    ".pyd",
    ".cs",
    ".fs",
    ".fsx",
    ".vb",
    ".ps1",
    ".psm1",
    ".psd1",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".cmd",
    ".bat",
    ".dll",
    ".exe",
    ".com",
    ".msi",
    ".msix",
    ".so",
    ".dylib",
    ".a",
    ".o",
    ".obj",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".wasm",
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hpp",
    ".rs",
    ".go",
    ".java",
    ".class",
    ".kt",
    ".kts",
    ".swift",
    ".m",
    ".mm",
    ".r",
    ".rmd",
    ".jl",
    ".lua",
    ".rb",
    ".php",
    ".pl",
    ".pm",
    ".sql",
    ".ipynb",
    ".patch",
    ".diff",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".vue",
    ".svelte",
    ".csproj",
    ".fsproj",
    ".vbproj",
    ".sln",
    ".slnx",
    ".props",
    ".targets",
    ".resx",
    ".pdb",
    ".lib",
    ".map",
    ".tar",
    ".tgz",
    ".tbz",
    ".tbz2",
    ".txz",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".whl",
    ".egg",
    ".nupkg",
    ".snupkg",
    ".jar",
    ".war",
    ".deb",
    ".rpm",
    ".bundle",
}
BLOCKED_NAMES = {
    "dockerfile",
    "containerfile",
    "makefile",
    "gnumakefile",
    "cmakelists.txt",
    "pyproject.toml",
    "poetry.lock",
    "uv.lock",
    "pipfile",
    "pipfile.lock",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "cargo.toml",
    "cargo.lock",
    "go.mod",
    "go.sum",
    "gemfile",
    "gemfile.lock",
    "composer.json",
    "composer.lock",
    "nuget.config",
    "packages.lock.json",
    "global.json",
    ".gitignore",
    ".gitattributes",
}
NESTED_DATA_SUFFIXES = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".parquet", ".feather"}


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _digest(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError("Expected a full SHA-256 digest.")
    return value.lower()


def _size(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Expected a nonnegative integer byte count.")
    return value


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _load_json(payload: bytes) -> dict:
    if len(payload) > MAX_METADATA_BYTES:
        raise ValueError("JSON metadata exceeds the size limit.")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON metadata key.")
            result[key] = value
        return result

    value = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON metadata object.")
    return value


def _stamp(path: Path) -> tuple:
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError("Input must be a regular file, not a symlink.")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _hash_file(path: Path) -> str:
    before = _stamp(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
    if _stamp(path) != before:
        raise ValueError("Input changed while hashing: " + str(path))
    return digest.hexdigest()


def _safe_name(name: str, *, directory: bool = False) -> str:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Unsafe archive name.")
    if directory and name.endswith("/"):
        name = name[:-1]
    path = PurePosixPath(name)
    if path.is_absolute() or path.as_posix() != name or any(part in {"", ".", ".."} for part in name.split("/")):
        raise ValueError("Noncanonical archive name: " + name)
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)}
    for part in path.parts:
        if (
            any(ord(char) < 32 or char in '<>:"|?*' for char in part)
            or part.endswith((".", " "))
            or len(part) > 255
            or part.split(".")[0].upper() in reserved
        ):
            raise ValueError("Archive name cannot be restored safely on Windows: " + name)
    return name


def _windows_key(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


def _check_payload_name(name: str) -> None:
    for part in PurePosixPath(_safe_name(name)).parts:
        lower = part.lower()
        if lower in BLOCKED_PARTS or lower in BLOCKED_NAMES:
            raise ValueError("Code/build/dependency path is forbidden: " + name)
        if set(PurePosixPath(lower).suffixes) & BLOCKED_SUFFIXES:
            raise ValueError("Source/compiled/opaque-archive suffix is forbidden: " + name)
        if lower.startswith("requirements") and lower.endswith(".txt"):
            raise ValueError("Dependency manifest is forbidden: " + name)
        if lower.startswith(("dockerfile.", "containerfile.")):
            raise ValueError("Build instructions are forbidden: " + name)


def _index(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    indexed, keys, file_keys = {}, set(), set()
    for info in archive.infolist():
        name = _safe_name(info.filename, directory=info.is_dir())
        key = _windows_key(name)
        if key in keys:
            raise ValueError("Duplicate or Windows-colliding ZIP names: " + name)
        keys.add(key)
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))):
            raise ValueError("Nonregular ZIP entry: " + name)
        if info.flag_bits & 1:
            raise ValueError("Encrypted ZIP entries are unsupported: " + name)
        if not info.is_dir():
            indexed[name] = info
            file_keys.add(key)
    for key in keys:
        if any(parent.as_posix() in file_keys for parent in PurePosixPath(key).parents if parent.as_posix() != "."):
            raise ValueError("Archive file collides with a parent directory.")
    return indexed


def _nested_zip(stream, *, depth: int = 1, budget: dict | None = None) -> dict:
    if depth > MAX_NESTED_DEPTH:
        raise ValueError("Nested ZIP depth exceeds the limit.")
    if budget is None:
        budget = {"entries": 0, "expanded_bytes": 0, "archives": 0}
    with tempfile.SpooledTemporaryFile(max_size=8 * CHUNK, mode="w+b") as spool:
        count = 0
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            count += len(chunk)
            if count > MAX_NESTED_ZIP_BYTES:
                raise ValueError("Nested ZIP file exceeds the byte limit.")
            spool.write(chunk)
        spool.seek(0)
        with zipfile.ZipFile(spool) as nested:
            budget["archives"] += 1
            for info in nested.infolist():
                _check_payload_name(_safe_name(info.filename, directory=info.is_dir()))
            for name, info in _index(nested).items():
                _check_payload_name(name)
                budget["entries"] += 1
                budget["expanded_bytes"] += info.file_size
                if budget["entries"] > MAX_NESTED_ENTRIES or budget["expanded_bytes"] > MAX_NESTED_EXPANDED_BYTES:
                    raise ValueError("Nested ZIP metadata exceeds the entry/size budget.")
                suffix = PurePosixPath(name).suffix.lower()
                if suffix == ".zip":
                    with nested.open(info) as child:
                        _nested_zip(child, depth=depth + 1, budget=budget)
                elif suffix not in NESTED_DATA_SUFFIXES:
                    raise ValueError("Nested ZIP contains an unapproved data type: " + name)
    return budget


def _metadata_entry(name: str, payload: bytes) -> dict:
    return {"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stream_entry(incoming, outgoing, expected: dict) -> None:
    count = 0
    digest = hashlib.sha256()
    for chunk in iter(lambda: incoming.read(CHUNK), b""):
        count += len(chunk)
        if count > expected["bytes"]:
            raise ValueError("Entry exceeds its declared size: " + expected["path"])
        digest.update(chunk)
        outgoing.write(chunk)
    if count != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
        raise ValueError("Entry SHA-256/size mismatch: " + expected["path"])


def _snapshot_maps(manifest: dict, selected: set[str], expected: dict) -> list[dict]:
    maps = manifest.get("snapshot_restore_map", [])
    if not isinstance(maps, list):
        raise ValueError("Invalid snapshot restore map.")
    seen = set()
    for item in maps:
        source = _safe_name(item["source_archive_path"])
        snapshot = _safe_name(item["snapshot_archive_path"])
        if source in seen:
            raise ValueError("Duplicate snapshot source mapping.")
        seen.add(source)
        receipt = item["receipt"]
        receipt_name = PurePosixPath(snapshot).parent / PureWindowsPath(receipt["receipt_path"]).name
        receipt_name = _safe_name(receipt_name.as_posix())
        if not {source, snapshot, receipt_name}.issubset(selected):
            raise ValueError("Every original SQLite source/snapshot/receipt must remain included.")
        digest = _digest(item["snapshot_sha256"])
        if (
            expected[snapshot]["sha256"] != digest
            or _digest(receipt["snapshot_sha256"]) != digest
            or receipt.get("status") != "ok"
            or receipt.get("integrity_ok") is not True
        ):
            raise ValueError("Snapshot mapping does not match a successful original receipt.")
    return maps


def _validate_code_reference(commit: str, remote: str) -> None:
    if not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", commit):
        raise ValueError("--code-commit must be a full Git object ID (40 or 64 hex digits).")
    parsed = urlsplit(remote)
    if (
        parsed.scheme not in {"https", "ssh"}
        or not parsed.hostname
        or not parsed.path.strip("/")
        or parsed.password
        or parsed.query
        or parsed.fragment
        or (parsed.username and not (parsed.scheme == "ssh" and parsed.username == "git"))
    ):
        raise ValueError("--code-remote must be an HTTPS/SSH repository URL without secrets/query/fragment.")


def build_archive(source: Path, plan_path: Path, output: Path, *, code_commit: str, code_remote: str) -> dict:
    """Stream selected entries, preserve all SQLite maps and verify the final ZIP.

    All artifacts are exclusive. Source and extra file hashes are checked while
    copying; the source ZIP is also rehashed after copying. Private temporary
    spools are used only to inspect the central directories of nested ZIPs.
    """
    source, plan_path, output = Path(source).absolute(), Path(plan_path).absolute(), Path(output).absolute()
    _validate_code_reference(code_commit, code_remote)
    if output.suffix.lower() != ".zip":
        raise ValueError("Output must end in .zip.")
    artifacts = {
        "zip": output,
        "checksum": output.with_suffix(".zip.sha256"),
        "manifest": output.with_suffix(".manifest.json"),
        "plan": output.with_suffix(".selection_plan.json"),
        "exclusions": output.with_suffix(".exclusions.json"),
        "receipt": output.with_suffix(".creation.json"),
    }
    if any(path.exists() or path.is_symlink() for path in artifacts.values()):
        raise ValueError("Refusing to overwrite an existing output artifact.")
    plan_stamp = _stamp(plan_path)
    with plan_path.open("rb") as handle:
        plan_bytes = handle.read(MAX_METADATA_BYTES + 1)
    if _stamp(plan_path) != plan_stamp:
        raise ValueError("Plan changed while reading.")
    plan = _load_json(plan_bytes)
    if plan.get("schema_version") != 1 or isinstance(plan.get("schema_version"), bool):
        raise ValueError("Expected plan schema_version=1.")
    source_stamp = _stamp(source)
    source_hash = _hash_file(source)
    if source_hash != _digest(plan["source_sha256"]):
        raise ValueError("Source ZIP does not match the explicit plan.")
    started = _utc()
    created: list[tuple[Path, tuple]] = []

    def create(path: Path, payload: bytes) -> None:
        with path.open("xb") as handle:
            created.append((path, _stamp(path)))
            handle.write(payload)

    try:
        with zipfile.ZipFile(source) as archive:
            indexed = _index(archive)
            if MANIFEST not in indexed or indexed[MANIFEST].file_size > MAX_METADATA_BYTES:
                raise ValueError("Source lacks a bounded manifest.")
            manifest_bytes = archive.read(MANIFEST)
            if hashlib.sha256(manifest_bytes).hexdigest() != _digest(plan["source_manifest_sha256"]):
                raise ValueError("Source manifest does not match the plan.")
            original = _load_json(manifest_bytes)
            expected = {}
            for item in original["files"]:
                name = _safe_name(item["path"])
                if name in expected:
                    raise ValueError("Duplicate source manifest path.")
                expected[name] = {**item, "sha256": _digest(item["sha256"]), "bytes": _size(item["bytes"])}
            if set(indexed) != set(expected) | {MANIFEST}:
                raise ValueError("Source ZIP contents differ from its manifest.")
            if any(indexed[name].file_size != item["bytes"] for name, item in expected.items()):
                raise ValueError("Source ZIP size metadata differs from its manifest.")
            names, excluded, extras = plan["include_names"], plan["excluded"], plan.get("extras", [])
            if (
                not isinstance(names, list)
                or not names
                or not isinstance(excluded, list)
                or not isinstance(extras, list)
            ):
                raise ValueError("Plan requires inclusion/exclusion lists and an optional extras list.")
            for name in names:
                _check_payload_name(name)
            if len(set(names)) != len(names) or not set(names).issubset(expected):
                raise ValueError("Included names must be unique exact existing manifest names.")
            excluded_names = set()
            for item in excluded:
                name = _safe_name(item["path"])
                if (
                    name in excluded_names
                    or name not in expected
                    or not isinstance(item["reason"], str)
                    or not item["reason"].strip()
                ):
                    raise ValueError("Invalid/duplicate exclusion or missing reason.")
                excluded_names.add(name)
                if (
                    _size(item["bytes"]) != expected[name]["bytes"]
                    or _digest(item["sha256"]) != expected[name]["sha256"]
                ):
                    raise ValueError("Excluded metadata differs from the source manifest.")
            if excluded_names != set(expected) - set(names):
                raise ValueError("Exclusions must account for every unselected source entry exactly once.")
            maps = _snapshot_maps(original, set(names), expected)
            entries = [dict(expected[name]) for name in names]
            extra_paths = {}
            for item in extras:
                name = _safe_name(item["archive_path"])
                _check_payload_name(name)
                path = Path(item["source_path"])
                if not path.is_absolute():
                    raise ValueError("Extra sources must have explicit absolute paths.")
                _check_payload_name(path.name)
                _stamp(path)
                provenance = item.get("provenance")
                if not (
                    isinstance(provenance, str) and provenance.strip() or isinstance(provenance, dict) and provenance
                ):
                    raise ValueError("Extra sources require explicit provenance.")
                entries.append(
                    {
                        "path": name,
                        "bytes": _size(item["bytes"]),
                        "sha256": _digest(item["sha256"]),
                        "source": str(path),
                        "provenance": item["provenance"],
                    }
                )
                extra_paths[name] = path
            all_names = [entry["path"] for entry in entries] + [MANIFEST, PLAN_ENTRY, EXCLUSIONS_ENTRY]
            if len({_windows_key(name) for name in all_names}) != len(all_names):
                raise ValueError("Included/extra/generated names collide on Windows.")
            all_keys = {_windows_key(name) for name in all_names}
            if any(
                parent.as_posix() in all_keys
                for name in all_keys
                for parent in PurePosixPath(name).parents
                if parent.as_posix() != "."
            ):
                raise ValueError("Included file collides with a parent directory.")
            nested_audit = []
            for entry in entries:
                name = entry["path"]
                if PurePosixPath(name).suffix.lower() == ".zip":
                    with extra_paths[name].open("rb") if name in extra_paths else archive.open(indexed[name]) as stream:
                        nested_audit.append({"path": name, **_nested_zip(stream)})
            selection_payload = plan_bytes
            exclusion_payload = _json_bytes({"original_omissions": original.get("omissions", []), "excluded": excluded})
            entries += [
                _metadata_entry(PLAN_ENTRY, selection_payload),
                _metadata_entry(EXCLUSIONS_ENTRY, exclusion_payload),
            ]
            manifest = {
                **{key: value for key, value in original.items() if key not in {"files", "scope", "created_at_utc"}},
                "format": "data-only-archive/1",
                "created_at_utc": _utc(),
                "scope": (
                    "Explicitly selected data, configs, data backups and restoration documentation; "
                    "code is separate in Git."
                ),
                "code": {"commit": code_commit.lower(), "remote": code_remote, "included_in_archive": False},
                "source_archive_sha256": source_hash,
                "source_manifest_sha256": plan["source_manifest_sha256"].lower(),
                "selection_plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
                "filename_policy": (
                    "Explicit names plus source/build suffix and path denials; no semantic payload inspection."
                ),
                "nested_zip_audit": nested_audit,
                "snapshot_restore_map": maps,
                "files": entries,
            }
            final_manifest_bytes = _json_bytes(manifest)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as destination:
                created.append((output, _stamp(output)))
                with zipfile.ZipFile(
                    destination,
                    "w",
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=3,
                    allowZip64=True,
                    strict_timestamps=False,
                ) as outgoing:
                    for index, entry in enumerate(entries[:-2]):
                        name = entry["path"]
                        extra = extra_paths.get(name)
                        before = _stamp(extra) if extra is not None else None
                        with extra.open("rb") if extra is not None else archive.open(indexed[name]) as incoming:
                            with outgoing.open(name, "w", force_zip64=True) as sink:
                                _stream_entry(incoming, sink, entry)
                        if extra is not None and _stamp(extra) != before:
                            raise ValueError("Extra changed during copying: " + name)
                        if (index + 1) % 3000 == 0:
                            print(
                                json.dumps({"copied_entries": index + 1, "total_entries": len(entries) - 2}), flush=True
                            )
                    outgoing.writestr(PLAN_ENTRY, selection_payload)
                    outgoing.writestr(EXCLUSIONS_ENTRY, exclusion_payload)
                    outgoing.writestr(MANIFEST, final_manifest_bytes)
        if _stamp(source) != source_stamp or _hash_file(source) != source_hash:
            raise ValueError("Source ZIP changed during archive creation.")
        verification = verify(output)
        create(artifacts["checksum"], (verification["zip_sha256"] + "  " + output.name + "\n").encode("utf-8"))
        create(artifacts["manifest"], final_manifest_bytes)
        create(artifacts["plan"], selection_payload)
        create(artifacts["exclusions"], exclusion_payload)
        receipt = {
            "status": "PASS",
            "started_at_utc": started,
            "completed_at_utc": _utc(),
            "source": str(source),
            "source_sha256": source_hash,
            "source_unchanged": True,
            "output": str(output),
            "code_commit": code_commit.lower(),
            "code_remote": code_remote,
            "included_source_files": len(names),
            "extra_files": len(extras),
            "excluded_source_files": len(excluded),
            "snapshot_restore_maps_preserved": len(maps),
            "nested_zip_files_checked": len(nested_audit),
            "artifacts": {key: str(value) for key, value in artifacts.items()},
            "verification": verification,
            "payloads_executed": False,
            "database_queries": False,
        }
        create(artifacts["receipt"], _json_bytes(receipt))
        return receipt
    except BaseException:
        # Delete only this invocation's exclusive files, never preexisting/replaced
        # artifacts or source inputs. Every path must remain within the output dir.
        for path, identity in reversed(created):
            if path.exists() and path.resolve().parent == output.parent.resolve() and not path.is_symlink():
                if _stamp(path)[:2] == identity[:2]:
                    path.unlink()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--code-remote", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build_archive(
                args.source, args.plan, args.output, code_commit=args.code_commit, code_remote=args.code_remote
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
