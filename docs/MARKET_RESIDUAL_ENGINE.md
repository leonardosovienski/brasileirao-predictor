# Market residual engine

> **Estado em 2026-08-22:** o motor binário descrito abaixo continua sendo
> infraestrutura de pesquisa. O candidato multinomial 1X2 MARKET-02 foi
> implementado separadamente e deu **NO-GO** na validação 2024 (`n=340`):
> delta RPS +0,002135, IC95 [+0,000588,+0,003649]. Não foi promovido. Protocolo
> e resultado: `docs/experiments/MARKET_02_1X2_PROTOCOL.md` e
> `reports/market02_1x2_validation_2024.json`.

## Objective

The candidate does not attempt to replace the betting market. It treats each
bookmaker's complete market as a noisy probability estimate, removes the
overround, builds a robust consensus and learns only a regularized correction
from information available before kickoff.

This is a research candidate. Every artifact contains `capital_enabled=false`.
No gate or command in this implementation can place a real bet.

## Data flow

1. `brasileirao_scripts/collect_market_research.py` archives featured odds from multiple
   named bookmakers. `--first-half` additionally queries event-scoped
   `totals_h1`; `--lineup-fixture` archives an API-Football lineup vintage.
2. `brasileirao_predictor.research.residual_dataset` creates rows at a fixed horizon. Quotes
   observed after the cutoff, incomplete books and unmatched results are
   excluded.
3. `brasileirao_predictor.research.market_residual` fits logistic residuals with the market
   log-odds as an offset and L2 regularization.
4. `brasileirao_predictor.research.residual_walkforward` uses only results settled before the
   next prediction time.
5. `brasileirao_predictor.research.economic_decision` selects a shadow quote only when the lower
   probability bound clears the configured economic margin.
6. `brasileirao_predictor.research.residual_gate` requires sample size, positive ROI and CLV
   confidence bounds, PSR and externally computed DSR. Passing produces
   `GO_CANDIDATE`, not permission to deploy capital.

## Features

- dispersion of no-vig probabilities across complete books;
- number of contributing books;
- time remaining to kickoff;
- lineup completeness and starter changes;
- point-in-time xG form difference;
- rest-days difference.

Missing lineup/context values are explicit neutral baselines. They must never
be backfilled from information published after the prediction time.

## Commands

```bash
uv run python -m brasileirao_scripts.collect_market_research
uv run python -m brasileirao_scripts.collect_market_research --first-half
uv run python -m brasileirao_scripts.collect_market_research --lineup-fixture 123456
uv run python -m brasileirao_scripts.evaluate_market_residual --minimum-train 200 --block-size 50
```

API-Football lineups may be unavailable before kickoff for some fixtures. Such
rows retain `published_at_untrusted` until the provider supplies a trustworthy
source update timestamp. They cannot support a causal lineup claim while that
flag remains unresolved.

## Promotion requirements

- a charter and hypothesis registered before inspecting OOS economics;
- stable bookmaker coverage and named executable prices;
- at least 200 independent settled candidate bets or a stronger power-derived
  floor;
- positive lower 95% confidence bounds for ROI and CLV;
- PSR >= 0.80 and DSR >= 0.95 including every attempted configuration;
- no source in quarantine and no point-in-time violation;
- explicit human decision in a separate change to capital policy.
