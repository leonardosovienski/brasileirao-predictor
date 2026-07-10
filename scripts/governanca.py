"""Governança do domínio Brasileirão: controle positivo + pré-registro (PASSO 4.2).

Ordem OBRIGATÓRIA (trava de poder do core, v1.1.0):
  1. Harness de controle positivo — prova que o funil O/U + critério de
     avaliação DETECTAM edge sintético (ataque de um time inflado em +30%
     que o mercado não precificou) e REJEITAM ruído (mercado justo + vig).
     Passando, emite data/trials.harness_attestation.json.
  2. Pré-registro das hipóteses em data/trials.json — ANTES de ler qualquer
     resultado do walk-forward:
       H1: O/U 2.5 com janela de valor 2–15% (a única com CLV comprovado na Copa)
       H2: picks de período (1T) com confiança ≥ 60% (informativa — sem odds)
  3. Só então scripts/backtest_walkforward.py produz o veredito, e o DSR
     desconta pelas N tentativas aqui registradas.

O edge sintético usa o MESMO motor de precificação do serving
(model._score_grid + leitura O/U da grade) e o MESMO gatilho do backtest
(edge vs preço na janela [min_edge, max_edge]) — o controle é do pipeline,
não de uma maquete. Placares amostrados da própria grade (numpy, seed fixa).

Uso: python scripts/governanca.py
"""
import statistics as st
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from src import db, model, ratings                                    # noqa: E402
from src.ingest import load_config                                     # noqa: E402
from predictor_core.measurement.stats import probabilistic_sharpe_ratio   # noqa: E402
from predictor_core.measurement.bootstrap import bootstrap_ci          # noqa: E402
from predictor_core.measurement.trials import (                        # noqa: E402
    TrialRegistry, attestation_path_for)
from predictor_core.testing.harness import attest_pipeline_power       # noqa: E402

TRIALS = ROOT / "data" / "trials.json"
SEED = 13
N_GAMES = 800          # jogos sintéticos por braço (≈ 2 temporadas)
INFLATE = 1.30         # ataque do mandante inflado no braço com edge
VIG = 0.05             # overround aplicado ao preço "de mercado"


def _fit_params_pre_teste(cfg, conn):
    """Params calibrados SÓ com o 1º bloco (burn-in) — os mesmos jogos que o
    walk-forward nunca testa. O harness não enxerga a janela de teste."""
    rows = conn.execute(
        "SELECT date, home_team, away_team, home_score, away_score, tournament, neutral "
        "FROM matches WHERE home_score IS NOT NULL ORDER BY date").fetchall()
    block = int(cfg["backtest"].get("walk_forward_window_rounds", 19)) * 10
    burnin = rows[:block]
    if len(burnin) < 100:
        sys.exit(f"burn-in insuficiente ({len(burnin)} jogos) — rode a ingestão antes")
    _, history = ratings.compute_ratings(burnin, cfg["elo"])
    return model.fit_goal_model(history)


def _ou_prob(grid, line, max_goals):
    k = np.arange(max_goals + 1)
    totals = k.reshape(-1, 1) + k.reshape(1, -1)
    return float(grid[totals > line].sum())


def _sample_score(grid, rng, max_goals):
    flat = grid.ravel()
    idx = rng.choice(flat.size, p=flat / flat.sum())
    return divmod(int(idx), max_goals + 1)


def _make_series(params, cfg, *, inflated: bool, seed: int):
    """Série de apostas do funil O/U sobre jogos sintéticos.

    braço edge (inflated=True): placares saem da grade com ataque do mandante
      ×1.30; o MERCADO precifica a grade base + vig; o MODELO conhece a grade
      verdadeira → edge real dentro da janela → retornos devem ser positivos.
    braço ruído (inflated=False): placares saem da grade base; mercado idem +
      vig; modelo = grade base com jitter ±3pp (erro de estimação sem
      informação) → o que passar do gatilho é ruído pagando vig.
    """
    a, b, alpha, rho = params[0], params[1], params[2], params[3]
    bt = cfg["backtest"]
    min_edge, max_edge = float(bt["min_edge"]), float(bt["max_edge"])
    line = float(bt.get("over_under_line", 2.5))
    max_goals = int(cfg["model"]["max_goals"])
    rng = np.random.default_rng(seed)
    returns = []
    for _ in range(N_GAMES):
        diff = float(rng.normal(0.0, 120.0)) / 400.0   # elo diff típico de liga
        lam_h = float(np.exp(a + b * diff))
        lam_a = float(np.exp(a - b * diff))
        grid_base = model._score_grid(lam_h, lam_a, alpha, rho, max_goals)
        p_over_base = _ou_prob(grid_base, line, max_goals)

        if inflated:
            grid_true = model._score_grid(lam_h * INFLATE, lam_a, alpha, rho, max_goals)
            p_model = _ou_prob(grid_true, line, max_goals)
        else:
            grid_true = grid_base
            p_model = min(0.99, max(0.01, p_over_base + float(rng.normal(0, 0.03))))

        # mercado: probabilidade base + vig repartido → odds ofertadas
        for sel, sel_p_model, p_mkt in (("over", p_model, p_over_base),
                                        ("under", 1.0 - p_model, 1.0 - p_over_base)):
            odd = 1.0 / (p_mkt * (1.0 + VIG))
            if odd <= 1.0:
                continue
            edge = sel_p_model - 1.0 / odd
            if not (min_edge < edge <= max_edge):
                continue
            hs, as_ = _sample_score(grid_true, rng, max_goals)
            over_won = (hs + as_) > line
            won = over_won if sel == "over" else not over_won
            returns.append((odd - 1.0) if won else -1.0)
    return returns


def evaluate_funnel(returns):
    """O MESMO critério do GO/NO-GO do walk-forward (sem o DSR, que depende do
    nº de tentativas registradas — aqui o juiz é PSR + IC do bootstrap)."""
    if len(returns) < 30:
        return {"verdict": "REFUTADA", "n": len(returns),
                "motivo": "amostra insuficiente"}
    psr = probabilistic_sharpe_ratio(returns, 0.0)
    lo, hi, _ = bootstrap_ci(returns, st.mean, scheme="iid",
                             n_boot=2000, seed=SEED)
    ok = psr >= 0.80 and lo is not None and lo > 0
    return {"verdict": "COMPROVADA" if ok else "REFUTADA",
            "n": len(returns), "psr": round(psr, 4),
            "ic95": [round(lo, 4), round(hi, 4)] if lo is not None else None}


def main():
    cfg = load_config()
    conn = db.connect(str(ROOT / cfg["database"]), read_only=True)
    params = _fit_params_pre_teste(cfg, conn)
    print(f"params (burn-in): a={params[0]:.4f} b={params[1]:.4f} "
          f"alpha={params[2]:.4f} rho={params[3]:.4f}")

    # 1) controle positivo → atestado
    att = attestation_path_for(TRIALS)
    record = attest_pipeline_power(
        evaluate_funnel,
        lambda: _make_series(params, cfg, inflated=True, seed=SEED),
        lambda: _make_series(params, cfg, inflated=False, seed=SEED + 1),
        attestation_path=att,
        note=f"funil O/U {cfg['backtest']['min_edge']:.0%}-"
             f"{cfg['backtest']['max_edge']:.0%}; ataque mandante ×{INFLATE}; "
             f"vig {VIG:.0%}; {N_GAMES} jogos sintéticos/braço; seed {SEED}")
    print(f"controle positivo OK — atestado em {att.name} ({record['passed_at']})")

    # 2) pré-registro das hipóteses (sharpe=None: resultado ainda não existe)
    reg = TrialRegistry(TRIALS)
    reg.register(
        "h1-ou25-edge-2-15-walkforward",
        params={"market": "ou25", "min_edge": 0.02, "max_edge": 0.15,
                "stake": "fixo-1u", "params_mode": "walk_forward",
                "walk_forward_window_rounds":
                    cfg["backtest"].get("walk_forward_window_rounds", 19),
                "league": "Brasileirão Série A", "seasons": ["2024", "2025"]},
        sharpe=None,
        notes="H1: mesma hipótese da Copa (única com CLV comprovado lá: "
              "+16,11% na população open). GO exige PSR≥0.80, IC_lower>0, "
              "DSR≥0.95 no walk-forward 2024-2025.",
        test_period=["2024-01-01", "2025-12-31"])
    reg.register(
        "h2-periodo-1t-conf60",
        params={"market": "ou_1T", "lines": [1.5, 2.5], "min_conf": 0.60,
                "fracao": "ht_goal_fraction forward-only",
                "league": "Brasileirão Série A", "seasons": ["2024", "2025"]},
        sharpe=None,
        notes="H2: picks de período 1T com prob≥60% — INFORMATIVA (sem odds "
              "de período na base → sem ROI/CLV). Valida se acerto real ≥ 60%.",
        test_period=["2024-01-01", "2025-12-31"])
    errs = reg.validate()
    if errs:
        sys.exit("schema de trials violado: " + "; ".join(errs))
    print(f"pré-registro OK — {len(reg.load())} tentativa(s) em {TRIALS.name}")
    for t in reg.load():
        print(f"  - {t['name']} (registrada em {t['registered_at']})")


if __name__ == "__main__":
    main()
