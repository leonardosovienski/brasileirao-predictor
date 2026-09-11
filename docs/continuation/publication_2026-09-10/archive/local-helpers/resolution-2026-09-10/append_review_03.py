import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
notes = json.loads((root/'semantic-review-notes-02.json').read_text(encoding='utf-8'))
batches = [
(['brasileirao_predictor/research/price_strength/study.py', 'brasileirao_predictor/research/price_strength/dynamic_xg.py',
  'brasileirao_predictor/research/price_strength/economic_search.py', 'brasileirao_predictor/backtest_event.py',
  'brasileirao_predictor/research/market_0b_resolution.py', 'brasileirao_predictor/research/market_edge_ordering.py',
  'brasileirao_predictor/research/survival_test.py', 'brasileirao_predictor/ingest_sofascore.py',
  'brasileirao_predictor/backtest.py', 'brasileirao_predictor/research/season_2026_split.py',
  'brasileirao_predictor/research/sofascore_probe.py'],
 ['study/dynamic_xg explicitly separate exploratory diagnostics from execution; supplied clocks and calibration provenance remain caller assertions. No study executed. economic_search frozen protocol preserved; source read only including reread of previously truncated lines 405-478.',
  'backtest/backtest_event legacy SQL requires final goals and closing coverage, conditions the universe on future availability and cannot prove a historical executable quote. Old main writes operational tables/CSV; not run or modified.',
  'market_0b accepts weak numeric domains and empty supplied power reference falls back to tested data. market_edge_ordering row PSR and caller trial history are not valid promotion evidence. Frozen studies preserved; no new GO decision.',
  'survival_test is legacy inadmissible for new economic promotion: 12x12 labels versus 13x13 default score grid, postmatch player presence/current parameter cache, unsorted closing selection, Kelly scaling missing odds factor, same-event sequential capital, PnL uses base not advertised hybrid, observed-return percentiles called mean CI. Source read only, no model/ledger execution.',
  'Shared ingest_sofascore clock and cardinality ambiguities, missing units normalization and non-atomic multi-table writes cannot be repaired by altering protected collection. Byte-unchanged. season_2026_split is limited metadata roles, not authentic availability.',
  'sofascore_probe is not purely read-only: write-capable db.connect and fixed report/cache paths. No operational invocation.']),
(['brasileirao_scripts/auditoria.py', 'brasileirao_scripts/coverage_report.py', 'brasileirao_scripts/inventario_dados.py',
  'scripts/migration/verify_archive.py', 'tests/test_closeout_coverage.py', 'tests/test_resolution_coverage.py',
  '.gitignore', '.gitattributes', '.github/workflows/ci.yml'],
 ['auditoria.py has import-time operational database reads/training/2026 outcomes; no import or execution. inventario_dados single-price coverage and numeric proxy-closing heuristic cannot authenticate clocks/bookmaker identity; source only.',
  'verify_archive validates member traversal/collisions/links/hash/count and empty destination; immutable source authenticity and global restore are not implied. Partial output retained on failure; no new operational restore.',
  'Coverage gate falsely passed empty/missing required categories, omitted kernel CLI/Redis v2 from kernel category, accepted invalid counts and line-only input, and printed hardcoded .NET rates. Eleven failing regressions reproduced, implementation corrected without reducing 80% gates or 56% evidence ratchet; after-run pending at recording. No current whole-suite or Linux CI success inferred.',
  'Git ignore/attributes and CI configuration read in full; workflow contains separate real .NET Cobertura check. No CI dispatch or remote mutation.'])]
for paths, findings in batches:
    notes['batches'].append(dict(paths=paths, entire_returned_contents_read=True, findings=findings,
        recorded_at=datetime.now(UTC).isoformat(), source_hashes_at_recording={
            p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in paths}))
target = root/'semantic-review-notes-03.json'
assert not target.exists()
target.write_text(json.dumps(notes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
inventory = json.loads((repo/'docs/continuation/reconciliation_2026-09-10/evidence/source-inventory.json').read_text(encoding='utf-8'))
read = {p for b in notes['batches'] for p in b['paths']}
pending = [r for r in inventory if r['review']=='inventory_static_or_targeted_review_only' and r['path'] not in read]
(root/'semantic-pending-03.json').write_text(json.dumps(pending, indent=2), encoding='utf-8')
print('pending', len(pending), 'lines', sum(r.get('lines', 0) for r in pending))
for r in sorted(pending, key=lambda r:(r['path'].startswith('tests/'),r['path'])):
    print(r.get('lines'), r['path'])
