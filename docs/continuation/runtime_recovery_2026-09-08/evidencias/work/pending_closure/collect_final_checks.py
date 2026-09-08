"""Assemble final receipts and hashes; does not execute the application or tests."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/pending_closure'
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
ISOLATED = ROOT / 'work/integration-repo'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


sources = {}
for filename in ['python_after.json', 'python_entrypoint_after.json',
                 'DOTNET_FINAL_MANIFEST.json', 'WATCHDOG_FINAL_MANIFEST.json']:
    manifest = read(WORK / filename)
    for entry in manifest['files'] if isinstance(manifest, dict) else manifest:
        sources[entry['path']] = entry['sha256']
sources.update(read(WORK / 'environment_final_hashes.json')['after'])
for name in [
    'dotnet/LineupWorker/Services/LineupStreamConsumer.cs',
    'dotnet/LineupWorker/OperationalSettings.cs',
    'dotnet/LineupWorker.Tests/LineupStreamTests.cs',
    'dotnet/LineupWorker.Tests/RedisEndpointTests.cs',
    'dotnet/LineupWorker.Tests/WorkerRuntimeTests.cs',
    'dotnet/LineupWorker.Tests/KernelCrossProcessTests.cs',
    'brasileirao_scripts/lineup_inbox.py',
    'brasileirao_scripts/hotpath_smoke.py',
    'tests/test_lineup_inbox.py',
    'tests/test_hotpath_smoke.py',
    'tests/test_lineup_inbox_redis.py',
    'contracts/redis-protocol-v2.md',
]:
    sources[name] = sha(REPO / name)
documentation_only = ['contracts/redis-protocol-v2.md']
for name, digest in sources.items():
    assert sha(REPO / name) == digest, name
    if name not in documentation_only:
        assert sha(ISOLATED / name) == digest, 'Isolated copy differs: ' + name

names = [
    'python_ready_unit', 'python_ready_redis_green', 'python_ready_lint',
    'python_ready_format', 'python_ready_pyright', 'python_lineup_inbox_redis',
    'python_lineup_inbox_lint', 'python_lineup_inbox_format',
    'python_entrypoint_green', 'python_entrypoint_lint', 'python_entrypoint_format',
    'dotnet_watchdog_full', 'dotnet_watchdog_warnaserror',
    'pending_actual_hosts_final', 'pending_cross_process_final',
]
receipts = ['work/pending_closure/validation/' + name + '.json' for name in names]
receipts += ['work/validation/' + name + '.json' for name in [
    'pending_inbox_python_unit', 'pending_inbox_lint',
    'pending_inbox_format', 'pending_inbox_pyright',
]]
for relative in receipts:
    receipt = read(ROOT / relative)
    assert receipt['exit_code'] == 0 and receipt['command'], relative
for name, expected in [('python_ready_unit', 139), ('python_ready_redis_green', 24),
                       ('python_lineup_inbox_redis', 3), ('python_entrypoint_green', 3)]:
    assert f'{expected} passed' in (WORK / 'validation' / (name + '.log')).read_text(encoding='utf-8-sig')
assert '15 passed' in (ROOT / 'work/validation/pending_inbox_python_unit.log').read_text(encoding='utf-8-sig')

coverage_path = 'work/integration-repo/artifacts/dotnet-watchdog-full/1e6d51e5-8560-4daf-b9ac-8a5ce915d339/coverage.cobertura.xml'
coverage = ET.parse(ROOT / coverage_path).getroot().attrib
assert (coverage['lines-covered'], coverage['lines-valid'],
        coverage['branches-covered'], coverage['branches-valid']) == ('839', '969', '350', '426')
cross_folder = ROOT / 'work/integration-repo/artifacts/pending-cross-process-final'
trx = next(cross_folder.glob('*.trx'))
counters = ET.parse(trx).find('.//{http://microsoft.com/schemas/VisualStudio/TeamTest/2010}Counters').attrib
assert counters['passed'] == '1' and counters['failed'] == '0' and counters['total'] == '1'

host_receipt = 'work/pending_closure/host_process_evidence_20260908T044044929864/receipt.json'
host = read(ROOT / host_receipt)
assert host['status'] == 'PASS' and host['dbsize_after'] == 0
assert all(c['exit_code'] == c['expected'] for c in host['checks'])
checks = {
    'created_at_utc': datetime.now(UTC).isoformat(),
    'source_sha256': dict(sorted(sources.items())),
    'documentation_only': documentation_only,
    'final_receipts': receipts,
    'coverage_path': coverage_path,
    'host_receipt': host_receipt,
    'artifact_directories': [
        'work/integration-repo/artifacts/dotnet-watchdog-full',
        'work/integration-repo/artifacts/pending-cross-process-final',
    ],
    'validation_counts': {
        'python_unit_passed': 154,
        'python_unit_detail': {'kernel': 139, 'smoke': 12, 'inbox_producer': 3},
        'python_redis_passed': 30,
        'python_redis_detail': {'kernel': 24, 'inbox_producer': 3, 'module_cli': 3},
        'python_entire_suite_rerun': False,
        'dotnet_full_passed': 109,
        'dotnet_full_skipped': 1,
        'dotnet_full_failed': 0,
        'dotnet_cross_process_passed': 1,
        'dotnet_cross_process_skipped': 0,
        'dotnet_cross_process_failed': 0,
        'dotnet_full_skip_executed_separately': True,
        'actual_hosts_checks_passed': len(host['checks']),
        'actual_hosts_smoke_iterations': 2,
        'dotnet_lines_covered': 839,
        'dotnet_lines_valid': 969,
        'dotnet_branches_covered': 350,
        'dotnet_branches_valid': 426,
        'full_compose_build_run_executed': False,
        'remote_ci_executed': False,
    },
    'source_comparison_note': 'Runtime and test copies match. Docker inputs match the isolated config checks; no container build/run is implied. Contract markdown is documentation only.',
}
(WORK / 'final_checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'sources': len(sources), 'receipts': len(receipts),
                  'validation_counts': checks['validation_counts']}, indent=2))
