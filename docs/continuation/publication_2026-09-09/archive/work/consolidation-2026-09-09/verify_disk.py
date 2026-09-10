"""Hash every preserved file without parsing outcomes, credentials or databases."""
import hashlib
import json
import os
import zipfile
from pathlib import Path

ROOT = Path('C:/BRASILEIRAO')
DATA = ROOT / 'DADOS_PRESERVADOS'
PACKAGE = ROOT / 'MIGRACAO_DADOS/MIGRACAO_DADOS'


def physical(path):
    prefix = chr(92) * 2 + '?' + chr(92)
    return Path(prefix + str(path.absolute())) if os.name == 'nt' else path


def digest(path):
    with physical(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    manifest = json.loads((DATA / 'MANIFESTO_SHA256.json').read_bytes())
    checked, total, mds = [], 0, []
    for index, expected in enumerate(manifest['files'], 1):
        path = (DATA / expected['path']).resolve()
        if not path.is_relative_to(DATA) or physical(path).is_symlink():
            raise ValueError('unsafe_preservation_path')
        size = physical(path).stat().st_size
        actual = digest(path)
        if actual != expected['sha256'] or size != expected['bytes']:
            raise ValueError('preserved_file_mismatch:' + expected['path'])
        entry = {'path': path.relative_to(ROOT).as_posix(), 'bytes': size, 'sha256': actual}
        checked.append(entry)
        total += size
        if path.suffix.lower() == '.md':
            mds.append({**entry, 'classification': 'MIGRATION_IMMUTABLE_NO_CONTENT_REVIEW'})
        if index % 3000 == 0:
            print(json.dumps({'files_checked_on_disk': index}), flush=True)
    with zipfile.ZipFile(PACKAGE / 'brasileirao-predictor-dados.zip') as archive:
        expected_manifest = archive.read('MANIFESTO_SHA256.json')
    if digest(DATA / 'MANIFESTO_SHA256.json') != hashlib.sha256(expected_manifest).hexdigest():
        raise ValueError('manifest_copy_mismatch')
    expected_names = {entry['path'] for entry in manifest['files']} | {'MANIFESTO_SHA256.json'}
    actual_names = {p.relative_to(physical(DATA)).as_posix() for p in physical(DATA).rglob('*') if p.is_file()}
    if actual_names != expected_names:
        raise ValueError('extra_or_missing_preserved_files')
    for area in ('ENTREGAS', 'MIGRACAO_DADOS'):
        for path in sorted((ROOT / area).rglob('*.md')):
            mds.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
                        'sha256': digest(path), 'classification': 'RECEIVED_COPY_NO_CONTENT_REVIEW'})
    (ROOT / 'AUDITORIA/markdown_fora_do_git.json').write_text(
        json.dumps({'count': len(mds), 'files': mds}, indent=2, ensure_ascii=False), encoding='utf-8')
    (ROOT / 'AUDITORIA/inventario_dados_preservados.json').write_text(
        json.dumps({'files': checked}, indent=2, ensure_ascii=False), encoding='utf-8')
    receipt = {'status': 'PASS', 'disk_files_hash_verified': len(checked), 'manifest_itself_verified': True,
               'file_set_exact_match': True, 'data_bytes_excluding_manifest': total,
               'markdown_outside_git_count': len(mds), 'database_queries': 0, 'payloads_executed': 0,
               'protected_outcomes_read': False, 'credential_values_emitted': False}
    (ROOT / 'AUDITORIA/verificacao_disco_2026-09-09.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
