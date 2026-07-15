"""Read-only, deterministic report for the pre-registered H3 shadow ledger."""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = "shadow-report/v1"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path.name}:{number} is not a JSON object")
            rows.append(row)
    return rows


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _mean(values: list[float]) -> float | None:
    return round(st.fmean(values), 6) if values else None


def _median(values: list[float]) -> float | None:
    return round(st.median(values), 6) if values else None


def _bootstrap_mean(values: list[float], seed: int = 13) -> dict[str, float] | None:
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(st.fmean(rng.choice(values) for _ in values) for _ in range(2000))
    return {"method": "iid bootstrap, 2000 replicates, seed=13", "lower_95": round(means[49], 6), "upper_95": round(means[1949], 6)}


def _bin(probability: float) -> str:
    lower = min(int(probability * 5) * 0.2, 0.8)
    return f"{lower:.1f}-{lower + 0.2:.1f}"


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnl = [float(row["pnl"]) for row in rows if isinstance(row.get("pnl"), (int, float))]
    clv = [float(row["clv"]) for row in rows if isinstance(row.get("clv"), (int, float))]
    scored = [(float(row["model_prob"]), int(row["won"])) for row in rows if isinstance(row.get("model_prob"), (int, float)) and row.get("won") in (0, 1)]
    losses = [-(y * math.log(max(p, 1e-12)) + (1 - y) * math.log(max(1 - p, 1e-12))) for p, y in scored]
    brier = [(p - y) ** 2 for p, y in scored]
    drawdown = 0.0
    peak = cumulative = 0.0
    for value in pnl:
        cumulative += value
        peak = max(peak, cumulative)
        drawdown = min(drawdown, cumulative - peak)
    return {
        "matured": len(rows), "win_rate": _mean([float(row["won"]) for row in rows if row.get("won") in (0, 1)]),
        "roi_gross": _mean(pnl), "roi_costs": None, "costs_note": "NÃO DISPONÍVEL: custos não são definidos no ledger H3.",
        "clv_mean": _mean(clv), "clv_median": _median(clv), "clv_positive_rate": _mean([1.0 if value > 0 else 0.0 for value in clv]),
        "clv_distribution": {"negative": sum(value < 0 for value in clv), "zero": sum(value == 0 for value in clv), "positive": sum(value > 0 for value in clv)},
        "brier": _mean(brier), "rps_binary": _mean(brier), "log_loss": _mean(losses),
        "odds_mean": _mean([float(row["odd"]) for row in rows if isinstance(row.get("odd"), (int, float))]),
        "ev_predicted": _mean([float(row["edge"]) for row in rows if isinstance(row.get("edge"), (int, float))]),
        "pnl_total": round(sum(pnl), 6), "drawdown_units": round(drawdown, 6),
        "roi_bootstrap_95": _bootstrap_mean(pnl), "clv_bootstrap_95": _bootstrap_mean(clv), "effective_sample_size": len(rows),
    }


def _calibration(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for row in rows:
        if isinstance(row.get("model_prob"), (int, float)) and row.get("won") in (0, 1):
            buckets[_bin(float(row["model_prob"]))].append((float(row["model_prob"]), int(row["won"])))
    return [{"bin": key, "count": len(values), "predicted_mean": _mean([p for p, _ in values]), "observed_frequency": _mean([float(y) for _, y in values]), "calibration_error": round(abs(st.fmean(p for p, _ in values) - st.fmean(y for _, y in values)), 6), "confidence_interval": None} for key, values in sorted(buckets.items())]


def build_report(picks_path: Path, results_path: Path, start: str | None = None, end: str | None = None) -> dict[str, Any]:
    picks = _load_jsonl(picks_path)
    results = _load_jsonl(results_path)
    exclusions: Counter[str] = Counter()
    unique_picks: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in picks:
        key = (row.get("event_id"), row.get("selection"))
        if None in key:
            exclusions["pick_missing_key"] += 1
        elif key in unique_picks:
            exclusions["duplicate_pick"] += 1
        else:
            unique_picks[key] = row
    unique_results: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in results:
        key = (row.get("event_id"), row.get("selection"))
        if None in key or key not in unique_picks:
            exclusions["result_without_pick"] += 1
        elif key in unique_results:
            exclusions["duplicate_result"] += 1
        else:
            unique_results[key] = row
    included: list[dict[str, Any]] = []
    temporal: Counter[str] = Counter()
    for key, pick in unique_picks.items():
        captured, event_day = _utc(pick.get("captured_at")), _event_date(pick.get("date"))
        if captured is None or event_day is None:
            exclusions["invalid_capture_or_event_date"] += 1
            continue
        if start and str(event_day) < start or end and str(event_day) > end:
            exclusions["outside_filter"] += 1
            continue
        if captured.date() > event_day:
            exclusions["capture_after_event_date"] += 1
            continue
        temporal["valid_date_order" if captured.date() < event_day else "kickoff_time_unavailable"] += 1
        result = unique_results.get(key)
        if result is None:
            continue
        settled = _utc(result.get("settled_at"))
        if settled is None or settled < captured:
            exclusions["invalid_settlement_order"] += 1
            continue
        combined = {**pick, **result}
        included.append(combined)
    open_count = sum(1 for key in unique_picks if key not in unique_results)
    period = sorted(str(row.get("date")) for row in unique_picks.values() if row.get("date"))
    metrics = _metrics(included)
    segments = {"selection": {selection: _metrics([row for row in included if row.get("selection") == selection]) for selection in ("over", "under")}, "capture_turn": "NÃO DISPONÍVEL: ledger não registra a tarefa manhã/noite.", "market": {market: _metrics([row for row in included if row.get("market") == market]) for market in sorted({str(row.get("market")) for row in included})}}
    if not included:
        classification = "DADOS INSUFICIENTES"
    elif len(included) < 100:
        classification = "INCONCLUSIVO"
    else:
        classification = "INCONCLUSIVO"
    return {"schema_version": SCHEMA_VERSION, "inputs": {"picks": str(picks_path), "results": str(results_path), "filters": {"from": start, "to": end}}, "period": {"first_event_date": period[0] if period else None, "last_event_date": period[-1] if period else None}, "counts": {"pick_records": len(picks), "unique_picks": len(unique_picks), "matured": len(included), "open": open_count, "result_records": len(results)}, "exclusions": dict(sorted(exclusions.items())), "temporal_validation": dict(sorted(temporal.items())), "metrics": metrics, "calibration": _calibration(included), "segments": segments, "capturability": {"capture_vs_open": "NÃO DISPONÍVEL: ledger não registra odd de abertura separada.", "capture_vs_close": "NÃO DISPONÍVEL: ledger registra CLV, mas não a odd de fechamento bruta.", "captured_odds_available": sum(isinstance(row.get("odd"), (int, float)) for row in unique_picks.values()), "capture_turn": segments["capture_turn"]}, "limitations": ["predicted_at e kickoff timestamp não estão no ledger H3.", "Não há resultados maturados se sombra_results.jsonl estiver ausente ou vazio.", "Custos, fonte de odds, odd de abertura e odd de fechamento bruta não são registrados pelo ledger atual."], "classification": classification, "next_sample_milestone": "100 picks liquidados, conforme H3 pré-registrada; não reavaliar como GO antes desse marco."}


def _human(report: dict[str, Any]) -> str:
    counts, metrics = report["counts"], report["metrics"]
    return "\n".join(["H3 modo sombra — relatório somente leitura", f"Período: {report['period']['first_event_date'] or 'NÃO DISPONÍVEL'} a {report['period']['last_event_date'] or 'NÃO DISPONÍVEL'}", f"Picks únicos: {counts['unique_picks']} | maturados: {counts['matured']} | abertos: {counts['open']}", f"ROI bruto: {metrics['roi_gross']} | CLV médio: {metrics['clv_mean']} | classificação: {report['classification']}", f"Limite: {report['next_sample_milestone']}"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a read-only deterministic H3 shadow report.")
    parser.add_argument("--db", default=str(ROOT / "data" / "matches.db"), help="Recorded for provenance only; this reporter does not open it.")
    parser.add_argument("--from", dest="start")
    parser.add_argument("--to", dest="end")
    parser.add_argument("--json", action="store_true", help="Write structured JSON to stdout.")
    parser.add_argument("--output", type=Path, help="Write the same structured JSON to this path.")
    parser.add_argument("--strict", action="store_true", help="Return 2 when exclusions or temporal uncertainty are present.")
    args = parser.parse_args(argv)
    report = build_report(ROOT / "data" / "sombra_picks.jsonl", ROOT / "data" / "sombra_results.jsonl", args.start, args.end)
    report["inputs"]["database_argument"] = args.db
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded if args.json else _human(report))
    return 2 if args.strict and (report["exclusions"] or report["temporal_validation"].get("kickoff_time_unavailable")) else 0


if __name__ == "__main__":
    raise SystemExit(main())
