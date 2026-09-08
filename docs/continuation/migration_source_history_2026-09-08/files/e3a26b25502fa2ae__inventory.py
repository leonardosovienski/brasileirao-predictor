"""File metadata inventory for the user-requested local migration; no data analysis."""
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'projeto': Path('C:/Users/Superleo13/projetos/brasileirao-predictor'),
    'backups': Path('C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes'),
    'tarefa': ROOT,
    'operacao': Path('C:/predictor/data'),
    'backups_locais': Path('C:/Users/Superleo13/AppData/Local/brasileirao-predictor/backups'),
    'ops_padrao': Path('C:/Users/Superleo13/.local/state/predictor-ops'),
}
OUTPUT = ROOT / 'outputs/MIGRACAO_WINDOWS'
summaries = {}
records = []
issues = []
for label, root in SOURCES.items():
    summary = {'files': 0, 'bytes': 0, 'top_level': {}}
    def walk(folder):
        try:
            items = list(os.scandir(folder))
        except OSError as exc:
            issues.append({'source': label, 'path': Path(folder).relative_to(root).as_posix(), 'kind': 'unreadable_directory', 'error': str(exc)})
            return
        for item in items:
            path = Path(item.path)
            if path in {OUTPUT, ROOT / 'work/migration'}:
                continue
            try:
                info = item.stat(follow_symlinks=False)
            except OSError as exc:
                issues.append({'source': label, 'path': path.relative_to(root).as_posix(), 'kind': 'unreadable_metadata', 'error': str(exc)})
                continue
            relative = path.relative_to(root).as_posix()
            if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                issues.append({'source': label, 'path': relative, 'kind': 'reparse_point', 'target': os.readlink(path) if item.is_symlink() else None})
                continue
            if item.is_dir(follow_symlinks=False):
                walk(path)
            elif item.is_file(follow_symlinks=False):
                summary['files'] += 1
                summary['bytes'] += info.st_size
                bucket = relative.split('/')[0]
                entry = summary['top_level'].setdefault(bucket, {'files': 0, 'bytes': 0})
                entry['files'] += 1
                entry['bytes'] += info.st_size
                records.append({'source': label, 'path': relative, 'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns})
    walk(root)
    summaries[label] = summary
result = {'at_utc': datetime.now(UTC).isoformat(), 'roots': {k: str(v) for k, v in SOURCES.items()},
          'summaries': summaries, 'issues': issues, 'files': records}
(ROOT / 'work/migration/inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'summaries': summaries, 'issues': issues, 'total_files': len(records),
                  'total_bytes': sum(r['bytes'] for r in records)}, ensure_ascii=False, indent=2))
