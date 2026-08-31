"""RESEARCH-XG — o ensemble de xG ligado vs. desligado, na pilha de serving.

Testa UMA coisa só (Regra 6): a flag `ensemble_xg.enabled`. Motor, período,
cadência de reajuste, half-life, janelas de Elo e de calibração, guarda de
bloco — tudo idêntico entre os braços.

    CONTROL   ensemble_xg.enabled = True   (o que estava em produção)
    TREATMENT ensemble_xg.enabled = False

PROVENIÊNCIA — LEIA ANTES DE INTERPRETAR O VEREDITO. Este NÃO é um
pré-registro cego. O efeito já tinha sido observado em 2026-08-22, em duas
corridas NÃO pareadas de `benchmark_predictor --engine serving`
(RPS 0,217749 com ensemble contra 0,213339 sem). Este script existe para pôr
um IC95 pareado naquele ponto estimado, não para descobri-lo. Um "comprovada"
aqui é confirmação de um efeito já visto na mesma amostra — vale bem menos que
um GO pré-registrado, e a trial entra no denominador do DSR justamente para
que essa distinção não se perca.

POR QUE O `config.yaml` NÃO DECIDE OS BRAÇOS: os dois estados são forçados no
código, sobrescrevendo o que estiver no arquivo. Se o script lesse a config, o
experimento mudaria de identidade conforme alguém editasse produção — e foi
exatamente uma edição não aplicada que fez duas corridas do painel saírem com
RPS idêntico e parecerem braços opostos.

MÉTRICA PRIMÁRIA: RPS (ordinal 1X2), ganho pareado jogo a jogo.
GUARDRAILS: log-loss e Brier 1X2/OU2.5 não podem piorar materialmente.
DIAGNÓSTICO: accuracy 1X2 (DIAGNOSTIC_ONLY, Regra 12) e `xg_fit_failures`.

`xg_fit_failures` NÃO É COSMÉTICO AQUI: cada falha de ajuste degrada aquela
previsão para o baseline puro. Se o braço CONTROL acumular falhas, ele deixa
de ser "com ensemble" na proporção das falhas, e o contraste medido encolhe
para o do braço que sobrou. O script avisa alto quando isso acontece.

NÃO AUTORIZA CAPITAL. É hipótese de qualidade de modelo (RPS), não de mercado.

Uso:
    python brasileirao_scripts/research_xg_ensemble.py --period 2021-01-01,2024-12-31

O holdout de 2025 fica SELADO (Regra 7): o default de `--period` termina em
2024-12-31 e o script RECUSA um `end` dentro de 2025 sem `--unseal-holdout`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry  # noqa: E402

from brasileirao_predictor.ingest import load_config  # noqa: E402
from brasileirao_scripts.benchmark_predictor import (  # noqa: E402
    MIN_HISTORY,
    RETRAIN_EVERY,
    _half_life_for,
    _load_observations,
    _run_walkforward,
)

# O atestado de poder é do PIPELINE (a régua RPS), não da trial: mesma função,
# mesmo arquivo de attestation. Reemitir aqui re-atesta o código atual, que é o
# comportamento desejado — código que muda invalida atestado anterior.
from brasileirao_scripts.research_01a_refit_cadence import (  # noqa: E402
    BLOCK_LENGTH,
    GUARDRAIL_METRICS,
    N_BOOT,
    SEALED_HOLDOUT_YEAR,
    SEED,
    _accuracy_1x2,
    _check_row_contract,
    _paired_gain,
    _paired_losses,
    attest_rps_power,
)

log = logging.getLogger("research_xg")

TRIALS = ROOT / "data" / "trials.json"
TRIAL_NAME = "h12-ensemble-xg-ligado-vs-desligado"
MODEL_TAG = "H4_DIXON_COLES_CALIBRATED"
ENGINE = "serving"
DEFAULT_PERIOD = "2021-01-01,2024-12-31"


def _cfg_with_ensemble(cfg: dict[str, Any], enabled: bool) -> dict[str, Any]:
    """Cópia PROFUNDA da config com a flag forçada.

    Profunda porque os dois braços rodam no mesmo processo: um `{**cfg}` raso
    deixaria `cfg["ensemble_xg"]` compartilhado, e mexer nele num braço mudaria
    o outro — um vazamento de configuração entre braços que nenhum teste de
    métrica pegaria."""
    novo = deepcopy(cfg)
    novo.setdefault("ensemble_xg", {})["enabled"] = enabled
    return novo


def _arm(
    observations: list[dict[str, Any]],
    half_life: float,
    cfg: dict[str, Any],
    start: str,
    end: str,
    arm: str,
):
    def _progress(done: int, total: int) -> None:
        log.info("  %s: %d/%d previsões", arm, done, total)

    rows, ev = _run_walkforward(
        observations,
        half_life,
        RETRAIN_EVERY,
        progress=_progress,
        engine=ENGINE,
        cfg=cfg,
    )
    _check_row_contract(rows)
    rows = [r for r in rows if (not start or r["date"] >= start) and (not end or r["date"] <= end)]
    return rows, ev


def _verdict(primary: dict[str, Any], guardrails: dict[str, dict[str, Any]]) -> tuple[str, str]:
    """Ganho = perda(CONTROL) − perda(TREATMENT). Positivo = DESLIGAR é melhor."""
    lo, hi = primary["ci95"]
    if lo is None or hi is None:
        return "inconclusiva", "bootstrap não produziu IC95 — amostra insuficiente"
    if lo <= 0:
        detail = (
            "IC95 do ganho de RPS cruza zero — desligar o ensemble de xG é indistinguível de sorte"
            if hi > 0
            else "IC95 do ganho de RPS estritamente negativo — desligar o ensemble PIORA a previsão"
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
        "IC95 do ganho de RPS estritamente positivo e nenhum guardrail materialmente pior — "
        "desligar o ensemble de xG melhora a previsão",
    )


def _trial_params(start: str, end: str) -> dict[str, Any]:
    """Identidade da configuração. Mudar qualquer coisa aqui é trial NOVA."""
    return {
        "market": "1x2",
        "variable": "ensemble_xg.enabled",
        "control": True,
        "treatment": False,
        "engine": ENGINE,
        "model": MODEL_TAG,
        "retrain_every": RETRAIN_EVERY,
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
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    start, _, end = args.period.partition(",")
    start, end = start.strip(), end.strip()
    if not args.unseal_holdout and (not end or end >= f"{SEALED_HOLDOUT_YEAR}-01-01"):
        log.error(
            "--period termina em %s, dentro/além do holdout selado de %s. Regra 7.",
            end or "(aberto)",
            SEALED_HOLDOUT_YEAR,
        )
        return 1

    cfg = load_config()
    registry = TrialRegistry(TRIALS)
    params = _trial_params(start, end)
    attestation = attest_rps_power()
    log.info("atestado de poder emitido: fingerprint=%s", attestation["pipeline_fingerprint"])

    half_life = _half_life_for(MODEL_TAG)
    observations = _load_observations(end)
    if len(observations) < MIN_HISTORY + 50:
        log.error("histórico insuficiente (%d) para min_history=%d", len(observations), MIN_HISTORY)
        return 1

    log.info("braço CONTROL: ensemble_xg.enabled=True")
    control_rows, control_ev = _arm(observations, half_life, _cfg_with_ensemble(cfg, True), start, end, "CONTROL")
    log.info("braço TREATMENT: ensemble_xg.enabled=False")
    treatment_rows, treatment_ev = _arm(
        observations, half_life, _cfg_with_ensemble(cfg, False), start, end, "TREATMENT"
    )

    if not control_rows:
        log.error("nenhuma previsão no período [%s, %s]", start or "-inf", end or "+inf")
        return 1
    key = [(r["date"], r["home"], r["away"]) for r in control_rows]
    if key != [(r["date"], r["home"], r["away"]) for r in treatment_rows]:
        log.error("braços não pareiam jogo a jogo — abortando em vez de comparar amostras diferentes")
        return 1

    # Os braços TÊM que diferir: se as previsões saírem idênticas, a flag não
    # foi aplicada e o "experimento" comparou uma corrida com ela mesma. Foi o
    # que aconteceu em 2026-08-22 com duas execuções manuais do painel.
    identicas = sum(1 for a, b in zip(control_rows, treatment_rows) if a["p_win"] == b["p_win"])
    if identicas == len(control_rows):
        log.error(
            "os dois braços produziram previsões IDÊNTICAS em %d/%d jogos — a flag do ensemble "
            "não teve efeito; não há experimento aqui",
            identicas,
            len(control_rows),
        )
        return 1

    if control_ev.xg_fit_failures:
        log.warning(
            "CONTROL degradou para o baseline em %d ajustes (xg_fit_failures) — o braço 'com ensemble' "
            "não é integralmente com ensemble; o contraste medido é menor que o real",
            control_ev.xg_fit_failures,
        )

    control_losses = _paired_losses(control_rows)
    treatment_losses = _paired_losses(treatment_rows)
    primary = _paired_gain(control_losses["rps"], treatment_losses["rps"])
    guardrails = {m: _paired_gain(control_losses[m], treatment_losses[m]) for m in GUARDRAIL_METRICS}

    status, detail = _verdict(primary, guardrails)
    lo, hi = primary["ci95"]
    log.info(
        "n=%d | RPS com_ensemble=%.6f sem_ensemble=%.6f | ganho=%.6f | IC95=[%.6f, %.6f]",
        primary["n"],
        primary["control_mean_loss"],
        primary["treatment_mean_loss"],
        primary["mean_gain"],
        lo,
        hi,
    )
    log.info("VEREDITO RESEARCH-XG: %s (%s)", status.upper(), detail)

    report = {
        "schema_version": "research-xg/1",
        "trial": TRIAL_NAME,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "params": params,
        "half_life_days": half_life,
        "primary": {"metric": "rps", "is_primary": True, **primary},
        "guardrails": guardrails,
        "diagnostic": {
            "accuracy_1x2_control": _accuracy_1x2(control_rows),
            "accuracy_1x2_treatment": _accuracy_1x2(treatment_rows),
            "xg_fit_failures_control": control_ev.xg_fit_failures,
            "blocked_observations_control": control_ev.blocked_observations,
            "blocked_observations_treatment": treatment_ev.blocked_observations,
            "linhas_identicas_entre_bracos": identicas,
        },
        "provenance": (
            "NÃO é pré-registro cego: o efeito foi observado antes, em duas corridas não pareadas "
            "de benchmark_predictor --engine serving (2026-08-22). Este experimento acrescenta o "
            "IC95 pareado, na MESMA amostra em que o efeito foi visto."
        ),
        "verdict": {"status": status, "detail": detail},
    }
    out = args.output or ROOT / "reports" / f"research_xg_ensemble_{date.today().isoformat()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    registry.register(
        TRIAL_NAME,
        params=params,
        sharpe=None,
        notes=(
            f"RESEARCH-XG: ensemble de xG ligado vs. desligado na pilha de serving. Uma variável só; "
            f"os dois estados forçados no código, não lidos do config.yaml. "
            f"RESULTADO ({date.today().isoformat()}): n={primary['n']}, RPS com_ensemble="
            f"{primary['control_mean_loss']:.6f} sem_ensemble={primary['treatment_mean_loss']:.6f}, "
            f"ganho pareado={primary['mean_gain']:.6f}, IC95=[{lo:.6f}, {hi:.6f}] via bootstrap de bloco "
            f"móvel (block_length={BLOCK_LENGTH}, n_boot={N_BOOT}, seed={SEED}). {detail}. "
            f"PROVENIÊNCIA: não é pré-registro cego — o efeito foi observado antes em duas corridas não "
            f"pareadas do painel (2026-08-22); este experimento pôs IC95 na MESMA amostra. "
            f"NÃO AUTORIZA CAPITAL — hipótese de qualidade de modelo (RPS), não de mercado. "
            f"Relatório: {out.name}"
        ),
        metric="rps",
        status=status,
        pipeline_fingerprint=attestation["pipeline_fingerprint"],
        test_period=[start or None, end or None],
    )
    log.info("trial '%s' registrada com status='%s' | relatório: %s", TRIAL_NAME, status, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
