"""Copy the explicitly requested project roots, then create a hash-manifested ZIP."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import zipfile

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
OUT = ROOT / 'outputs/MIGRACAO_WINDOWS'
STAGE = WORK / 'stage_files'
PREFIXES = {
    'projeto': 'projetos/brasileirao-predictor',
    'backups': 'projetos/brasileirao-predictor-sessoes',
    'tarefa': 'tarefa',
    'operacao': 'externos/predictor-data',
    'backups_locais': 'externos/localappdata-brasileirao-backups',
    'ops_padrao': 'externos/predictor-ops-default-state',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def copy_stable(source, name):
    target = STAGE.joinpath(*name.split('/'))
    assert target.resolve().is_relative_to(STAGE.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        before = source.stat()
        digest = hashlib.sha256()
        size = 0
        with source.open('rb') as inp, target.open('wb') as out:
            for chunk in iter(lambda: inp.read(4 * 1024 * 1024), b''):
                size += len(chunk)
                digest.update(chunk)
                out.write(chunk)
        after = source.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino) and size == before.st_size:
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            return {'path': name, 'bytes': size, 'sha256': digest.hexdigest(),
                    'source': str(source), 'source_mtime_ns': before.st_mtime_ns,
                    'copied_at_utc': datetime.now(UTC).isoformat(), 'stable_during_copy': True}
        time.sleep(.1)
    raise RuntimeError('Source changed during three copy attempts: ' + str(source))


def stage():
    if STAGE.exists():
        raise RuntimeError('A stage already exists; use its receipt instead of overwriting it.')
    inventory = read(WORK / 'inventory.json')
    for issue in inventory['issues']:
        if not (issue['source'] == 'projeto' and issue['path'] == '.pytest_cache' and issue['kind'] == 'unreadable_directory'):
            raise RuntimeError('Unreviewed inaccessible source: ' + str(issue))
    needed = sum(item['bytes'] for item in inventory['files'])
    if shutil.disk_usage(WORK).free < needed * 2 + 2_000_000_000:
        raise RuntimeError('Not enough space for staging and a worst-case ZIP.')
    state = {'started_at_utc': datetime.now(UTC).isoformat(), 'status': 'COPYING',
             'roots': inventory['roots'], 'archive_prefixes': PREFIXES,
             'omissions': inventory['issues'], 'files': []}
    STAGE.mkdir()
    try:
        for index, entry in enumerate(inventory['files']):
            source = Path(inventory['roots'][entry['source']]) / entry['path']
            name = PREFIXES[entry['source']] + '/' + entry['path']
            state['files'].append(copy_stable(source, name))
            if index % 3000 == 0:
                print(json.dumps({'staged_files': index + 1, 'total': len(inventory['files'])}), flush=True)
        state['status'] = 'STAGED'
    except Exception as exc:
        state['status'], state['error'] = 'FAILED', str(exc)
        raise
    finally:
        state['finished_at_utc'] = datetime.now(UTC).isoformat()
        write(WORK / 'stage_receipt.json', state)
    print(json.dumps({'status': state['status'], 'files': len(state['files']),
                      'bytes': sum(item['bytes'] for item in state['files'])}), flush=True)


def archive_name_for_source(source, roots):
    source = Path(source).resolve()
    for label, root in roots.items():
        root = Path(root).resolve()
        if source.is_relative_to(root):
            return PREFIXES[label] + '/' + source.relative_to(root).as_posix()
    raise ValueError('Snapshot source is outside inventoried roots.')


def refresh():
    state = read(WORK / 'stage_receipt.json')
    assert state['status'] == 'STAGED'
    inventory = read(WORK / 'inventory.json')
    assert inventory['roots'] == state['roots']
    assert inventory['issues'] == state['omissions']
    by_name = {entry['path']: entry for entry in state['files']}
    current = []
    changed = []
    start = datetime.now(UTC).isoformat()
    for entry in inventory['files']:
        source = Path(inventory['roots'][entry['source']]) / entry['path']
        name = PREFIXES[entry['source']] + '/' + entry['path']
        prior = by_name.pop(name, None)
        info = source.stat()
        if prior and (info.st_size, info.st_mtime_ns) == (prior['bytes'], prior['source_mtime_ns']):
            current.append(prior)
        else:
            current.append(copy_stable(source, name))
            changed.append(name)
    if not (WORK / 'stage_receipt_initial.json').exists():
        shutil.copy2(WORK / 'stage_receipt.json', WORK / 'stage_receipt_initial.json')
    state['files'] = current
    state['finished_at_utc'] = datetime.now(UTC).isoformat()
    state['final_refresh'] = {'started_at_utc': start, 'finished_at_utc': state['finished_at_utc'],
                              'new_or_updated': changed, 'no_longer_present_at_source': list(by_name)}
    write(WORK / 'stage_receipt.json', state)
    print(json.dumps({'status': 'REFRESHED', 'files': len(current), 'new_or_updated': len(changed),
                      'no_longer_present_at_source': len(by_name)}), flush=True)


def build():
    state = read(WORK / 'stage_receipt.json')
    assert state['status'] == 'STAGED'
    OUT.mkdir(parents=True, exist_ok=True)
    archive_path = OUT / 'brasileirao-predictor-migracao.zip'
    if archive_path.exists():
        raise RuntimeError('Refusing to overwrite a completed ZIP.')
    files = list(state['files'])
    extras = [p for p in WORK.iterdir() if p.is_file() and p.suffix in {'.py', '.md', '.json', '.ps1', '.log'}]
    for folder in ['tasks', 'private', 'verifier_tests']:
        for path in (WORK / folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and (folder != 'verifier_tests' or path.suffix in {'.json', '.log', '.py'}):
                extras.append(path)
    for source in sorted(set(extras)):
        files.append(copy_stable(source, 'migracao/' + source.relative_to(WORK).as_posix()))
    files.append(copy_stable(WORK / 'LEIA_PRIMEIRO.md', 'LEIA_PRIMEIRO.md'))
    snapshot_receipts = read(WORK / 'sqlite_snapshot_receipts_final.json')
    snapshots = snapshot_receipts if isinstance(snapshot_receipts, list) else snapshot_receipts['snapshots']
    restore_map = []
    for item in snapshots:
        assert item['status'] == 'ok' and item['integrity_ok'], item['source_path']
        source = Path(item['snapshot_path'])
        assert sha(source) == item['snapshot_sha256'], str(source)
        snapshot_name = 'snapshots_sqlite/' + source.relative_to(WORK / 'sqlite_snapshots').as_posix()
        copied = copy_stable(source, snapshot_name)
        files.append(copied)
        receipt_file = Path(item['receipt_path'])
        files.append(copy_stable(receipt_file, 'snapshots_sqlite/' + receipt_file.name))
        restore_map.append({'source_archive_path': archive_name_for_source(item['source_path'], state['roots']),
                            'snapshot_archive_path': snapshot_name, 'snapshot_sha256': copied['sha256'],
                            'receipt': item})
    names = [entry['path'] for entry in files]
    assert len(set(name.casefold() for name in names)) == len(names), 'Duplicate archive path'
    manifest = {
        'created_at_utc': datetime.now(UTC).isoformat(),
        'scope': 'Project source, Git, ignored/local data, project session backups, task workspace, configured external data, project environment and scheduler exports.',
        'entire_windows_disk_image': False,
        'source_roots': state['roots'], 'archive_prefixes': PREFIXES,
        'copy_window': {'start': state['started_at_utc'], 'end': state['finished_at_utc']},
        'snapshot_type': 'Per-file stable copies and per-database verified SQLite snapshots; no global VSS snapshot.',
        'contains_private_api_keys': True,
        'tasks_imported_or_changed': False,
        'old_computer_jobs_still_enabled': True,
        'omissions': state['omissions'],
        'migration_temporary_files_excluded': True,
        'snapshot_restore_map': restore_map,
        'files': files,
    }
    write(OUT / 'MANIFESTO_SHA256.json', manifest)
    partial = archive_path.with_suffix('.zip.incomplete')
    with zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True, strict_timestamps=False) as archive:
        for index, entry in enumerate(files):
            source = STAGE.joinpath(*entry['path'].split('/'))
            if sha(source) != entry['sha256']:
                raise ValueError('Stage changed before archiving: ' + entry['path'])
            archive.write(source, entry['path'])
            if index % 3000 == 0:
                print(json.dumps({'zipped_files': index + 1, 'total': len(files)}), flush=True)
        archive.write(OUT / 'MANIFESTO_SHA256.json', 'MANIFESTO_SHA256.json')
    os.rename(partial, archive_path)
    digest = sha(archive_path)
    archive_path.with_suffix('.zip.sha256').write_text(digest + '  ' + archive_path.name + '\n', encoding='utf-8')
    shutil.copy2(WORK / 'verificar_zip.py', OUT / 'verificar_zip.py')
    shutil.copy2(WORK / 'RESTAURAR_NO_WINDOWS.md', OUT / 'RESTAURAR_NO_WINDOWS.md')
    write(OUT / 'criacao.json', {'status': 'CREATED_AWAITING_FULL_VERIFICATION', 'archive': str(archive_path),
                                'files': len(files), 'bytes': archive_path.stat().st_size,
                                'sha256': digest, 'contains_private_api_keys': True})
    print(json.dumps({'status': 'CREATED_AWAITING_FULL_VERIFICATION', 'files': len(files),
                      'zip_bytes': archive_path.stat().st_size, 'sha256': digest}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'refresh', 'build'))
    args = parser.parse_args()
    {'stage': stage, 'refresh': refresh, 'build': build}[args.action]()
