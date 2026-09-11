"""Create a checkpoint archive and verify a fresh bare Git restoration."""
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
base = Path('C:/BRASILEIRAO')
repo = base / 'brasileirao-predictor'
start = 'c2fd45675cf84cf6ba4ed637a111eaf5d6ba74ac'
out = base / 'ENTREGAS/BRASILEIRAO_LGC_20260910'
bundle = base / 'BACKUPS/brasileirao-predictor-LGC-20260910.bundle'
archive = base / 'ENTREGAS/BRASILEIRAO_LGC_20260910_entrega.zip'
restore = root / 'restored-git.git'
audit = base / 'AUDITORIA/CONSISTENCIA_LEDGER_2026-09-10.json'
docs = repo / 'docs/continuation/ledger_consistency_2026-09-10'
for path in (out, bundle, archive, restore, audit):
    assert path.resolve().is_relative_to(base) and not path.exists(), str(path)

def git_bytes(*args, cwd=repo):
    return subprocess.run(['git', *args], cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True).stdout

def git(*args, cwd=repo):
    return git_bytes(*args, cwd=cwd).decode('utf-8').strip()

def digest(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

commit = git('rev-parse', 'HEAD')
assert commit != start and git('rev-parse', 'HEAD^') == start
assert git('branch', '--show-current') == 'main'
assert not git('status', '--porcelain=v1')
changed = git('diff', '--name-only', start, commit).splitlines()
assert set(changed) == set(json.loads((root / "staged-paths.json").read_text()))
wheel = next((root / 'package-smoke-final/dist').glob('*.whl'))
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None
    module_checks = []
    for name in changed:
        if name.endswith('.py') and name.startswith(('brasileirao_predictor/', 'brasileirao_scripts/')):
            assert z.read(name) == (repo / name).read_bytes(), name
            module_checks.append(name)
out.mkdir(parents=True)
copies = {}

def copy(source, relative):
    target = out / relative
    assert target.resolve().is_relative_to(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    assert digest(source) == digest(target)
    copies[relative.as_posix()] = digest(target)

for name in changed:
    copy(repo / name, Path('changed-files') / name)
for path in sorted(docs.rglob('*')):
    if path.is_file():
        copy(path, Path('review') / path.relative_to(docs))
for path in (root / 'package-smoke-final/dist').iterdir():
    copy(path, Path('dist') / path.name)
for name in ['run_isolated.py', 'check_changed.py', 'write_docs.py',
             'prepare_integration.py', 'process_lock_lab.py', 'process_lock_lab-first.py', 'build_package.py',
             'backup_delivery.py', 'precommit.diff', 'staged-paths.json',
             'index-evidence-check.json', 'PLANO.md', 'pyright.json']:
    copy(root / name, Path('reproduction') / name)
copy(base / 'LEIA_PRIMEIRO.md', Path('LEIA_PRIMEIRO.md'))
copy(base / 'INSTRUCOES/PROXIMO_PROMPT_APOS_CONSISTENCIA_LEDGER_2026-09-10.md', Path('PROXIMO_PROMPT.md'))
git('bundle', 'create', str(bundle), '--all')
git('bundle', 'verify', str(bundle))
git('clone', '--bare', str(bundle), str(restore))
assert git('rev-parse', 'HEAD', cwd=restore) == commit
git('fsck', '--full', cwd=restore)
assert git('rev-parse', 'HEAD^{tree}', cwd=restore) == git('rev-parse', 'HEAD^{tree}')
evidence_checks = []
for path in sorted((docs / 'evidence').rglob('*')):
    if path.is_file():
        relative = path.relative_to(repo).as_posix()
        assert git_bytes('show', f'HEAD:{relative}', cwd=restore) == path.read_bytes(), relative
        evidence_checks.append(relative)
expected_evidence = json.loads((root / 'index-evidence-check.json').read_text())['files']
assert sorted(evidence_checks) == sorted(expected_evidence)
copy(bundle, Path('git') / bundle.name)
receipt = dict(
    round='LGC-20260910', verified_at=datetime.now(UTC).isoformat(), commit=commit,
    base=start, branch='main', git_clean=True, pushed=False, deployed=False,
    bundle=dict(path=str(bundle), **digest(bundle)), bare_restore_verified=True,
    restored_tree=git('rev-parse', 'HEAD^{tree}', cwd=restore),
    restored_evidence_bytes_verified=evidence_checks,
    wheel_changed_module_bytes_verified=module_checks, delivery_path=str(out), files=copies,
    scope='code_and_review_checkpoint_only_not_operational_database_restore',
    mandate_complete=False, profitability_established=False)
(out / 'DELIVERY_MANIFEST.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for path in sorted(out.rglob('*')):
        if path.is_file():
            z.write(path, path.relative_to(out).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name in z.namelist():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert z.read(name) == (out / name).read_bytes()
    member_count = len(z.namelist())
receipt['zip'] = dict(path=str(archive), **digest(archive), members_verified=member_count,
                      crc_ok=True, all_bytes_equal=True)
audit.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
assert not git('status', '--porcelain=v1')
print(json.dumps(dict(commit=commit, changed_files=len(changed), zip=receipt['zip'],
                      bundle=receipt['bundle'], audit=str(audit)), ensure_ascii=False))

