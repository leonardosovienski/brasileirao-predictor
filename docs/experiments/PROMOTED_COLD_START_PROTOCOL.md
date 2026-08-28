# Promoted cold-start protocol

Status: `BLOCKED_DATA_ENTRY_RATINGS_AND_FIRST_MATCHES`. Serving remains unchanged.

The experiment must use canonical team ids, complete Serie A participation
history, point-in-time entry ratings and explicit promotion provenance. For
each validation season, every empirical prior is derived only from strictly
earlier seasons. Fixed values such as Elo 1420, attack 0.88 or defense 1.15 are
not admissible without this derivation. Primary evaluation is paired RPS over
the first ten league matches, comparing neutral Elo 1500 against empirical
prior plus dynamic K; global log loss and multiclass Brier are guardrails. No
result may be promoted from 2025 because that season is no longer a blind
holdout.
