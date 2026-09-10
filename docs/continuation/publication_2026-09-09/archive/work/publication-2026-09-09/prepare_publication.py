"""Preserve authored session support files; never collect raw data or credentials."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

ROOT = Path('C:/BRASILEIRAO')
REPO = ROOT / 'brasileirao-predictor'
DEST = REPO / 'docs/continuation/publication_2026-09-09'
DEST.mkdir(parents=True, exist_ok=True)
SHA = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=REPO).decode().split('\0')
by_hash = {}
for rel in tracked:
    path = REPO / rel
    if rel and path.is_file():
        by_hash.setdefault(SHA(path), []).append(rel)

entries = []

def record_file(path, category, destination=None):
    digest = SHA(path)
    existing = by_hash.get(digest, [])
    entry = {'source_relative_to_root': path.relative_to(ROOT).as_posix(),
             'sha256': digest, 'bytes': path.stat().st_size, 'category': category}
    if existing:
        entry.update({'status': 'ALREADY_VERSIONED_IDENTICAL', 'git_paths': existing})
    else:
        target = DEST / (destination or ('archive/' + path.relative_to(ROOT).as_posix()))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        assert SHA(target) == digest
        rel = target.relative_to(REPO).as_posix()
        entry.update({'status': 'ADDED_IDENTICAL', 'git_paths': [rel]})
        by_hash.setdefault(digest, []).append(rel)
    entries.append(entry)

for folder in ['consolidation-2026-09-09', 'price-feasibility-2026-09-09',
               'data-completion-2026-09-09', 'execution-readiness-2026-09-09',
               'publication-2026-09-09']:
    for path in sorted((ROOT / 'work' / folder).glob('*.py')):
        record_file(path, 'AUTHORED_SUPPORT_SCRIPT_ARCHIVE_NOT_RUNTIME')

for path in sorted((ROOT / 'INSTRUCOES').iterdir()):
    if path.is_file() and path.suffix in {'.txt', '.md'}:
        record_file(path, 'USER_MANDATE')

audit_names = [
    'CONSOLIDACAO_2026-09-09.md', 'DADOS_COMPLEMENTARES_2026-09-09.md',
    'DADOS_COMPLEMENTARES_2026-09-09.json', 'EXECUTION_READINESS_2026-09-09.md',
    'EXECUTION_READINESS_2026-09-09.json', 'ENTREGA_CONSOLIDACAO.json',
    'HANDOFF_REVISAO_INTEGRAL_2026-09-09.json', 'PROMPT_FINAL_REVISAO_2026-09-09.json',
    'verificacao_migracao_2026-09-09.json', 'verificacao_disco_2026-09-09.json',
    'verificacao_disco_tentativa_01.json', 'backup_git_2026-09-09.json',
    'consolidacao_copias_2026-09-09.json', 'automacao_dados_2026-09-09.toml'
]
for name in audit_names:
    # Text snapshots retain local-context links and immutable historical assertions.
    target = 'archive/AUDITORIA/' + name + ('.txt' if name.endswith('.md') else '')
    record_file(ROOT / 'AUDITORIA' / name, 'HISTORICAL_SESSION_RECEIPT', target)
record_file(ROOT / 'LEIA_PRIMEIRO.md', 'ROOT_GUIDE_SNAPSHOT', 'archive/LEIA_PRIMEIRO.md.txt')

local_manifests = []
for name in ['inventario_dados_preservados.json', 'inventario_backup_DC_20260909.json',
             'markdown_fora_do_git.json', 'markdown_projeto.json']:
    p = ROOT / 'AUDITORIA' / name
    local_manifests.append({'relative_path': p.relative_to(ROOT).as_posix(),
                            'sha256': SHA(p), 'bytes': p.stat().st_size,
                            'publication': 'LOCAL_METADATA_INVENTORY_ONLY'})

manifest = {
    'created_at_utc': datetime.now(timezone.utc).isoformat(),
    'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO).decode().strip(),
    'scope': 'Authored code, instructions and sanitized receipts; no raw provider data or private inputs',
    'source_file_count': len(entries), 'entries': entries,
    'local_inventory_receipts': local_manifests,
    'local_only_categories': [
        'DADOS_PRESERVADOS and MIGRACAO_DADOS: received originals, private configuration and protected data',
        'Raw provider timelines, odds captures, CSV inputs and copied public-page bodies',
        'Operational databases, private settings and financial credentials',
        'Virtual environments, generated caches and binary backup copies',
        'Future observations or work after this snapshot'
    ],
    'previous_false_push_flags_are_dated_history': True,
    'financial_or_protected_operations_performed': False
}
(DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'source_files': len(entries),
                  'new_copies': sum(e['status'] == 'ADDED_IDENTICAL' for e in entries),
                  'already_versioned': sum(e['status'] == 'ALREADY_VERSIONED_IDENTICAL' for e in entries)}))
