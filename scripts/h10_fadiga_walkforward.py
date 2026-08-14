"""h10_fadiga_walkforward — H10: descanso (dias desde o último jogo) melhora
o modelo de gols do Brasileirão?

Substitui `scripts/poc_fadiga.py` (herdado do wc-predictor-v2, vestigial:
lia `matches` com faixas de data 2010-2023/2024-2026 que só fazem sentido
pro `matches` internacional pré-adaptação — hoje essa tabela é o espelho do
Sofascore só com jogos do Brasileirão, então aquele split de datas não
corresponde a nenhum jogo real). Este script roda no domínio certo, com
governança de verdade: walk-forward por blocos de rodadas (o MESMO padrão de
`scripts/backtest_walkforward.py`/H1, não um split único treino/holdout) e
veredito por bootstrap pareado (o MESMO padrão de `scripts/run_h4_sweep.py`).

Mecanismo: `model.fit_goal_model` já aceita um covariável genérico via
`delta_xg` (o nome é herdado do uso com xG, mas o mecanismo é agnóstico —
MLE de um único parâmetro theta que escala λ_casa para cima e λ_visitante
para baixo pelo mesmo diferencial). Aqui o covariável é o diferencial de
descanso: dias-desde-o-último-jogo do mandante MENOS o do visitante, capado
em ±CAP dias (recuperação satura — descansar 20 dias não ajuda mais que
descansar 5). Nenhum código de fit/predict foi duplicado: theta=0 (tupla de
4) é o baseline, theta livre (tupla de 5, MESMO fit_goal_model) é a H10.

Métrica: RPS ordinal 1X2 (mesma régua de H4 — hipótese de QUALIDADE do
modelo, não de mercado; O/U e CLV são perguntas de outra trial). Bootstrap
pareado por BLOCO móvel (não iid — jogos consecutivos do mesmo confronto ou
do mesmo time compartilham choque de forma, e o módulo bootstrap do core
avisa explicitamente contra iid em série autocorrelacionada).

Uso:
    python scripts/h10_fadiga_walkforward.py [--cutoff 2026-08-14]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry, attestation_path_for  # noqa: E402
from predictor_core.measurement.bootstrap import bootstrap_ci  # noqa: E402
from predictor_core.measurement.metrics import rps  # noqa: E402
from predictor_core.testing.harness import attest_pipeline_power  # noqa: E402
from predictor_core.testing.synth import probabilistic_predictor  # noqa: E402

from src import db, model, ratings  # noqa: E402
from src.ingest import load_config  # noqa: E402

TRIALS = ROOT / "data" / "trials.json"
TRIAL_NAME = "h10-fadiga-descanso-walkforward"
GAMES_PER_ROUND = 10  # Série A: 20 clubes -> 10 jogos por rodada
CAP_DAYS = 5.0  # recuperação satura — descanso > CAP não ajuda mais
MIN_CAL_GAMES = 100  # mesmo piso de backtest_walkforward.py
N_BOOT = 10_000
SEED = 42
BLOCK_LENGTH = GAMES_PER_ROUND  # bootstrap por bloco móvel ~1 rodada

log = logging.getLogger("h10_fadiga")


# ---------- dados ----------


def load_rows(conn, cutoff: str) -> list[tuple]:
    return conn.execute(
        "SELECT date, home_team, away_team, home_score, away_score, tournament, neutral "
        "FROM matches WHERE home_score IS NOT NULL AND date <= ? ORDER BY date",
        (cutoff,),
    ).fetchall()


def rest_days_diff(rows: list[tuple]) -> list[float]:
    """Diferencial de descanso (mandante - visitante), capado em ±CAP_DAYS.
    Estreia de um time = CAP_DAYS (totalmente descansado, mesma convenção do
    poc original)."""
    last_seen: dict[str, date] = {}
    out: list[float] = []
    for d, home, away, *_ in rows:
        today = date.fromisoformat(d)

        def rest(team: str) -> float:
            if team not in last_seen:
                return CAP_DAYS
            return min(float((today - last_seen[team]).days), CAP_DAYS)

        out.append(rest(home) - rest(away))
        last_seen[home] = last_seen[away] = today
    return out


def outcome_index(hs: int, aws: int) -> int:
    return 0 if hs > aws else (1 if hs == aws else 2)


# ---------- walk-forward pareado ----------


def run_walkforward(cfg, rows: list[tuple], rest_diff: list[float], block_games: int) -> dict[str, Any]:
    cal_years = cfg["model"].get("calibration_window_years", 4)
    max_goals = cfg["model"]["max_goals"]

    if len(rows) < 2 * block_games:
        sys.exit(f"base insuficiente: {len(rows)} jogos < 2 blocos de {block_games}")

    _, history = ratings.compute_ratings(rows, cfg["elo"])

    blocks = []
    start = block_games
    while start < len(rows):
        blocks.append((start, min(start + block_games, len(rows))))
        start += block_games

    rps_base: list[float] = []
    rps_fadiga: list[float] = []
    n_blocks_used = 0
    for block_idx, (lo, hi) in enumerate(blocks, 1):
        first_date = rows[lo][0]
        cal_cut = (date.fromisoformat(first_date) - timedelta(days=int(cal_years * 365.25))).isoformat()
        cal_mask = [cal_cut <= r[0] < first_date for r in rows]
        hist_cal = [h for h, keep in zip(history, cal_mask) if keep]
        rest_cal = [rd for rd, keep in zip(rest_diff, cal_mask) if keep]
        if len(hist_cal) < MIN_CAL_GAMES:
            log.info("bloco %d: só %d jogos de calibração — pulado", block_idx, len(hist_cal))
            continue
        params_base = model.fit_goal_model(hist_cal)
        params_fadiga = model.fit_goal_model(hist_cal, delta_xg=rest_cal)
        n_blocks_used += 1

        for i in range(lo, hi):
            diff, hs, aws = history[i][0], rows[i][3], rows[i][4]
            y = outcome_index(hs, aws)
            pb = model.predict_match(diff, 0.0, params_base, home_adv=0.0, max_goals=max_goals)
            pf = model.predict_match(diff, 0.0, params_fadiga, home_adv=0.0, delta_xg=rest_diff[i], max_goals=max_goals)
            rps_base.append(rps([[pb["p_win"], pb["p_draw"], pb["p_loss"]]], [y]))
            rps_fadiga.append(rps([[pf["p_win"], pf["p_draw"], pf["p_loss"]]], [y]))

    return {
        "n": len(rps_base),
        "n_blocks_used": n_blocks_used,
        "rps_base": rps_base,
        "rps_fadiga": rps_fadiga,
    }


def paired_bootstrap_gain(rps_base: list[float], rps_fadiga: list[float]) -> tuple[float, float, float]:
    """gain_i = RPS_base_i - RPS_fadiga_i (positivo = fadiga acerta mais).
    IC95 do ganho médio por bootstrap de BLOCO móvel (não iid — jogos
    consecutivos correlacionados)."""
    gains = [b - f for b, f in zip(rps_base, rps_fadiga)]
    mean_gain = sum(gains) / len(gains)
    lo, hi, _ = bootstrap_ci(
        gains,
        lambda u: sum(u) / len(u),
        scheme="moving",
        block_length=min(BLOCK_LENGTH, len(gains) - 1) if len(gains) > 1 else 1,
        n_boot=N_BOOT,
        seed=SEED,
    )
    return mean_gain, lo, hi


# ---------- controle positivo (harness, metric="rps") ----------


def _rps_pipeline(series: tuple[list[list[float]], list[int]]) -> dict[str, str]:
    probs, outcomes = series
    uniform = [1 / 3, 1 / 3, 1 / 3]
    gains = [rps([uniform], [y]) - rps([p], [y]) for p, y in zip(probs, outcomes)]
    lo, _, _ = bootstrap_ci(gains, lambda u: sum(u) / len(u), scheme="iid", n_boot=500, seed=13)
    return {"verdict": "COMPROVADA" if (lo is not None and lo > 0) else "REFUTADA"}


def attest_rps_power() -> dict[str, Any]:
    def edge():
        return probabilistic_predictor(300, skill_level=0.6, seed=13, n_classes=3)

    def noise():
        return probabilistic_predictor(300, skill_level=0.0, seed=17, n_classes=3)

    return attest_pipeline_power(
        _rps_pipeline,
        edge,
        noise,
        attestation_path=attestation_path_for(TRIALS),
        note="H10: controle positivo da régua RPS (edge sintético k=3 detectado, ruído uniforme rejeitado)",
        metric="rps",
    )


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", default=date.today().isoformat())
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    cfg = load_config()
    conn = db.connect(str(ROOT / cfg["database"]), read_only=True)
    try:
        rows = load_rows(conn, args.cutoff)
    finally:
        conn.close()
    if not rows:
        log.error("nenhum jogo encerrado até %s em `matches` — rode sync_matches_from_sofascore antes", args.cutoff)
        return 1

    rest = rest_days_diff(rows)
    block_games = int(cfg["backtest"].get("walk_forward_window_rounds", 19)) * GAMES_PER_ROUND
    result = run_walkforward(cfg, rows, rest, block_games)
    if result["n"] == 0:
        log.error("nenhum bloco com calibração suficiente (>= %d jogos) — base insuficiente", MIN_CAL_GAMES)
        return 1

    mean_gain, lo, hi = paired_bootstrap_gain(result["rps_base"], result["rps_fadiga"])
    log.info(
        "n=%d (%d blocos) | RPS base=%.5f fadiga=%.5f | ganho médio=%.5f | IC95=[%.5f, %.5f]",
        result["n"],
        result["n_blocks_used"],
        sum(result["rps_base"]) / result["n"],
        sum(result["rps_fadiga"]) / result["n"],
        mean_gain,
        lo if lo is not None else float("nan"),
        hi if hi is not None else float("nan"),
    )

    go = lo is not None and lo > 0
    status = "comprovada" if go else "refutada"
    detail = (
        "IC95 estritamente positivo — o descanso reduz o erro ordinal com significância"
        if go
        else (
            "IC95 cruza zero — o ganho do descanso é indistinguível de sorte"
            if (lo is not None and lo < 0 < (hi or 0))
            else "IC95 estritamente negativo — o descanso piora o RPS"
        )
    )
    log.info("VEREDITO H10: %s (%s)", status.upper(), detail)

    # Atestado SEMPRE antes de registrar uma trial nova, comprovada ou não —
    # é a prova de que o funil detecta sinal sintético, não uma formalidade
    # que só se aplica quando o resultado agrada.
    attestation = attest_rps_power()
    log.info("atestado de poder emitido: fingerprint=%s", attestation["pipeline_fingerprint"])

    registry = TrialRegistry(TRIALS)
    registry.register(
        TRIAL_NAME,
        params={
            "market": "1x2",
            "feature": "rest_days_diff_capped",
            "cap_days": CAP_DAYS,
            "walk_forward_window_rounds": cfg["backtest"].get("walk_forward_window_rounds", 19),
            "league": "Brasileirão Série A",
            "domain": "matches (Sofascore mirror, pós-adaptação — substitui poc_fadiga.py vestigial)",
        },
        sharpe=None,
        notes=(
            f"H10: descanso (dias desde o último jogo, diferencial mandante-visitante, capado em "
            f"±{CAP_DAYS:.0f}d) melhora o RPS 1X2 sobre o baseline sem a feature? Walk-forward por blocos de "
            f"{cfg['backtest'].get('walk_forward_window_rounds', 19)} rodadas (mesmo padrão de H1/H4), "
            f"recalibração via model.fit_goal_model(delta_xg=diferencial_descanso) — mesmo mecanismo genérico "
            f"já usado por xG, sem MLE duplicado. RESULTADO ({date.today().isoformat()}): n={result['n']} "
            f"({result['n_blocks_used']} blocos), ganho médio de RPS={mean_gain:.5f}, IC95=[{lo:.5f}, {hi:.5f}] "
            f"via bootstrap de bloco móvel (block_length={BLOCK_LENGTH}, n_boot={N_BOOT}, seed={SEED}). {detail}. "
            f"NÃO AUTORIZA CAPITAL — hipótese de qualidade de modelo (RPS), não de mercado; mesmo se COMPROVADA, "
            f"ainda faltaria um funil de aposta com odds reais para virar decisão econômica."
        ),
        metric="rps",
        status=status,
        pipeline_fingerprint=attestation["pipeline_fingerprint"],
    )
    log.info("trial '%s' registrada em %s com status='%s'", TRIAL_NAME, TRIALS, status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
