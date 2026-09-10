"""Publish compact receipts; preserved payloads are never changed."""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('C:/BRASILEIRAO')
AUDIT = ROOT / 'AUDITORIA'
REPO = ROOT / 'brasileirao-predictor'
GIT = 'C:/Users/leona/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'
DELIVERY = Path('C:/Users/leona/Documents/Codex/2026-09-09/le/outputs/CONSOLIDACAO_BRASILEIRAO')


def read(name):
    return json.loads((AUDIT / name).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    disk, docs, copies, backup = (read(name) for name in (
        'verificacao_disco_2026-09-09.json', 'markdown_projeto.json',
        'consolidacao_copias_2026-09-09.json', 'backup_git_2026-09-09.json'))
    if any(item['status'] != 'PASS' for item in (disk, docs, copies, backup)):
        raise ValueError('incomplete_verification')
    for entry in docs['inventory']:
        if digest(REPO / entry['path']) != entry['sha256']:
            raise ValueError('documentation_changed_after_audit')
    for entry in copies['files']:
        if digest(ROOT / 'ENTREGAS/BRASILEIRAO_PF_20260909' / entry['source_relative']) != entry['sha256']:
            raise ValueError('delivery_copy_changed')
    status = subprocess.run([GIT, '-C', str(REPO), 'status', '--porcelain'], check=True, capture_output=True).stdout
    if status.strip():
        raise ValueError('working_tree_not_clean')
    head = subprocess.run([GIT, '-C', str(REPO), 'rev-parse', 'HEAD'], check=True, capture_output=True).stdout.decode().strip()
    if head != backup['restored_commit']:
        raise ValueError('backup_not_current')
    report = AUDIT / 'CONSOLIDACAO_2026-09-09.md'
    addition = (f'\n## Fechamento verificado\n\nCommit local: `{head}`, branch main, árvore limpa; sem push.\n'
                f'Links locais conferidos: {docs["local_links_checked"]}; destinos ausentes: 0.\n'
                f'Backup Git completo: `{backup["bundle"]}`.\nSHA-256: `{backup["sha256"]}`.\n'
                'A recuperação em repositório bare separado reproduziu o SHA final e passou no git fsck.\n')
    with report.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(addition)
    outside = read('markdown_fora_do_git.json')
    existing = {entry['path'] for entry in outside['files']}
    for path in (ROOT / 'LEIA_PRIMEIRO.md', report):
        relative = path.relative_to(ROOT).as_posix()
        if relative not in existing:
            outside['files'].append({'path': relative, 'bytes': path.stat().st_size,
                                     'sha256': digest(path), 'classification': 'CURRENT_ROOT_GUIDE_OR_AUDIT'})
    outside['count'] = len(outside['files'])
    outside['scope'] = 'Project documentation; excludes third-party environment/cache documentation and Git internals'
    (AUDIT / 'markdown_fora_do_git.json').write_text(json.dumps(outside, indent=2, ensure_ascii=False), encoding='utf-8')
    receipt = {
        'status': 'COMPLETE_VERIFIED', 'root': str(ROOT), 'repository': str(REPO), 'branch': 'main',
        'commit': head, 'working_tree_clean': True, 'push_performed': False,
        'data_files_verified': disk['disk_files_hash_verified'], 'manifest_verified': True,
        'missing_data_files': 0, 'extra_data_files': 0, 'mismatched_data_hashes': 0,
        'copied_external_delivery_files': copies['copied_delivery_files'],
        'project_markdown_indexed': docs['project_markdown_count'], 'outside_project_markdown_inventoried': outside['count'],
        'existing_markdown_byte_preserved': docs['preserved_existing_markdown_count'],
        'old_guides_preserved_as_full_copies': len(docs['historical_copies_match_base']),
        'active_local_links_checked': docs['local_links_checked'], 'broken_active_links': 0,
        'backup': backup, 'application_started': False, 'tasks_imported': False,
        'protected_cohorts_evaluated': False, 'financial_actions': False,
        'limits': ['Coverage is the supplied migration snapshot plus known current-session artifacts',
                   'Source snapshot recorded inaccessible .pytest_cache',
                   'Files created later or never supplied from the old computer cannot be attested',
                   'File completeness is not operational installation or environment portability'],
        'finished_at_utc': datetime.now(timezone.utc).isoformat(),
    }
    (AUDIT / 'ENTREGA_CONSOLIDACAO.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    DELIVERY.mkdir(parents=True, exist_ok=False)
    for name in ('CONSOLIDACAO_2026-09-09.md', 'ENTREGA_CONSOLIDACAO.json',
                 'verificacao_migracao_2026-09-09.json', 'verificacao_disco_2026-09-09.json', 'backup_git_2026-09-09.json'):
        shutil.copy2(AUDIT / name, DELIVERY / name)
        if digest(AUDIT / name) != digest(DELIVERY / name):
            raise ValueError('display_copy_mismatch')
    print(json.dumps(receipt, ensure_ascii=True))


if __name__ == '__main__':
    main()
