"""Reconcile current public artifacts and metadata without application imports or outcomes."""
import collections
import hashlib
import importlib.metadata as md
import json
import os
import shutil
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

root = Path(__file__).resolve().parent
base = Path('C:/BRASILEIRAO')
repo = base / 'brasileirao-predictor'
prior = repo / 'docs/continuation/artifact_integrity_2026-09-10'
start = '6c850454418a1c7e878fdb6a461dea509571caec'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=repo).decode('utf-8').strip()

def fingerprint(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}

def dump(name, obj):
    (root / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

assert git('rev-parse', 'HEAD') == start
current = dict(checked_at=datetime.now(UTC).isoformat(), base=start, branch=git('branch', '--show-current'),
               worktrees=git('worktree', 'list', '--porcelain'), git_executable=shutil.which('git'),
               docker_in_path=shutil.which('docker'), podman_in_path=shutil.which('podman'),
               source_changes=git('diff', '--name-only').splitlines(), operational_apps_started=False)
dump('current-state.json', current)

inventory = json.loads((prior / 'evidence/source-inventory.json').read_text(encoding='utf-8'))
changed = set(current['source_changes'])
comparisons = []
for row in inventory:
    path = repo / row['path']
    if row['review'] == 'protected_contract_only_no_execution':
        comparisons.append({'path': row['path'], 'status': 'protected_metadata_only', 'present': path.exists()})
        continue
    actual = fingerprint(path)
    expected = {key: row[key] for key in ('bytes', 'sha256')}
    assert actual == expected or row['path'] in changed, row['path']
    comparisons.append({'path': row['path'], 'status': 'unchanged_hash' if actual == expected else 'changed_this_round', **actual})
known_paths = {row['path'] for row in inventory}
source_roots = {row['path'].split('/')[0] for row in inventory}
tracked = git('ls-files', '--', *sorted(source_roots)).splitlines()
unlisted = [p for p in tracked if p not in known_paths]
dump('inventory-verification.json', {'base_inventory_count': len(inventory), 'counts': dict(collections.Counter(row['review'] for row in inventory)),
    'source_roots': sorted(source_roots), 'tracked_paths_outside_source_inventory': unlisted,
    'comparison_counts': dict(collections.Counter(r['status'] for r in comparisons)), 'files': comparisons,
    'scope': 'Source inventory is not every project/config/test/document file. No protected source content read.'})

manifest = json.loads((prior / 'evidence/manifest.json').read_text(encoding='utf-8'))
for relative, expected in manifest.items():
    path = prior / relative
    assert path.resolve().is_relative_to(prior)
    assert fingerprint(path) == expected, relative
audit = json.loads((base / 'AUDITORIA/INTEGRIDADE_ARTEFATOS_2026-09-10.json').read_text(encoding='utf-8'))
assert audit['commit'] == start
artifacts = {}
for label in ('zip', 'bundle'):
    expected = audit[label]
    actual = fingerprint(Path(expected['path']))
    assert all(actual[key] == expected[key] for key in actual)
    artifacts[label] = {'path': expected['path'], **actual}
assert git('rev-parse', 'HEAD^{tree}') == audit['restored_tree']
dump('prior-evidence-verification.json', {'checked_at': datetime.now(UTC).isoformat(), 'commit': start,
    'manifest_entries_verified': len(manifest), 'artifacts': artifacts, 'tree_matches_prior_restore': True,
    'scope': 'Fresh byte/hash checks; previous test executions and restore are historical, not rerun here.'})

project = tomllib.loads((repo / 'pyproject.toml').read_text())
installed = {canonicalize_name(d.metadata['Name']): d for d in md.distributions() if d.metadata['Name']}
pending = [Requirement(raw) for raw in project['project']['dependencies']]
for requirements in project['project']['optional-dependencies'].values():
    pending.extend(Requirement(raw) for raw in requirements)
seen = set()
requirements_checked = []
conflicts = []
while pending:
    req = pending.pop()
    name = canonicalize_name(req.name)
    key = (name, tuple(sorted(req.extras)), str(req.specifier))
    if key in seen:
        continue
    seen.add(key)
    dist = installed.get(name)
    ok = dist is not None and (not req.specifier or dist.version in req.specifier)
    record = {'requirement': str(req), 'installed': None if dist is None else dist.version, 'satisfied': bool(ok)}
    requirements_checked.append(record)
    if not ok:
        conflicts.append(record)
        continue
    for raw in dist.requires or []:
        dependency = Requirement(raw)
        if dependency.marker is None or any(dependency.marker.evaluate({'extra': extra}) for extra in {''} | req.extras):
            pending.append(dependency)
cache = base / 'work/implementacao-2026-09-10/uv-cache/archive-v0/Myxg33JoTOLihE8rOwRs4/hatchling-1.32.0.dist-info/METADATA'
dump('dependency-extras.json', {'checked_at': datetime.now(UTC).isoformat(), 'conflicts': conflicts,
    'requirements_checked': requirements_checked, 'hiredis': installed['hiredis'].version,
    'hatchling_cached_metadata': {'path': str(cache), **fingerprint(cache)},
    'build_scope': 'Hatchling 1.32.0 is cached for isolated uv builds; not installed in the runtime venv. Current offline build verifies availability.'})
assert not conflicts

dc = base / 'work/data-completion-2026-09-09'
hashes = {'followup_capture.py': '31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88',
          'audit_followup.py': 'ebce7ddeb384b347be4985b7a3812a1b83c7dfaceafdb3e2a6cb00f7e2d09a24'}
for name, sha in hashes.items():
    assert fingerprint(dc / name)['sha256'] == sha
csv = dc / 'public_sources/football_data_bra_origin_csv.csv'
csv_hash = fingerprint(csv)
assert csv_hash['sha256'] == 'ba3e9ea79ab4091b117a901f3914940cea07f1fe06de0deb57af5076f664ccb6'
dump('data-metadata.json', {'checked_at': datetime.now(UTC).isoformat(), 'helper_hashes': hashes,
    'attempt_exists': (dc / 'followup/attempt.json').exists(), 'receipt_exists': (dc / 'followup/receipt.json').exists(),
    'decision_utc': '2026-09-11T23:00:00Z', 'csv': {'path': str(csv), **csv_hash},
    'automation_view_return': 'Rendered automation card in the app.',
    'automation_state': 'NOT_VERIFIABLE_FROM_TEXT_RESPONSE',
    'expected_local_automation_definition_exists': (Path('C:/Users/leona/.codex/automations/completar-dados-do-brasileir-o/automation.toml')).exists(),
    'scope': 'Hash/existence only. No API, quota, outcome reading, schedule mutation or protected evaluator execution.'})
print(json.dumps({'inventory':len(inventory), 'unlisted_in_roots':len(unlisted), 'prior_manifest':len(manifest),
    'requirements_checked':len(requirements_checked), 'dependency_conflicts':len(conflicts), 'data_hashes_ok':True}))
