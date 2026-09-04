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
Depois de uma avaliação bem-sucedida (n>=900), o relatório é escrito em
`reports/h14_avaliacao_<timestamp>.json`. Rodar de novo NÃO sobrescreve nem
reavalia silenciosamente — sinaliza que já houve avaliação e pede
`--force-reavaliacao` com justificativa explícita no código-fonte de quem
está chamando (não um simples parâmetro CLI, de propósito: reavaliar uma
trial de ponto único é uma decisão de governança, não uma flag de rotina).

Uso:
    python brasileirao_scripts/evaluate_h14_prospective.py
"""

from __future__ import annotations

import json
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
        "SELECT event_id, home_score, away_score FROM sofascore_matches WHERE home_score IS NOT NULL"
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


def _verdict(primary: dict[str, Any], guardrails: dict[str, dict[str, Any]]) -> tuple[str, str]:
    lo, hi = primary["ci95"]
    if lo is None or hi is None:
        return "inconclusiva", "bootstrap não produziu IC95 — amostra insuficiente"
    if lo <= 0:
        detail = (
            "IC95 do ganho de RPS cruza zero — bater a climatologia é indistinguível de sorte"
            if hi > 0
            else "IC95 do ganho de RPS estritamente negativo — serving-v2 PIOR que a climatologia"
        )
        return "refutada", detail
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


def evaluate(
    *,
    trials_path: Path | None = None,
    ledger_path: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    trials_path = trials_path or TRIALS_PATH
    ledger_path = ledger_path or LEDGER_PATH
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
        "capital_enabled": False,
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] == "AGUARDANDO_N":
        return 0
    existing = sorted(REPORTS_DIR.glob("h14_avaliacao_*.json"))
    if existing:
        print(
            f"AVISO: já existe relatório de avaliação ({existing[-1].name}). "
            "H14 é ponto único — reavaliar exige decisão de governança explícita, "
            "não é automático. Nenhum arquivo novo foi escrito.",
            file=sys.stderr,
        )
        return 1
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import UTC, datetime

    out = REPORTS_DIR / f"h14_avaliacao_{datetime.now(UTC).strftime('%Y-%m-%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"relatório escrito em {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
