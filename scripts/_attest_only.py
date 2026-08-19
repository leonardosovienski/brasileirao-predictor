"""Renovacao isolada do harness attestation (etapa 1 de governanca.py, sem
a etapa 2 de pre-registro). Uso: python scripts/_attest_only.py
Apague este arquivo depois de rodar; nao faz parte do repo canonico."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.measurement.trials import attestation_path_for  # noqa: E402
from predictor_core.testing.harness import attest_pipeline_power  # noqa: E402

from scripts.governanca import SEED, TRIALS, _fit_params_pre_teste, _make_series, evaluate_funnel  # noqa: E402
from src import db  # noqa: E402
from src.ingest import load_config  # noqa: E402

cfg = load_config()
conn = db.connect(str(ROOT / "data" / "matches.db"), read_only=True)
params = _fit_params_pre_teste(cfg, conn)
print(f"params (burn-in): a={params[0]:.4f} b={params[1]:.4f} alpha={params[2]:.4f} rho={params[3]:.4f}")

att = attestation_path_for(TRIALS)
record = attest_pipeline_power(
    evaluate_funnel,
    lambda: _make_series(params, cfg, inflated=True, seed=SEED),
    lambda: _make_series(params, cfg, inflated=False, seed=SEED + 1),
    attestation_path=att,
    note=(f"funil O/U {cfg['backtest']['min_edge']:.0%}-{cfg['backtest']['max_edge']:.0%}; renovacao core 2.3.0"),
    metric="psr",
)
print(f"controle positivo OK - atestado em {att} ({record['passed_at']})")
