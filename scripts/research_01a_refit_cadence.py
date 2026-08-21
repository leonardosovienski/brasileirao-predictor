"""RESEARCH-01A — cadência de reajuste: bloco de rodada vs. bloco de 100 jogos.

Primeiro experimento matemático do Roadmap Técnico Consolidado v1.0-final
(TRACK A). Testa UMA coisa só (Regra 6): com que frequência o Dixon-Coles é
reajustado. Todo o resto — half-life, min_history, max_goals, base, ordenação,
guarda de bloco — é idêntico entre os braços.

    CONTROL   retrain_every=100  (a cadência vigente do painel canônico)
    TREATMENT retrain_every=10   (~1 bloco de rodada do Brasileirão)

NOTA SOBRE O ROADMAP: o texto descreve o CONTROL como "refit na virada do mês".
O código nunca fez isso — `benchmark_predictor.RETRAIN_EVERY` conta JOGOS, não
dias, e 100 jogos ≈ 10 rodadas ≈ um mês de calendário por coincidência de
cadência do campeonato. O experimento manipula a variável que existe de fato.

AGRUPAMENTO POR RELÓGIO, NÃO POR RODADA (roadmap, TRACK A): "rodada" é uma
abstração imperfeita porque jogo adiado migra de bloco. O que importa aqui é o
KICKOFF: a guarda de bloco de `src.evaluator` já impede que um jogo treine com
resultado de outro que ainda não apitou. Sem essa guarda, o braço TREATMENT
ganharia de graça — refit mais frequente = mais oportunidades de espiar o
bloco simultâneo —, e o experimento mediria leakage em vez de cadência.

MÉTRICA PRIMÁRIA: RPS (ordinal 1X2), ganho pareado jogo a jogo.
GUARDRAILS: log-loss e Brier 1X2/OU2.5 não podem piorar materialmente.
DIAGNÓSTICO: accuracy 1X2 (DIAGNOSTIC_ONLY, Regra 12), nº de reajustes.

NÃO AUTORIZA CAPITAL. É hipótese de qualidade de modelo (RPS), não de mercado:
mesmo um GO limpo não diz nada sobre edge econômico contra preço de casa.

Uso:
    python scripts/research_01a_refit_cadence.py --period 2021-01-01,2024-12-31

O holdout de 2025 fica SELADO (Regra 7): o default de `--period` termina em
2024-12-31 e o script RECUSA um `end` dentro de 2025 sem `--unseal-holdout`,
que existe só para a decisão final de arquitetura, não para este experimento.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry, attestation_path_for  # noqa: E402
from predictor_core.measurement.bootstrap import bootstrap_ci  # noqa: E402
from predictor_core.measurement.metrics import brier, log_loss, rps  # noqa: E402
from predictor_core.testing.harness import attest_pipeline_power  # noqa: E402
from predictor_core.testing.synth import probabilistic_predictor  # noqa: E402

from scripts.benchmark_predictor import (  # noqa: E402
    MIN_HISTORY,
    RETRAIN_EVERY,
    _half_life_for,
    _load_observations,
    _run_walkforward,
)
from src.ingest import load_config  # noqa: E402

log = logging.getLogger("research_01a")

TRIALS = ROOT / "data" / "trials.json"
TRIAL_NAME = "h11-refit-cadence-rodada-vs-100jogos"
MODEL_TAG = "H4_DIXON_COLES_CALIBRATED"

CONTROL_RETRAIN = RETRAIN_EVERY  # 100 jogos
TREATMENT_RETRAIN = 10  # ~1 bloco de rodada
DEFAULT_PERIOD = "2021-01-01,2024-12-31"
SEALED_HOLDOUT_YEAR = "2025"

BLOCK_LENGTH = 21  # bootstrap de bloco móvel — jogos vizinhos são correlacionados
N_BOOT = 10_000
SEED = 42
# "Materialmente pior" nos guardrails: o IC95 do ganho tem que estar
# inteiramente do lado ruim, não só a média. Um guardrail que dispara com
# ruído vira veto arbitrário e reabre a porta pro cherry-picking.
GUARDRAIL_METRICS = ("log_loss", "brier_1x2", "brier_ou25")


# ---------- perdas pareadas ----------


def _paired_losses(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Perda POR JOGO de cada métrica — o pareamento exige uma perda por
    observação, não um agregado. `rows` vem do painel canônico."""
    out: dict[str, list[float]] = {"rps": [], "brier_1x2": [], "log_loss": [], "brier_ou25": []}
    for r in rows:
        p = [r["p_loss"], r["p_draw"], r["p_win"]]
        y = r["actual_1x2"]
        out["rps"].append(rps([p], [y]))
        out["brier_1x2"].append(brier([p], [y]))
        out["log_loss"].append(log_loss([p], [y]))
        out["brier_ou25"].append(brier([[1 - r["p_over"], r["p_over"]]], [r["actual_ou25"]]))
    return out


def _accuracy_1x2(rows: list[dict[str, Any]]) -> float:
    """DIAGNOSTIC_ONLY (Regra 12) — nunca métrica de promoção. Está no relatório
    porque é o número que o operador reconhece, não porque decide algo."""
    hits = sum(
        1 for r in rows if max(range(3), key=lambda i: [r["p_loss"], r["p_draw"], r["p_win"]][i]) == r["actual_1x2"]
    )
    return hits / len(rows)


def _paired_gain(control: list[float], treatment: list[float]) -> dict[str, Any]:
    """Ganho = perda do CONTROL menos perda do TREATMENT. Positivo = tratamento
    melhor. IC95 por bootstrap de bloco móvel (jogos vizinhos no tempo não são
    independentes; iid inflaria a significância)."""
    gains = [c - t for c, t in zip(control, treatment)]
    mean = sum(gains) / len(gains)
    lo, hi, _ = bootstrap_ci(
        gains,
        lambda u: sum(u) / len(u),
        scheme="moving",
        block_length=BLOCK_LENGTH,
        n_boot=N_BOOT,
        seed=SEED,
    )
    return {
        "mean_gain": mean,
        "ci95": [lo, hi],
        "control_mean_loss": sum(control) / len(control),
        "treatment_mean_loss": sum(treatment) / len(treatment),
        "n": len(gains),
    }


def _verdict(primary: dict[str, Any], guardrails: dict[str, dict[str, Any]]) -> tuple[str, str]:
    lo, hi = primary["ci95"]
    if lo is None or hi is None:
        return "inconclusiva", "bootstrap não produziu IC95 — amostra insuficiente"
    if lo <= 0:
        detail = (
            "IC95 do ganho de RPS cruza zero — recalibrar por rodada é indistinguível de sorte"
            if hi > 0
            else "IC95 do ganho de RPS estritamente negativo — recalibrar por rodada PIORA a previsão"
        )
        return "refutada", detail
    piorados = [
        f"{m} (IC95=[{g['ci95'][0]:.6f}, {g['ci95'][1]:.6f}])"
        for m, g in guardrails.items()
        if g["ci95"][1] is not None and g["ci95"][1] < 0
    ]
    if piorados:
        return (
            "refutada",
            "RPS melhora com IC95 acima de zero, mas guardrail piorou materialmente: " + "; ".join(piorados),
        )
    return (
        "comprovada",
        "IC95 do ganho de RPS estritamente positivo e nenhum guardrail materialmente pior",
    )


# ---------- controle positivo (harness, metric="rps") ----------


def _rps_pipeline(series: tuple[list[list[float]], list[int]]) -> dict[str, str]:
    probs, outcomes = series
    uniform = [1 / 3, 1 / 3, 1 / 3]
    gains = [rps([uniform], [y]) - rps([p], [y]) for p, y in zip(probs, outcomes)]
    lo, _, _ = bootstrap_ci(gains, lambda u: sum(u) / len(u), scheme="iid", n_boot=500, seed=13)
    return {"verdict": "COMPROVADA" if (lo is not None and lo > 0) else "REFUTADA"}


def attest_rps_power() -> dict[str, Any]:
    return attest_pipeline_power(
        _rps_pipeline,
        lambda: probabilistic_predictor(300, skill_level=0.6, seed=13, n_classes=3),
        lambda: probabilistic_predictor(300, skill_level=0.0, seed=17, n_classes=3),
        attestation_path=attestation_path_for(TRIALS),
        note="RESEARCH-01A: controle positivo da régua RPS (edge sintético k=3 detectado, ruído uniforme rejeitado)",
        metric="rps",
    )


# ---------- experimento ----------


def _arm(observations: list[dict[str, Any]], half_life: float, retrain_every: int, start: str, end: str, arm: str):
    def _progress(done: int, total: int) -> None:
        log.info("  %s: %d/%d previsões", arm, done, total)

    rows, ev = _run_walkforward(observations, half_life, retrain_every, progress=_progress)
    rows = [r for r in rows if (not start or r["date"] >= start) and (not end or r["date"] <= end)]
    return rows, ev


def _trial_params(start: str, end: str) -> dict[str, Any]:
    """A identidade da configuração. Mudar QUALQUER coisa aqui é trial NOVA —
    o registro do core recusa update com params diferentes, de propósito."""
    return {
        "market": "1x2",
        "variable": "retrain_every",
        "control": CONTROL_RETRAIN,
        "treatment": TREATMENT_RETRAIN,
        "model": MODEL_TAG,
        "min_history": MIN_HISTORY,
        "block_guard": "kickoff (jogos simultâneos fora do treino um do outro)",
        "bootstrap": {"scheme": "moving", "block_length": BLOCK_LENGTH, "n_boot": N_BOOT, "seed": SEED},
        "league": "Brasileirão Série A",
        "period": [start, end],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--period", default=DEFAULT_PERIOD, help=f"start,end (default {DEFAULT_PERIOD})")
    parser.add_argument("--output", type=Path, default=None, help="JSON do relatório (default reports/)")
    parser.add_argument(
        "--unseal-holdout",
        action="store_true",
        help="permite --period alcançar 2025. NÃO usar neste experimento (Regra 7).",
    )
    parser.add_argument(
        "--pre-register-only",
        action="store_true",
        help="registra o desenho da trial e sai, SEM rodar os braços",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    start, _, end = args.period.partition(",")
    start, end = start.strip(), end.strip()
    if not args.unseal_holdout and (not end or end >= f"{SEALED_HOLDOUT_YEAR}-01-01"):
        log.error(
            "--period termina em %s, dentro/além do holdout selado de %s. "
            "Regra 7: usar 2025 aqui deixa de ser holdout. Recuse-se ou passe --unseal-holdout conscientemente.",
            end or "(aberto)",
            SEALED_HOLDOUT_YEAR,
        )
        return 1

    load_config()
    registry = TrialRegistry(TRIALS)
    params = _trial_params(start, end)

    # PRÉ-REGISTRO: o desenho entra no denominador do DSR ANTES de qualquer
    # número aparecer. Reexecutar com os MESMOS params atualiza esta entrada
    # (preservando registered_at); mudar params é trial nova, por construção.
    attestation = attest_rps_power()
    log.info("atestado de poder emitido: fingerprint=%s", attestation["pipeline_fingerprint"])
    registry.register(
        TRIAL_NAME,
        params=params,
        sharpe=None,
        notes=(
            f"RESEARCH-01A (PRÉ-REGISTRO {date.today().isoformat()}): reajustar o Dixon-Coles a cada "
            f"~{TREATMENT_RETRAIN} jogos (bloco de rodada) melhora o RPS 1X2 frente à cadência vigente de "
            f"{CONTROL_RETRAIN} jogos? Uma variável só; guarda de bloco de kickoff ativa nos DOIS braços. "
            f"GO exige IC95 do ganho pareado de RPS estritamente acima de zero E nenhum guardrail "
            f"({', '.join(GUARDRAIL_METRICS)}) materialmente pior. Resultado ainda não medido."
        ),
        metric="rps",
        status="pre-registrada",
        pipeline_fingerprint=attestation["pipeline_fingerprint"],
        test_period=[start or None, end or None],
    )
    log.info("trial '%s' pré-registrada em %s", TRIAL_NAME, TRIALS)
    if args.pre_register_only:
        return 0

    half_life = _half_life_for(MODEL_TAG)
    observations = _load_observations(end)
    if len(observations) < MIN_HISTORY + 50:
        log.error("histórico insuficiente (%d) para min_history=%d", len(observations), MIN_HISTORY)
        return 1

    log.info("braço CONTROL: retrain_every=%d", CONTROL_RETRAIN)
    control_rows, control_ev = _arm(observations, half_life, CONTROL_RETRAIN, start, end, "CONTROL")
    log.info("braço TREATMENT: retrain_every=%d", TREATMENT_RETRAIN)
    treatment_rows, treatment_ev = _arm(observations, half_life, TREATMENT_RETRAIN, start, end, "TREATMENT")

    # Pareamento só é válido sobre a MESMA sequência de jogos; os dois braços
    # partem das mesmas observações e do mesmo min_history, então isso deveria
    # valer sempre — mas "deveria" não é verificação.
    key = [(r["date"], r["home"], r["away"]) for r in control_rows]
    if key != [(r["date"], r["home"], r["away"]) for r in treatment_rows]:
        log.error("braços não pareiam jogo a jogo — abortando em vez de comparar amostras diferentes")
        return 1
    if not control_rows:
        log.error("nenhuma previsão no período [%s, %s]", start or "-inf", end or "+inf")
        return 1

    control_losses = _paired_losses(control_rows)
    treatment_losses = _paired_losses(treatment_rows)
    primary = _paired_gain(control_losses["rps"], treatment_losses["rps"])
    guardrails = {m: _paired_gain(control_losses[m], treatment_losses[m]) for m in GUARDRAIL_METRICS}

    status, detail = _verdict(primary, guardrails)
    lo, hi = primary["ci95"]
    log.info(
        "n=%d | RPS control=%.6f treatment=%.6f | ganho=%.6f | IC95=[%.6f, %.6f]",
        primary["n"],
        primary["control_mean_loss"],
        primary["treatment_mean_loss"],
        primary["mean_gain"],
        lo,
        hi,
    )
    log.info("VEREDITO RESEARCH-01A: %s (%s)", status.upper(), detail)

    report = {
        "schema_version": "research-01a/1",
        "trial": TRIAL_NAME,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "params": params,
        "half_life_days": half_life,
        "primary": {"metric": "rps", "is_primary": True, **primary},
        "guardrails": guardrails,
        "diagnostic": {
            "accuracy_1x2_control": _accuracy_1x2(control_rows),
            "accuracy_1x2_treatment": _accuracy_1x2(treatment_rows),
            "blocked_observations_control": control_ev.blocked_observations,
            "blocked_observations_treatment": treatment_ev.blocked_observations,
            "deferred_refits_control": control_ev.deferred_refits,
            "deferred_refits_treatment": treatment_ev.deferred_refits,
        },
        "verdict": {"status": status, "detail": detail},
    }
    out = args.output or ROOT / "reports" / f"research_01a_refit_cadence_{date.today().isoformat()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    registry.register(
        TRIAL_NAME,
        params=params,
        sharpe=None,
        notes=(
            f"RESEARCH-01A: reajustar o Dixon-Coles a cada ~{TREATMENT_RETRAIN} jogos (bloco de rodada) vs. a "
            f"cadência vigente de {CONTROL_RETRAIN} jogos. Uma variável só; guarda de bloco de kickoff ativa nos "
            f"DOIS braços. RESULTADO ({date.today().isoformat()}): n={primary['n']}, RPS control="
            f"{primary['control_mean_loss']:.6f} treatment={primary['treatment_mean_loss']:.6f}, ganho pareado="
            f"{primary['mean_gain']:.6f}, IC95=[{lo:.6f}, {hi:.6f}] via bootstrap de bloco móvel "
            f"(block_length={BLOCK_LENGTH}, n_boot={N_BOOT}, seed={SEED}). {detail}. "
            f"NÃO AUTORIZA CAPITAL — hipótese de qualidade de modelo (RPS), não de mercado. Relatório: {out.name}"
        ),
        metric="rps",
        status=status,
        pipeline_fingerprint=attestation["pipeline_fingerprint"],
        test_period=[start or None, end or None],
    )
    log.info("trial '%s' atualizada com status='%s' | relatório: %s", TRIAL_NAME, status, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
