"""Painel de progresso da coorte prospectiva H3/H5 rumo ao gate de 100 picks.

Não recalcula nada que evaluate_shadow_cohort.py e src/bootstrap.py já fazem
com rigor — só junta os dois numa leitura rápida: quantos picks maturados,
ETA até os gates (100 picks do H3/H5, 50 picks do CLV antecedente H7), e o
CLV/ROI diagnóstico via bootstrap cluster por jogo (informacional, nunca um
veredito abaixo do n mínimo pré-registrado).

Uso: python brasileirao_scripts/shadow_dashboard.py
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from brasileirao_predictor.bootstrap import ci_mean_cluster
from brasileirao_scripts.evaluate_shadow_cohort import evaluate

ROOT = Path(__file__).resolve().parent.parent

COHORTS = {
    "H3 (baseline)": {
        "picks": ROOT / "data" / "sombra_picks_pinnacle.jsonl",
        "results": ROOT / "data" / "sombra_results_pinnacle.jsonl",
        "registered_at": "2026-07-25T00:00:00Z",
        "h7_gate": 50,  # h7-clv-prospectivo-pinnacle-2026 só cobre a população H3
    },
    "H5 (ensemble xG)": {
        "picks": ROOT / "data" / "sombra_h5_picks_pinnacle.jsonl",
        "results": ROOT / "data" / "sombra_h5_results_pinnacle.jsonl",
        "registered_at": "2026-07-25T00:00:00Z",
        "h7_gate": None,
    },
}

MAIN_GATE = 100
WINDOW_END = datetime(2026, 9, 30, tzinfo=UTC)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _eta(matured: int, target: int, rate_per_day: float, now: datetime) -> str:
    if matured >= target:
        return "atingido"
    if rate_per_day <= 0:
        return "sem captura suficiente para estimar (rate=0)"
    days = (target - matured) / rate_per_day
    eta_date = now + timedelta(days=days)
    flag = "  [depois do fim da janela 2026-09-30]" if eta_date > WINDOW_END else ""
    return f"~{days:.0f}d -> {eta_date.date().isoformat()}{flag}"


def _diagnostic(results: list[dict], metric: str) -> str:
    pairs = [(r[metric], r.get("event_id")) for r in results if r.get(metric) is not None]
    n = len(pairs)
    if n < 2:
        return f"    {metric}: amostra insuficiente (n={n})"
    n_games = len({c for _v, c in pairs})
    mean, lo, hi = ci_mean_cluster(pairs, iterations=1000, rng=np.random.default_rng(13))
    sig = "cruza o zero (sem sinal)" if lo <= 0 <= hi else ("SIGNIFICATIVO+" if lo > 0 else "SIGNIFICATIVO-")
    return f"    {metric}: n={n} ({n_games}j) media={mean:+.2%} IC95=[{lo:+.2%}, {hi:+.2%}] {sig}"


def build_report() -> str:
    now = datetime.now(UTC)
    lines = [
        f"PAINEL SOMBRA — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Gate economico (h3/h5): {MAIN_GATE} picks MATURED_ELIGIBLE | Gate antecedente CLV (h7, so H3): 50",
        f"Janela pre-registrada: ate {WINDOW_END.date().isoformat()}",
        "capital_enabled = false em qualquer cenario deste painel (o gate nao autoriza capital sozinho).",
        "",
    ]
    for label, cfg in COHORTS.items():
        picks_path, results_path = cfg["picks"], cfg["results"]
        report = evaluate(picks_path, results_path, min_sample=MAIN_GATE)
        matured = report["classification"]["MATURED_ELIGIBLE"]
        eligible = report["classification"]["PROSPECTIVE_ELIGIBLE"]
        registered_at = datetime.fromisoformat(cfg["registered_at"].replace("Z", "+00:00"))
        elapsed_days = max((now - registered_at).total_seconds() / 86400, 1e-9)
        rate = matured / elapsed_days

        lines.append(f"== {label} ==")
        lines.append(f"  emitidos={report['counts']['emitted']}  elegiveis={eligible}  maturados={matured}/{MAIN_GATE}")
        bar_len = 30
        filled = min(bar_len, round(bar_len * matured / MAIN_GATE))
        lines.append(f"  [{'#' * filled}{'.' * (bar_len - filled)}] {matured / MAIN_GATE:.0%}")
        lines.append(f"  taxa observada: {rate:.3f} picks maturados/dia (desde {registered_at.date().isoformat()})")
        lines.append(f"  ETA gate 100: {_eta(matured, MAIN_GATE, rate, now)}")
        if cfg["h7_gate"]:
            lines.append(f"  ETA gate CLV antecedente (n={cfg['h7_gate']}): {_eta(matured, cfg['h7_gate'], rate, now)}")

        results = _load_jsonl(results_path)
        lines.append("  diagnostico (informacional — NAO e veredito abaixo do n minimo pre-registrado):")
        lines.append(_diagnostic(results, "clv"))
        lines.append(_diagnostic(results, "pnl"))
        lines.append("")

    lines.append(
        "Lembrete: um sinal positivo aqui antes do n minimo ja enganou o proprio time uma vez "
        "(H1 vs abertura-fantasma, ROI +7.9% -> -7.8% no fechamento real). Nao usar estes numeros "
        "para nenhuma decisao de capital."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="tambem grava data/shadow_dashboard.json")
    args = parser.parse_args()
    text = build_report()
    print(text)
    if args.json:
        now = datetime.now(UTC)
        payload = {"generated_at": now.isoformat(), "report_text": text}
        out = ROOT / "data" / "shadow_dashboard.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n[gravado: {out.relative_to(ROOT)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
