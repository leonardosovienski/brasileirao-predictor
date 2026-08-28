# Promoted cold-start protocol

Status: `BLOCKED_MISSING_PROMOTION_METADATA`. Serving remains unchanged.

The experiment must use canonical team ids and explicit promotion provenance.
For each validation season, every empirical prior is derived only from strictly
earlier seasons. Fixed values such as Elo 1420, attack 0.88 or defense 1.15 are
not admissible without this derivation. Primary evaluation is paired RPS over
the first eight league matches; global log loss and multiclass Brier are
guardrails. The neutral 1500 prior is the incumbent. No result may be promoted
from 2025 because that season is no longer a blind holdout.
