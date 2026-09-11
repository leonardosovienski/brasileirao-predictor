"""Record only explicitly read batches; hashes do not advance review depth."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
inventory=json.loads((repo/'docs/continuation/reconciliation_2026-09-10/evidence/source-inventory.json').read_text(encoding='utf-8'))
notes=json.loads((root/'semantic-review-notes.json').read_text(encoding='utf-8'))
notes['batches'][0]['paths']=[row['path'] for row in inventory if row['review']=='inventory_static_or_targeted_review_only' and row.get('lines',10**9)<=30]
notes['batches'].append(dict(
    paths=[row['path'] for row in inventory if row['review']=='inventory_static_or_targeted_review_only' and 30<row.get('lines',0)<=55
           and 'renew_core3_harness' not in row['path'] and 'install_closing_snapshot_task' not in row['path']],
    entire_returned_contents_read=True,
    findings=[
      'The truncated ingest_typing_boundaries/logic_registry portion was fetched separately and read completely.',
      'Harness/promotion/telemetry/CI containment tests access referenced real or protected data/source; they are source-reviewed only, not added to the execution allowlist.',
      'Player statistics test encoded a postmatch availability at kickoff. Seven regressions reproduced backdating, zero imputation, invalid counts and silent corruption. Standalone importer corrected, eight tests pass, no operational backfill run.',
      'Temporal policy tests distinguish UTC-normalized kickoff groups and conservative date fallback; simulator tests cover its generic tournament machinery, not implementation of league simulation.',
      'Redis endpoint tests preserve ACL/TLS/database and reject ambiguity without leaking credentials. Runtime tests use explicit disposable identifiers.',
      'Legacy evaluation wrappers have fixed default output paths and historical input assumptions; do not execute or overwrite their frozen reports. Conditional residual successor has stronger input/replay contracts.',
      'API-Football history wrapper still uses operational connection without read_only and performs quota-sensitive network work; not executed. Required safe invocation/source isolation remains in the historical recovery boundary.',
      'Repository hygiene tests need read-only Git subprocess access, so they cannot run under the generic no-subprocess test guard unchanged.'
    ]))
notes['batches'].append(dict(paths=['brasileirao_predictor/kernel_daemon.py','brasileirao_scripts/backfill_player_comp_stats_from_sofascore.py',
    'tools/runtime_lab/lab_guard.py','tools/runtime_lab/kernel_synthetic.py','tests/test_resolution_kernel_params.py','tests/test_resolution_player_stats.py'],
    entire_returned_contents_read=True,findings=[
      'Kernel preserves durable request identity, leases, late-result fences and reconnect recovery; source parameters still come from the legacy shared learned-state cache. This is not authenticated model provenance.',
      'Grid dimensions below one can reach unchecked native low-score cell writes. Eight synthetic guarded regressions failed before correction, without executing unsafe JIT dimensions. New numeric validation precedes warmup and session startup.',
      'Kernel performance claims in old comments are expectations, not current measured guarantees. Health CLI imports numeric dependencies and pubsub dispatch is not yet explicitly bounded; review these separately.',
      'Explicit lab_guard import in synthetic bootstrap replaces CI environment path injection; full installed-package cross-process suite passed 160 tests with no PYTHONPATH.',
      'Player importer is standalone: source/code search found only its test as importer; versioned job manifest does not reference it. Existing data and shared collector dependencies were not modified.'
    ]))
for batch in notes['batches']:
    batch['source_hashes_at_recording']={p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in batch['paths']}
(root/'semantic-review-notes-expanded.json').write_text(json.dumps(notes,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
reviewed=set(p for batch in notes['batches'] for p in batch['paths'])
print(json.dumps(dict(explicit_paths=len(reviewed),previous_static_now_read=sum(row['path'] in reviewed and row['review']=='inventory_static_or_targeted_review_only' for row in inventory))))
