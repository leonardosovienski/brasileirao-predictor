from pathlib import Path

path = Path('C:/BRASILEIRAO/brasileirao-predictor/brasileirao_scripts/import_ou25_historical_backfill.py')
source = path.read_text(encoding='utf-8')
start = source.index('    conn.executescript(', source.index('def _build_backfill('))
end = source.index('    conn.close()', start)
block = source[start:end]
source = source[:start] + '    try:\n' + ''.join('    '+line if line.strip() else line for line in block.splitlines(keepends=True)) + '    finally:\n        conn.close()\n' + source[end+len('    conn.close()\n'):]
path.write_text(source, encoding='utf-8')
