# BR-CAIN-MAIN-20260912 — validation and consolidation

The current mandate authorizes technical corrections and publication, not production operation, bets, or economic claims. Work uses clean isolated checkouts and new databases. Historical evidence and protected hypotheses are preserved.

## Predefined acceptance
The three documented CLAIM-BR-MARKET-001/002/003 must retain BLOCKED_PENDING_PIT_FEATURES, their H-24h/H-6h/H-1h wording, all table columns, source hashes and revision, and null scientific clocks through export, canonical contract validation, scoped CAIN ingestion, persistence, CLI/API retrieval and factual Historian context. Duplicate import is idempotent; invalid schema, missing required metadata, conflicting identity, corruption, unapproved input and revocation cannot become admitted content. Received source bytes must be recoverable offline. This is real versioned documentary input through isolated implementations, not production database validation, predictive evaluation or LLM precision.

Source contracts: docs/EVIDENCE_REGISTRY.md; both tools/export_cain_*.py; ecosystem packages/research-bundle and research-snapshot; CAIN research services, CLI/API and ADR 0020.

CAIN revision: 5ba4177a11b9312900e5035517aa5ef25d509859. Ecosystem revision: a9f6594c840482419d6c310f373813e0e71f17d0, published feature/research-bundle-v1 (its main does not yet contain BundleV1). All installed bundle .py/.json files match this ecosystem source byte-for-byte; CAIN vendors Snapshot 1.0.0 and Bundle 1.0.0. No modification or branch consolidation of those repositories is required for this combination.

## Findings and expectation corrections
- Result recording silently converted True to 1, False to 0, 1.9 to 1 and -0.5 to 0. Scores are goal counts, consistent with strict live settlement's existing score validation. New tests fail before correction; shared score validation now rejects invalid input before any write. Explicit prediction identity stays fail-closed; typing now proves non-null association.
- Main CI downloaded Core 3.2.0/Ops 4.1.0 while pyproject, uv.lock, Dockerfiles and hash manifest require 3.2.1/4.2.0. Regression failed before correction. URLs and output filenames now match the existing canonical pins; no hash control removed.
- Three shared-dependency test expectations still described superseded release artifacts. Updated to the already published pinned assets, independently exercised by the hash-locked clean installation.
- Old PIT fixture invented a three-column schema. The current producer requires source/source_match_id and preserves revisions (test_resolution_curated_versions.py). The fixture now goes through connect_curated/curate_match and checks before/inside/after temporal boundaries, retaining the original UTC assertion.
- Old invalid-date test accepted arbitrary event selection despite supplying an unusable date. That contradicts event identity and the test module's own wrong-match risk. It now requires rejection and does not change the stricter product behavior.
- CAIN query_id is a per-invocation uuid4 receipt (research/service.py); comparing it for equality across interfaces was a test-harness error. The acceptance compares every content field except that receipt ID. No source identifier or clock is ignored.
- Bundle approval reserves manifest semantics and explicitly reads no objects (BundleService.approve). Corruption is tested on first ingestion of a new manifest identity, not a duplicate whose previously stored objects remain verified. This corrected the test boundary using the documented independent contract.
- The existing RPS power attestation names Core 3.2.0. This is a real gate mismatch, not an expectation to relax. Any renewal must execute both synthetic controls, preserve the prior receipt and identify clean code; it cannot establish predictive/economic validity or authorize operational execution.

## Branch preservation
All original Brasileirão branches are ancestors of 5efb4716d4805e37e0aa09b09dcdc52022cae039: main local c0ae0113fadbac2f1f348463422d4550718498f0; remote main 24bdb9d0403071f38cba087b16768f105b9964d7; integration/cain-status-20260911 78cbe4dc2d02b1670149204e939ae2bd6e93ddac; publication-validation-architecture-20260911 5efb4716d4805e37e0aa09b09dcdc52022cae039. No exclusive divergent contribution is discarded. Backups at C:/BRASILEIRAO/BACKUPS/integration-main-20260912 include complete Git bundle, restored mirror checked with fsck and exact refs, raw index checked against restored objects, and 59 ignored local files restored with SHA256 comparison. Original working tree clean, no stashes/untracked nonignored files, LFS attributes or submodules. External historical archives remain in place and are not included in this backup. No branches may be deleted before final publication and acceptance checks.

## Reproduce
Use Windows Git core.longpaths=true for clean checkout (archived evidence paths exceed legacy MAX_PATH). Python 3.13/3.14 and uv: `uv sync --locked --all-extras`; `uv build`; `uv run ruff check brasileirao_predictor brasileirao_scripts tests`; `uv run ruff format --check brasileirao_predictor brasileirao_scripts tests`; `uv run pyright brasileirao_predictor`. Run the reviewed suite via `.venv/Scripts/python.exe -I -B tools/publication_validation/run.py NEW_SIBLING_OUTPUT`. On Linux use `.venv/bin/python`.

Install CAIN at the pinned revision into a separate venv using its vendor wheels: `python -m pip install --find-links CAIN/vendor "CAIN[dev]"`. Then use that installed Python for `tools/integration_validation/run.py PRODUCER_CHECKOUT NEW_OUTPUT`. Output must be outside the producer checkout and under its parent. This creates isolated policy/DB/object stores and imports only the committed public evidence registry. Run each case into a new directory. No production credentials or LLM are needed.

Local evidence root: C:/BRASILEIRAO/work/integration-main-20260912. It preserves commands, failed attempts, corrected harness boundary explanations, baseline and final results. Final publication/CI status must be recorded after checking the actual delivered SHA; the existence of this document is not an approval.

## RPS technical gate renewal
Executed both existing synthetic controls without real match data, at clean code 18d7ce212f7c659356019e72d21e8ee7f86fd989 under Core 3.2.1. Prior receipt preserved byte-for-byte in docs/history/attestations/trials-core-3.2.0-before-20260912.json. New receipt retains the existing pipeline fingerprint and control definitions, has a fresh seven-day validity, and does not change trials.json/trials.v2.json, hypotheses, predictions or economic decisions. No operational task was started. This restores the technical prerequisite; it is not authorization to run an experiment or production operation.


## Completed acceptance and publication

The canonical main was delivered at abdd965c98c228d73ae416944eb7531bed9ab197. All three workflows (34726769988, 34726770019, 34726770025) and 12 jobs succeeded. The real documentary scenario was repeated at that published SHA with PASS; original bytes, three claims, CLI/API content and offline recovery were verified. Both obsolete branches were deleted locally/remotely using expected-SHA transactions after backup restoration. Only main remained in the canonical checkout and remote at 2026-09-13T00:11:00Z.

Local report and 134-entry evidence archive: C:/BRASILEIRAO/ENTREGAS/integration-main-20260912. Backup: C:/BRASILEIRAO/BACKUPS/integration-main-20260912. Later documentation commits do not replace the runtime acceptance SHA or extend validation to newer CAIN versions.

The ecosystem contract revision a9f6594 is now an ancestor of its main, observed at 73111a1d13adfa09dd4928cae3b75ae28e4ea7e6. The original pinned combination above remains the provenance of the executed case. Current cross-project continuity: [Brasileirão integration record](https://github.com/leonardosovienski/ecosystem-predictor/blob/main/BRASILEIRAO_INTEGRATION_20260912.md).
