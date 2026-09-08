"""Verify the migration ZIP and optionally extract it to a new empty folder."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile


def safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if not name or not path.parts or '\\' in name or path.is_absolute() or any(part in ('', '.', '..') or ':' in part for part in path.parts):
        raise ValueError('Unsafe ZIP path: ' + name)
    if path.as_posix() != name.rstrip('/'):
        raise ValueError('Noncanonical ZIP path: ' + name)
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{prefix}{n}' for prefix in ('COM', 'LPT') for n in range(1, 10)}
    if any(part.rstrip(' .') != part or part.split('.')[0].upper() in reserved for part in path.parts):
        raise ValueError('Path cannot be restored safely on Windows: ' + name)
    return name.rstrip('/')


def windows_path(path: Path) -> str:
    value = str(path.absolute())
    if os.name != 'nt' or value.startswith('\\\\?\\'):
        return value
    return '\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value


def verify(archive_path: Path, destination: Path | None = None) -> dict:
    if destination is not None:
        destination = destination.absolute()
        if destination.is_symlink() or (destination.exists() and (not destination.is_dir() or any(destination.iterdir()))):
            raise ValueError('Extraction requires a new or empty regular directory.')
        if destination.exists() and os.name == 'nt' and destination.stat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError('Extraction destination cannot be a junction.')
    checksum = archive_path.with_suffix('.zip.sha256')
    archive_hash = hashlib.sha256()
    with archive_path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            archive_hash.update(chunk)
    digest = archive_hash.hexdigest()
    if checksum.exists() and checksum.read_text(encoding='utf-8-sig').split()[0].lower() != digest:
        raise ValueError('ZIP SHA-256 differs from its checksum file.')
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        normalized = [safe_name(info.filename) for info in infos]
        if len({name.casefold() for name in normalized}) != len(normalized):
            raise ValueError('ZIP contains duplicate or colliding names.')
        if any(stat.S_ISLNK(info.external_attr >> 16) for info in infos):
            raise ValueError('ZIP contains symbolic links.')
        manifest = json.loads(archive.read('MANIFESTO_SHA256.json'))
        expected = {entry['path']: entry for entry in manifest['files']}
        if len(expected) != len(manifest['files']):
            raise ValueError('Duplicate manifest path.')
        actual = {info.filename for info in infos if not info.is_dir()}
        if actual != set(expected) | {'MANIFESTO_SHA256.json'}:
            raise ValueError('ZIP contents differ from the manifest.')
        for name in expected:
            safe_name(name)
        total = 0
        for index, info in enumerate(infos):
            name = safe_name(info.filename)
            if info.is_dir():
                continue
            wanted = expected.get(name)
            digest_file = hashlib.sha256()
            count = 0
            output = None
            if destination is not None:
                target = destination.joinpath(*PurePosixPath(name).parts)
                os.makedirs(windows_path(target.parent), exist_ok=True)
                output = open(windows_path(target), 'xb')
            try:
                with archive.open(info) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        count += len(chunk)
                        digest_file.update(chunk)
                        if output is not None:
                            output.write(chunk)
            finally:
                if output is not None:
                    output.close()
            if wanted is not None and (count != wanted['bytes'] or digest_file.hexdigest() != wanted['sha256']):
                raise ValueError('File SHA-256 mismatch: ' + name)
            total += count
            if index and index % 5000 == 0:
                print(json.dumps({'files_checked': index, 'total_entries': len(infos)}), flush=True)
        return {'status': 'PASS', 'zip_sha256': digest, 'manifest_files_checked': len(expected),
                'uncompressed_bytes_read': total, 'crc_and_sha256_checked': True,
                'extracted_to': str(destination) if destination else None,
                'application_started': False, 'tasks_imported': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip', type=Path)
    parser.add_argument('--extrair', type=Path, metavar='PASTA_NOVA', help='Verify while extracting to a new/empty folder; does not start the project.')
    parser.add_argument('--recibo', type=Path, help='Write the verification receipt to a new JSON file.')
    args = parser.parse_args()
    result = verify(args.zip, args.extrair)
    if args.recibo:
        with args.recibo.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
