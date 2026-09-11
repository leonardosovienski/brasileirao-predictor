"""Inventory and dependency contracts only; never import or execute project code."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/BRASILEIRAO/brasileirao-predictor')
old = json.loads((REPO / 'docs/continuation/integral_review_2026-09-09/evidence/source-inventory.json').read_text(encoding='utf-8'))
protected = {r['path'] for r in old if r['review'].startswith('metadata_only')}
protected.add('brasileirao_predictor/operational_readiness.py')
records = []
for base in ('brasileirao_predictor', 'brasileirao_scripts', 'tests', 'dotnet', 'scripts', 'tools'):
    for path in sorted((REPO / base).rglob('*')):
        if not path.is_file() or path.suffix not in {'.py', '.cs', '.ps1', '.json', '.csproj', '.yml', '.yaml'} or any(x in path.parts for x in ('obj', 'bin', '__pycache__')):
            continue
        rel = path.relative_to(REPO).as_posix()
        row = {'path': rel, 'bytes': path.stat().st_size, 'review': 'pending_semantic_review'}
        if rel in protected:
            # Only import declarations form the dependency contract here. No
            # function bodies/results are retained, displayed or executed.
            row['review'] = 'dependency_contract_only_protected'
        else:
            raw = path.read_bytes()
            row.update(sha256=hashlib.sha256(raw).hexdigest(), lines=len(raw.splitlines()))
        if path.suffix == '.py':
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            imports = []
            package = rel.removesuffix('.py').split('.') if False else rel.removesuffix('.py').split('/')[:-1]
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(a.name for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    parent = package[:len(package) - node.level + 1] if node.level else []
                    prefix = '.'.join(parent + ([node.module] if node.module else []))
                    imports.append(prefix)
                    imports.extend(prefix + '.' + a.name for a in node.names)
            row['import_contract'] = sorted(set(imports))
        records.append(row)
(ROOT / 'inventory.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
targets = ('predict', 'display', 'ratings', 'db', 'feature_builder', 'cron_update_models', 'prediction_protocol', 'data.bitemporal_store', 'data.the_odds_api_provider', 'data.sportmonks_provider', 'data.api_football_provider')
edges = {t: [r['path'] for r in records if r['review'].startswith('dependency_contract') and any(i == 'brasileirao_predictor.' + t or i.startswith('brasileirao_predictor.' + t + '.') for i in r.get('import_contract', []))] for t in targets}
(ROOT / 'protected-dependency-edges.json').write_text(json.dumps(edges, indent=2), encoding='utf-8')
print(json.dumps({'files': len(records), 'protected_contract_only': len(protected), 'direct_protected_consumers': edges}, indent=2))
