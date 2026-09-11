"""Append the explicitly read source batches, never infer reading from hashes."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
source = root/'semantic-review-notes-expanded.json'
notes = json.loads(source.read_text(encoding='utf-8'))
batches = [
(['brasileirao_predictor/backup_restore.py', 'brasileirao_predictor/kernel_daemon.py',
  'brasileirao_predictor/kernel_cli.py', 'brasileirao_predictor/kernel_redis_v2.py',
  'dotnet/LineupWorker/Services/KernelRedisProtocolV2.cs', 'dotnet/LineupWorker/Services/MarketStateEngine.cs',
  'tests/test_kernel_runtime.py', 'tests/test_kernel_v2_runtime.py', 'tests/test_kernel_cli_redis.py',
  'tests/test_resolution_kernel_lifecycle.py', 'tests/test_resolution_restore.py', 'pyproject.toml', 'compose.yaml'],
 ['Full kernel lifecycle, Lua protocol and final MSE tail read. Redis standalone fencing uses exact stored payload/state, server TTL, durable pending/ready/outbox and ownership tokens. Not a Redis Cluster or actual execution contract.',
  'Kernel lifecycle regressions reproduced heavy numeric import for healthcheck and 128 simultaneous pubsub handlers against bound 32. Lightweight entrypoint and bounded wakeups implemented; durable recovery remains authoritative. 32 lifecycle/numeric/core tests passed, followed by one extra failure/secret-safe health case.',
  'Three extra backup regressions reproduced percent-URI decoding, destination recursion and source-link validation after copying. URI encoding/source link and junction checks/overlap checks corrected; 11 restore tests pass after correcting the test guard URI parser. Initial guard failure is preserved.',
  'MSE market recheck follows awaited reads and outgoing signal carries model/market identities. Local recheck is not exchange-level atomic availability or accepted fill. 160 installed-package .NET tests passed before latest Python CLI/numeric changes.',
  'The first attempted preservation copy of the old isolation runner completed after its edit; run_isolated_before_uri_guard.py is therefore not a pre-edit byte snapshot. Tool history records the actual previous code. Never use that misnamed copy to establish before-source hash.']),
(['brasileirao_predictor/data/promotions.py', 'brasileirao_predictor/elo_baseline.py',
  'brasileirao_predictor/sofascore.py', 'brasileirao_predictor/ingest_fbref.py',
  'brasileirao_predictor/diagnose_event_data.py', 'brasileirao_scripts/ingest_api_football_history.py',
  'tests/test_promotions_dataset.py', 'tests/test_resolution_promotions.py', 'tests/test_shared_dependencies.py'],
 ['Promotion/relegation validation accepted extra clubs with repeated positions, fractional positions and null identities; relegations also accepted duplicate teams. Seven failing cases corrected; ten synthetic/empty-file checks passed. Two dataset-reading tests were source-reviewed only, never run.',
  'Code-name search found promotion loaders only in promoted cold-start and residual diagnostic research scripts, not protected collectors. No operational data or scheduler was invoked.',
  'Elo baseline guard excludes same kickoff but does not certify result availability before the decision. It remains a legacy diagnostic, not a prospective availability contract.',
  'Sofascore legacy comments overstate immutability of completed data; mutable cache lacks immutable receipt/status history and optional insecure TLS/bypass-oriented commentary are not authorized usage. Shared collector remains unchanged and was not called.',
  'FBref legacy cache never refreshes by version/receipt, parser coerces counts and can accept infinity; its live importer is outside current PIT admission. No collection or downstream shared data write was made.',
  'diagnose_event_data reads operational joins/results even in read-only SQLite mode; it was only source-reviewed. API-Football history wrapper creates write-capable production connection and has no self-contained quota guard; never executed.',
  'Shared dependency tests include a subprocess runner test; cannot run wholesale under the no-subprocess guard. Installed versions and hashes are separately verified, not inferred from declarations.']),
(['brasileirao_predictor/research/score_metrics.py', 'brasileirao_predictor/research/rho_stability.py',
  'brasileirao_predictor/research/price_strength_reliability.py', 'brasileirao_predictor/research/structural_edge.py',
  'tests/test_structural_edge.py', 'tests/test_resolution_structural_edge.py',
  'brasileirao_predictor/research/contextual_ensemble.py', 'brasileirao_predictor/research/promoted_cold_start.py',
  'brasileirao_predictor/research/vorp_ridge.py', 'brasileirao_scripts/evaluate_promoted_cold_start.py'],
 ['Structural detector accepted stale soft-book offers, invalid policies, mutable validated odds and nonfinite lines; power method fixed bracket 20 rejected valid high-margin odds. Eight genuine regressions corrected; all 18 detector tests passed. Its legacy clock/completeness contract is not equivalent to quotes.py admission.',
  'Reliability fit is a clearly scoped pure convex Brier minimizer. It validates finite probability vectors and labels; callers own chronology/identity. No out-of-sample or economic improvement is implied.',
  'Score metrics assume valid matching arrays; DM-HLN computes squared-error differential, not arbitrary logloss differential. Input shape/horizon domains are not independently certified by this API.',
  'Rho split can bisect a kickoff group; its block sampler truncates rows rather than whole selected groups. Contextual ensemble groups unnormalized local dates, has no decision/label-availability contract, coerces outcomes and imputes all-missing columns to zero. Neither supports its broad leakage-safe claim as a new economic validator.',
  'Promoted cold-start entry provenance is a constructed string, not an authenticated PIT rating receipt; first-match ordering is season/match ordinal without availability clocks. The CLI would read real first_matches and overwrite a frozen report, so was not run.',
  'VORP ridge fits associations, not identified causal effects. Full-cache position lookup, player names, absent-team sign fallback, postmatch presence and negative replacement times 0.8 prevent treating old artifact as authenticated causal value. Existing historical artifact/results and model equations are preserved; no training/holdout evaluation occurred.']),
(['brasileirao_predictor/research/price_strength/historical_admission.py',
  'brasileirao_predictor/research/price_strength/live_capture_admission.py',
  'brasileirao_predictor/research/price_strength/capture_decision.py',
  'brasileirao_predictor/research/price_strength/closing_scenario.py',
  'brasileirao_predictor/research/price_strength/price_hurdle.py',
  'brasileirao_predictor/research/price_strength/demo.py'],
 ['Historical admission is explicitly Jan-Jun 2026 metadata/price-state diagnostics, not historical availability. Live audit checks parent status, identities, received clocks and returns execution false. These shared future-capture consumers remain byte-unchanged.',
  'Capture adapter requires all relevant saved/failed receipts, chooses latest before cutoff and rejects ambiguous clocks/states instead of fallback. Normalized clocks all mean the same local API receipt, explicitly declared. No labels/orders/credentials are read.',
  'Closing scenario freezes price-only choices before settlement, retains missing prices/pending labels and locks capital by day under declared hypothetical costs. It is a frozen 2025 scenario, not bookmaker acceptance.',
  'Price hurdle algebra explicitly compares the same aggregate diagnostically and keeps every missing-price event. It cannot recover bookmaker clocks or true probabilities; total business PnL remains unknown.',
  'Demo inputs are manufactured 2030 fixtures explicitly marked synthetic. They may exercise software but cannot provide economic evidence.'])]
for paths, findings in batches:
    notes['batches'].append(dict(paths=paths, entire_returned_contents_read=True, findings=findings,
                                recorded_at=datetime.now(UTC).isoformat(),
                                source_hashes_at_recording={p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in paths}))
target=root/'semantic-review-notes-02.json'
assert not target.exists()
target.write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(explicit_paths=len({p for b in notes['batches'] for p in b['paths']}))))
