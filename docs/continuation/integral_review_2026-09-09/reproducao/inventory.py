"""Read source metadata and explicitly allowed receipts; never read cohort contents."""
import ast
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/BRASILEIRAO/brasileirao-predictor')

def save(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def main():
    tracked = subprocess.check_output(['git', 'ls-files', '-s'], cwd=REPO, text=True).splitlines()
    save('tracked_initial.json', {'at': datetime.now(UTC).isoformat(), 'entries': tracked})
    forbidden = ('h14', 'h15', 'h9', 'a1_', '_a1', 'prospective', 'shadow', 'governanca', 'attest', 'collector')
    sources = []
    for folder in ('brasileirao_predictor', 'brasileirao_scripts', 'tests', 'dotnet', 'scripts'):
        for p in sorted((REPO / folder).rglob('*')):
            if not p.is_file() or p.suffix not in {'.py', '.cs', '.csproj', '.ps1'}:
                continue
            rel = p.relative_to(REPO).as_posix()
            meta = {'path': rel, 'bytes': p.stat().st_size}
            if any(word in rel.lower() for word in forbidden):
                meta['review'] = 'metadata_only_protected_or_adjacent'
            else:
                raw = p.read_bytes()
                content = raw.decode('utf-8-sig')
                meta.update(sha256=hashlib.sha256(raw).hexdigest(), lines=len(content.splitlines()), review='static_inventory')
                if p.suffix == '.py':
                    tree = ast.parse(content)
                    meta['imports'] = sorted({
                        (n.module or '') if isinstance(n, ast.ImportFrom) else alias.name
                        for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                        for alias in (n.names if isinstance(n, ast.Import) else [None])
                    })
                    meta['functions'] = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
                    meta['effect_indicators'] = [word for word in ('sqlite3', 'redis', 'subprocess', 'requests', 'urllib', 'socket', '.env', 'read_text', 'read_bytes', 'write_text', 'write_bytes', 'unlink', 'rmtree', 'pickle', 'eval(', 'exec(') if word in content]
                    meta['protected_reference'] = any(word in content.lower() for word in ('h14', 'h15', 'h9_', 'a1_', 'prospective.db', 'evaluate_gate_a1'))
            sources.append(meta)
    save('source_inventory.json', sources)
    save('environment.json', {'at': datetime.now(UTC).isoformat(), 'python':sys.version, 'executable':sys.executable, 'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}})
    save('candidate_tests.json', [r for r in sources if r['path'].startswith('tests/') and r['review']=='static_inventory' and not r.get('protected_reference')])
    print(json.dumps({'source_files':len(sources), 'static_inventory':sum(r['review']=='static_inventory' for r in sources), 'candidate_tests':sum(r['path'].startswith('tests/') and r['review']=='static_inventory' and not r.get('protected_reference') for r in sources)}))

if __name__ == '__main__':
    main()
