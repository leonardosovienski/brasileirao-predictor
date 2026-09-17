"""evaluate_h14_prospective — o ÚNICO ponto de avaliação da H14
(h14-serving-v2-vs-climatologia-prequential-prospectivo).

O pré-registro (`prereg_serving_vs_climatologia.py`) e a persistência
(`persist_h14_prospective.py`) já existem. Este script é o terceiro e
último passo: lê o ledger append-only, casa cada previsão persistida com o
resultado real do jogo (só quando já concluído), e mede.

GATE DE PODER — NÃO NEGOCIÁVEL
--------------------------------
`min_n_avaliacao=900` está congelado no pré-registro (`data/trials.json`).
Rodar isto com n<900 e IMPRIMIR qualquer métrica seria uma olhada
intermediária disfarçada de "só checando" — exatamente o mecanismo que
infla falso-positivo. Por isso, com n<900 o script NÃO calcula RPS, delta,
IC95 nem nada: só informa quantos faltam. `avaliacoes_intermediarias=false`
é MECÂNICO aqui, não só documentado.

PONTO ÚNICO
-----------
Uma checagem de contrato precede o claim; o claim precede leituras da coorte e cálculos, tanto no CLI quanto na
API evaluate(). Com n<900 o claim é liberado; sucesso, erro ou crash o retêm
e bloqueiam nova tentativa automática. O relatório exclusivo é persistido
antes de retornar/imprimir. Resolver claim retido exige governança; não
existe flag de reavaliação. Testes devem usar reports_dir temporário.

Uso:
    python brasileirao_scripts/evaluate_h14_prospective.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry  # noqa: E402
from predictor_core.measurement.bootstrap import bootstrap_ci  # noqa: E402
from predictor_core.measurement.metrics import brier, log_loss, rps  # noqa: E402

from brasileirao_predictor import db  # noqa: E402
from brasileirao_predictor.ingest import load_config  # noqa: E402
from brasileirao_scripts._prospective_evaluation_guard import (  # noqa: E402
    EvaluationBlocked,
    claim_directory,
    evaluate_once,
    require_available,
)

TRIAL = "h14-serving-v2-vs-climatologia-prequential-prospectivo"
TRIALS_PATH = ROOT / "data" / "trials.json"
LEDGER_PATH = ROOT / "data" / "research" / "h14_serving_vs_climatologia.jsonl"
REPORTS_DIR = ROOT / "reports"

BLOCK_LENGTH = 21
N_BOOT = 10_000
SEED = 42
GUARDRAIL_METRICS = ("log_loss", "brier_1x2")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _outcome_1x2(home_goals: int, away_goals: int) -> int:
    if home_goals > away_goals:
        return 2
    if home_goals == away_goals:
        return 1
    return 0


def _results_by_event(conn) -> dict[int, tuple[int, int]]:
    rows = conn.execute(
        "SELECT event_id, home_score, away_score FROM sofascore_matches "
        "WHERE home_score IS NOT NULL AND away_score IS NOT NULL"
    ).fetchall()
    return {eid: (int(hs), int(as_)) for eid, hs, as_ in rows}


def _paired_losses(record: dict[str, Any], arm: str, actual: int) -> dict[str, float]:
    p = [record[arm]["p_away"], record[arm]["p_draw"], record[arm]["p_home"]]
    return {
        "rps": rps([p], [actual]),
        "log_loss": log_loss([p], [actual]),
        "brier_1x2": brier([p], [actual]),
    }


def _paired_gain(control: list[float], treatment: list[float]) -> dict[str, Any]:
    """Ganho = perda da climatologia (control) menos perda do serving-v2
    (treatment). Positivo = serving-v2 melhor. Mesmo bootstrap de bloco
    móvel do RESEARCH-01A — jogos vizinhos no tempo não são independentes."""
    gains = [c - t for c, t in zip(control, treatment, strict=True)]
    mean = sum(gains) / len(gains)
    lo, hi, _ = bootstrap_ci(
        gains, lambda u: sum(u) / len(u), scheme="moving", block_length=BLOCK_LENGTH, n_boot=N_BOOT, seed=SEED
    )
    return {
        "mean_gain": mean,
        "ci95": [lo, hi],
        "climatology_mean_loss": sum(control) / len(control),
        "serving_v2_mean_loss": sum(treatment) / len(treatment),
        "n": len(gains),
    }


def _valid_interval(interval: Any) -> bool:
    return (
        isinstance(interval, (list, tuple))
        and len(interval) == 2
        and all(type(value) in (int, float) and math.isfinite(value) for value in interval)
        and interval[0] <= interval[1]
    )


def _verdict(primary: dict[str, Any], guardrails: dict[str, dict[str, Any]]) -> tuple[str, str]:
    interval = primary.get("ci95")
    if not _valid_interval(interval):
        return "inconclusiva", "IC95 primário ausente ou inválido — aprovação não permitida"
    lo, hi = interval
    if lo <= 0:
        detail = (
            "IC95 do ganho de RPS inclui zero — superioridade não demonstrada; não prova equivalência"
            if hi >= 0
            else "IC95 do ganho de RPS estritamente negativo — serving-v2 PIOR que a climatologia"
        )
        return "refutada", detail
    for metric in GUARDRAIL_METRICS:
        interval = guardrails.get(metric, {}).get("ci95")
        if not _valid_interval(interval):
            return "inconclusiva", f"guardrail {metric} sem IC95 válido — aprovação não permitida"
    piorados = [
        f"{m} (IC95=[{g['ci95'][0]:.6f}, {g['ci95'][1]:.6f}])"
        for m, g in guardrails.items()
        if g["ci95"][1] is not None and g["ci95"][1] < 0
    ]
    if piorados:
        return "refutada", "RPS melhora com IC95 acima de zero, mas guardrail piorou materialmente: " + "; ".join(
            piorados
        )
    return "comprovada", "IC95 do ganho de RPS estritamente positivo e nenhum guardrail materialmente pior"


def _require_supported_protocol(trials_path: Path) -> None:
    """Read contract metadata only; reject unsupported metrics before a claim.

    This does not authorize a cohort evaluation or modify the frozen protocol.
    In particular, absent OU2.5 forecasts cannot be reconstructed from 1X2.
    """
    trials = [t for t in TrialRegistry(trials_path).load() if t["name"] == TRIAL]
    if len(trials) != 1:
        raise EvaluationBlocked(f"{TRIAL}: expected exactly one registered protocol")
    params = trials[0].get("params", {})
    declared = params.get("guardrails")
    if (
        params.get("primary_metric") != "rps"
        or not isinstance(declared, list)
        or any(not isinstance(metric, str) for metric in declared)
        or len(declared) != len(GUARDRAIL_METRICS)
        or set(declared) != set(GUARDRAIL_METRICS)
    ):
        raise EvaluationBlocked(
            f"{TRIAL}: protocol/evaluator metric mismatch; "
            f"declared primary={params.get('primary_metric')!r}, guardrails={declared!r}; "
            f"implemented primary='rps', guardrails={GUARDRAIL_METRICS!r}. "
            "No cohort read or metric calculation authorized. "
            "Preserve the frozen protocol and resolve the missing implementation/data."
        )


def evaluate(
    *,
    trials_path: Path | None = None,
    ledger_path: Path | None = None,
    db_path: Path | None = None,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    """Check contract before claiming; claim before cohort reads; never auto retry."""
    ledger = Path(ledger_path if ledger_path is not None else LEDGER_PATH).resolve()
    claim_dir = claim_directory(trial=TRIAL, ledger_path=ledger)
    if ledger == LEDGER_PATH.resolve():
        # Legacy reports for the default cohort still block a changed output folder.
        require_available(REPORTS_DIR, "h14", claim_dir=claim_dir)
    require_available(reports_dir if reports_dir is not None else REPORTS_DIR, "h14", claim_dir=claim_dir)
    _require_supported_protocol(trials_path if trials_path is not None else TRIALS_PATH)
    return evaluate_once(
        lambda: _evaluate_claimed(trials_path=trials_path, ledger_path=ledger_path, db_path=db_path),
        reports_dir=reports_dir if reports_dir is not None else REPORTS_DIR,
        claim_dir=claim_dir,
        prefix="h14",
        trial=TRIAL,
    )


def _evaluate_claimed(*, trials_path: Path | None, ledger_path: Path | None, db_path: Path | None) -> dict[str, Any]:
    trials_path = trials_path or TRIALS_PATH
    ledger_path = ledger_path or LEDGER_PATH
    _require_supported_protocol(trials_path)
    trial = next((t for t in TrialRegistry(trials_path).load() if t["name"] == TRIAL), None)
    if trial is None:
        sys.exit(f"trial {TRIAL!r} não registrada")
    min_n = int(trial["params"]["min_n_avaliacao"])

    cfg = load_config()
    conn = db.connect(str(db_path or (ROOT / cfg["database"])), read_only=True)
    try:
        results = _results_by_event(conn)
    finally:
        conn.close()

    ledger = _load_jsonl(ledger_path)
    matured = [row for row in ledger if row["event_id"] in results]
    if len({row["event_id"] for row in ledger}) != len(ledger):
        raise EvaluationBlocked("Duplicate event IDs in the ledger; no metrics calculated")
    n = len(matured)

    if n < min_n:
        return {
            "status": "AGUARDANDO_N",
            "n": n,
            "min_n_avaliacao": min_n,
            "faltam": min_n - n,
            "nota": "avaliacoes_intermediarias=false: nenhuma métrica é calculada abaixo do n mínimo",
        }

    climatology_losses = {"rps": [], "log_loss": [], "brier_1x2": []}
    serving_losses = {"rps": [], "log_loss": [], "brier_1x2": []}
    for row in matured:
        actual = _outcome_1x2(*results[row["event_id"]])
        c = _paired_losses(row, "climatology", actual)
        s = _paired_losses(row, "serving_v2", actual)
        for metric in climatology_losses:
            climatology_losses[metric].append(c[metric])
            serving_losses[metric].append(s[metric])

    primary = _paired_gain(climatology_losses["rps"], serving_losses["rps"])
    guardrails = {m: _paired_gain(climatology_losses[m], serving_losses[m]) for m in GUARDRAIL_METRICS}
    status, detail = _verdict(primary, guardrails)
    return {
        "status": status.upper(),
        "detail": detail,
        "n": n,
        "min_n_avaliacao": min_n,
        "primary_rps": primary,
        "guardrails": guardrails,
        "trial": TRIAL,
        "decision_scope": "individual_trial_only",
        "portfolio_claim_authorized": False,
        "capital_enabled": False,
    }


def main() -> int:
    try:
        require_available(
            REPORTS_DIR,
            "h14",
            claim_dir=claim_directory(trial=TRIAL, ledger_path=LEDGER_PATH),
        )
        result = evaluate()
    except EvaluationBlocked as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
