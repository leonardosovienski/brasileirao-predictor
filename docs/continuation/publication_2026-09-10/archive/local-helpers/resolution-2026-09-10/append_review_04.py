import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
notes = json.loads((root/'semantic-review-notes-03.json').read_text(encoding='utf-8'))
names = '''backfill_bookmaker_smokes.py backtest_close.py bootstrap_calibration_window.py calib_empate.py calib_ou.py
capture_sofascore_event.py ci_check.py compare_hypothesis_errors.py confound.py cosh_free.py diag_zebra.py elasticidade.py
eval_walkforward.py exp001_coverage_audit.py exp001_data_pilot.py exp_a_calib.py exp_f_rho.py experimentos_causa.py
export_version_losses.py gen_teams_json.py hotpath_smoke.py backtest_walkforward.py benchmark_predictor.py
h10_fadiga_walkforward.py h4_verdict_bootstrap.py import_ou25_historical_backfill.py install_closing_snapshot_task.ps1
install_windows_scheduler.ps1 investigate_calibration_window.py investigate_half_life.py maher.py maher_verif.py
monitor_h8_gate.py p1_cost_probe.py odds_shop.py'''.split()
paths = ['brasileirao_scripts/'+p for p in names] + [
    'brasileirao_predictor/research/test_combinations.py', 'brasileirao_predictor/research/verify_calibration.py',
    'tests/test_odds_shop_stale.py', 'tests/test_resolution_historical_import.py', 'tests/test_resolution_odds_shop.py']
notes['batches'].append(dict(paths=paths, entire_returned_contents_read=True, recorded_at=datetime.now(UTC).isoformat(),
 source_hashes_at_recording={p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in paths}, findings=[
 'All listed source returned/read in full. benchmark tail was collected from session 5891; compare_hypothesis_errors and cosh_free continuations from 62899/29306. An earlier parallel read emitted empty outputs and was not counted; those sources were fetched again.',
 'coverage-after: 20 tests passed (12 coverage plus 8 detector); Ruff/format/Pyright all passed on 33 changed Python files. This predates historical importer and odds display changes.',
 'backfill_bookmaker_smokes appends shared prospective data/ledger and calls collected timestamps published_at; no execution. capture_sofascore_event takes clock before multiple network requests, makes PIT/pre-match claims without end receipt, weak lineup status/identity and append dedup not under a writer lock. Shared collectors preserved; standalone immutable lineup envelopes supersede admission for new research.',
 'Several old scripts execute config/DB/training at import: bootstrap_calibration_window, calib_empate/OU, confound, cosh_free, elasticidade, eval_walkforward, exp_a_calib, exp_f_rho, experimentos_causa, investigate windows/half-life, maher/verif. Source review only. Training to June 2026 overlaps declared 2024-2026 holdouts in calib_empate/cosh_free/exp_a_calib; Maher compares with parameters fitted through that holdout. Frozen reports cannot establish independent validation.',
 'eval_walkforward pairs Brier but compares model full-universe logloss/accuracy with market subset. diag_zebra explicitly in-sample but uses current parameter cache. elasticidade final never changes total statement contradicts its own cosh formula. Experimentos causal/no-vig perfect-probability wording is only a scenario assumption, not causal identification.',
 'backtest_close patches two imported settlement namespaces at import and omits connection close. backtest_walkforward conditions price rows on historical closing, has row PSR and inherited DSR registry; half-time sample assumes jointly present valid HT, block count includes skipped blocks. No ledger/trial was touched.',
 'benchmark has named diagnostic-only aggregate, baseline warmup fix and paired losses, but misleading coverage=1 denominator excludes burn-in/absentions, by_team only home, calendar return-leg inference cannot resolve postponed rounds, naive kickoff assumes host timezone, SQL join can duplicate event identity. H9 engine/shared evaluator remains preserved, not executed.',
 'compare_hypothesis_errors silently overwrites duplicate event IDs and trusts caller probabilities/losses; moving blocks of selected strata are row adjacency, not a time-block certificate. H4 bootstrap selects a sweep winner and uses iid numpy global RNG bootstrap without multiplicity; H10 rest omits other competitions and labels insufficient evidence refuted; no attestations renewed.',
 'EXP001 clients are old metered scripts without complete quota/reserve planning or raw receipt preservation, naive timezone and weak numeric prices. Coverage resume does not bind raw source/fixture universe. No API call made. gen_teams_json chooses first 2026 competition, accepts duplicate aliases and writes incomplete list before warning; not executed or collector-modified.',
 'hotpath_smoke validates current registered v2 payload/result without refreshing TTL; its timing is verification, not compute. Redis socket timeout not explicit. P1 cost probe synthetic-only, no operational reads; comparison defaults may differ and claims require actual measured run. Not run this segment.',
 'Scheduler files are contracts only: installing would replace/start protected H9/H14/H15 jobs and shared cache refresh. No scheduler action, claim or attestation change. File presence is not evidence of active installation.',
 'Historical importer seven failing regressions reproduced: output could target an existing/operational DB, bad prices/counts admitted, partial failure published. New-path-only atomic publication, complete SQLite integrity, snapshot hash tied to parsed CSV bytes, strict finite price/integer count, quarantine and finally close implemented. First after-run exposed Windows fsync read-only descriptor bug; fixed with writable own temporary descriptor. All 8 tests passed in historical-import-after-02; no real data import.',
 'odds_shop source has stale/unknown-clock acceptance, duplicate/incomplete consensus, unvalidated model/recommendation and copy-paste bet command, sensitive raw exception display and import-time config. Consumer-name search found only standalone module, CI mentions, bet_log comment and tests; no protected collector import. Tests pending at recording. Source/display fixes planned, no network/data invocation.',
 'verify_calibration and test_combinations require nonmissing features but not finite or common units; train/test split may bisect same date, labels/results coverage selection, no model decision/receipt clocks. Combination of xG and counts by mean is dimensionally unspecified. Existing retrospective candidate selection does not become an out-of-sample gain.'
 ]))
target=root/'semantic-review-notes-04.json'
assert not target.exists()
target.write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
inventory=json.loads((repo/'docs/continuation/reconciliation_2026-09-10/evidence/source-inventory.json').read_text(encoding='utf-8'))
read={p for b in notes['batches'] for p in b['paths']}
pending=[r for r in inventory if r['review']=='inventory_static_or_targeted_review_only' and r['path'] not in read]
(root/'semantic-pending-04.json').write_text(json.dumps(pending,indent=2),encoding='utf-8')
print('pending',len(pending),'lines',sum(r.get('lines',0) for r in pending))
