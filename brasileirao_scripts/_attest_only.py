"""Renovacao isolada do harness attestation (etapa 1 de governanca.py, sem
a etapa 2 de pre-registro). Uso: python brasileirao_scripts/_attest_only.py

Este arquivo diz de si mesmo, desde que foi criado, que nao faz parte do repo
canonico e que devia ser apagado depois de rodar -- e continua versionado. A
auditoria adversarial de 2026-09-05 registrou isso. Ele NAO foi apagado agora
de proposito: o atestado vigente em data/trials.harness_attestation.json foi
emitido a partir de arvore suja (achado 7) e expira em 2026-09-09, e esta e a
ferramenta que reemite. Precisa da matches.db real, entao so roda na maquina do
mantenedor.

Apague depois da reemissao, ou promova a etapa a governanca.py e apague de vez.
Ver docs/AUDITORIA_ADVERSARIAL_2026-09-05.md, adendo de 2026-09-06."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.measurement.trials import attestation_path_for  # noqa: E402
from predictor_core.testing.harness import attest_pipeline_power  # noqa: E402

from brasileirao_predictor import db  # noqa: E402
from brasileirao_predictor.ingest import load_config  # noqa: E402
from brasileirao_scripts.governanca import (  # noqa: E402
    SEED,
    TRIALS,
    _fit_params_pre_teste,
    _make_series,
    evaluate_funnel,
)

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
