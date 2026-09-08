"""Small synthetic CLI regressions for the migration verifier; no real archive."""
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
VERIFIER = ROOT / 'verificar_zip.py'
PYTHON = Path('C:/Users/Superleo13/projetos/brasileirao-predictor/.venv/Scripts/python.exe')
ALLOWED = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'COMSPEC', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA',
           'LOCALAPPDATA', 'PROGRAMDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432',
           'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'OS', 'HOMEDRIVE', 'HOMEPATH'}


def write_zip(path, files, *, bad_inner_hash=False):
    manifest = {'files': [{'path': name, 'bytes': len(data),
                           'sha256': '0' * 64 if bad_inner_hash else hashlib.sha256(data).hexdigest()}
                          for name, data in files.items()]}
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('MANIFESTO_SHA256.json', json.dumps(manifest))
    path.with_suffix('.zip.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n', encoding='utf-8')


def extended_path(path):
    # Independent access to a known synthetic long path for the assertion.
    value = os.path.abspath(path)
    return '\\\\?\\' + value if os.name == 'nt' else value


def main():
    base = ROOT / 'verifier_tests' / datetime.now(UTC).strftime('%Y%m%dT%H%M%S')
    base.mkdir(parents=True, exist_ok=False)
    source = VERIFIER.read_bytes()
    (base / 'verificar_zip.py.snapshot').write_bytes(source)
    env = {key: value for key, value in os.environ.items() if key.upper() in ALLOWED}
    results = []

    def cli_case(name, files, *, extract=True, bad_inner_hash=False, bad_outer_hash=False,
                 traversal=False, nonempty=False, crc_corrupt=False, long_path=False):
        case = base / name
        case.mkdir()
        archive = case / 'synthetic.zip'
        write_zip(archive, files, bad_inner_hash=bad_inner_hash)
        if bad_outer_hash:
            archive.with_suffix('.zip.sha256').write_text('0' * 64 + '\n', encoding='utf-8')
        if crc_corrupt:
            raw = bytearray(archive.read_bytes())
            payload = next(iter(files.values()))
            position = raw.find(payload)
            assert position >= 0
            raw[position] ^= 1
            archive.write_bytes(raw)
            archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(raw).hexdigest(), encoding='utf-8')
        destination = case / 'out'
        sentinel = destination / 'existing.txt'
        if nonempty:
            destination.mkdir()
            sentinel.write_bytes(b'PRESERVE THIS SYNTHETIC FILE')
        receipt_path = case / 'verifier_receipt.json'
        args = [str(PYTHON), '-X', 'utf8', str(VERIFIER), str(archive), '--recibo', str(receipt_path)]
        if extract:
            args += ['--extrair', str(destination)]
        run = subprocess.run(args, env=env, capture_output=True, timeout=20,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        (case / 'stdout.log').write_bytes(run.stdout)
        (case / 'stderr.log').write_bytes(run.stderr)
        expected_success = not any((bad_inner_hash, bad_outer_hash, traversal, nonempty, crc_corrupt))
        assert (run.returncode == 0) == expected_success, name + ': ' + run.stderr.decode('utf-8', errors='replace')
        if expected_success:
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            assert receipt['status'] == 'PASS' and receipt['crc_and_sha256_checked']
            assert receipt['manifest_files_checked'] == len(files)
            assert not receipt['application_started'] and not receipt['tasks_imported']
            if extract:
                for relative, expected in files.items():
                    with open(extended_path(destination / relative), 'rb') as stream:
                        assert stream.read() == expected
        else:
            assert not receipt_path.exists(), 'Rejected archive must not have success receipt'
        if nonempty:
            assert sentinel.read_bytes() == b'PRESERVE THIS SYNTHETIC FILE'
            assert list(destination.iterdir()) == [sentinel]
        if traversal:
            assert not (case / 'escaped.txt').exists()
            assert not destination.exists()
        if bad_outer_hash:
            assert not destination.exists()
        result = {'name': name, 'command': args, 'exit_code': run.returncode, 'expected_success': expected_success,
                  'passed': True, 'only_synthetic_files': True, 'no_success_receipt_on_rejection': not expected_success}
        if long_path:
            longest = max(len(str(destination / relative)) for relative in files)
            assert longest > 260
            result['longest_absolute_path_characters'] = longest
            result['windows_extended_path_extraction_verified'] = os.name == 'nt'
        results.append(result)

    summary = {'started_at_utc': datetime.now(UTC).isoformat(), 'verifier_sha256': hashlib.sha256(source).hexdigest(),
               'real_migration_archive_used': False, 'private_environment_read': False,
               'source_modified': False, 'cases': results, 'passed': False}
    try:
        simple = {'projetos/synthetic/hello.txt': b'hello synthetic migration\n', 'migracao/info.json': b'{"synthetic":true}\n'}
        cli_case('valid_verify', simple, extract=False)
        cli_case('valid_extract', simple)
        cli_case('bad_inner_hash', simple, bad_inner_hash=True)
        cli_case('bad_outer_hash', simple, bad_outer_hash=True)
        cli_case('traversal', {'../escaped.txt': b'not a real file'}, traversal=True)
        cli_case('nonempty_destination', simple, nonempty=True)
        cli_case('bad_crc', {'payload.txt': b'UNIQUE_SYNTHETIC_CRC_CONTENT_458719'}, crc_corrupt=True)
        relative = '/'.join(['projetos'] + ['synthetic_segment_' + str(index).zfill(2) for index in range(12)] + ['long.txt'])
        cli_case('long_windows_path', {relative: b'long-path synthetic content'}, long_path=True)
        assert hashlib.sha256(VERIFIER.read_bytes()).hexdigest() == summary['verifier_sha256']
        summary['passed'] = True
    finally:
        summary['finished_at_utc'] = datetime.now(UTC).isoformat()
        (base / 'results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(json.dumps({'passed': summary['passed'], 'cases_passed': len(results),
                          'receipt': str(base / 'results.json'), 'verifier_source_unchanged': summary['source_modified'] is False}, indent=2))


if __name__ == '__main__':
    main()
