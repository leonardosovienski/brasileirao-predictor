"""BR-F018: ajuste e walk-forward sobre os vetores sintéticos CONGELADOS, para comparar sistemas operacionais.

Monta o mesmo caminho do worker de pesquisa (_information → _targets → walkforward →
evaluate_with_prices), com os objetos de referência de tests/conformance/fixtures.py, sobre o
dataset sintético da suíte de conformidade (build_dataset, seed fixa; nenhum dado real), e grava
os refits mensais diretos (_fit_goal_model) e o resultado de cada pedido. O CI roda isto em
ubuntu-latest e windows-latest e compara com tools/crossos_fit_compare.py.

Uso: python tools/crossos_fit_report.py --out <json>
"""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from conformance import fixtures  # noqa: E402

from brasileirao_predictor.research_runtime import worker  # noqa: E402

REQUESTS = [(target, baseline) for target in ("1X2", "OU25") for baseline in ("climatology", "market")]
BASELINES = {"climatology": fixtures.BASELINE_CLIM, "market": fixtures.BASELINE_MARKET}


def _months(first: datetime, last: datetime) -> list[datetime]:
    out, current = [], first
    while current <= last:
        out.append(current)
        current = datetime(current.year + (current.month == 12), current.month % 12 + 1, 1, tzinfo=UTC)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg = fixtures.MODEL_CONFIG["config"]
    report: dict = {
        "schema": "brasileirao/CROSSOS_FIT_REPORT/1",
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "numpy": version("numpy"),
            "scipy": version("scipy"),
            "brasileirao_predictor": version("brasileirao-predictor"),
        },
        "vectors": "tests/conformance/fixtures.py build_dataset() (sintético, seed fixa)",
        "refits": [],
        "requests": [],
    }
    with tempfile.TemporaryDirectory() as tmp:
        dataset = fixtures.build_dataset(Path(tmp) / "synthetic.sqlite3")
        conn = sqlite3.connect(f"{dataset.resolve().as_uri()}?mode=ro", uri=True)
        try:
            as_of = worker.parse_instant(fixtures.AS_OF, "as_of")
            info_all = worker._information(conn, as_of)
            for refit_at in _months(datetime(2021, 6, 1, tzinfo=UTC), datetime(2023, 12, 1, tzinfo=UTC)):
                fit_info = [r for r in info_all if r["available_at"] < refit_at]
                params = worker._fit_goal_model(fit_info, refit_at, cfg)
                report["refits"].append(
                    {"refit_at": worker._z(refit_at), "params": None if params is None else [float(p) for p in params]}
                )
            for target, baseline in REQUESTS:
                request = fixtures.request(
                    f"brasileirao:REQ-CROSSOS-{target}-{baseline}", target=target, baseline=baseline
                )
                data_cutoff = worker.parse_instant(request["data_cutoff"], "data_cutoff")
                lead = timedelta(minutes=int(request["decision_lead_minutes"]))
                targets, quality = worker._targets(conn, request, data_cutoff, lead)
                info = [r for r in info_all if r["available_at"] < data_cutoff]
                decisions, _audit = worker.walkforward(info, targets, cfg, worker.GoalModelCache())
                refs = {
                    "model": fixtures.MODEL_CONFIG,
                    "features": fixtures.FEATURES,
                    "baseline": BASELINES[baseline],
                    "cost_model": fixtures.COST_MODEL,
                    "odds": fixtures.ODDS,
                }
                outcome = worker.evaluate_with_prices(request, refs, targets, decisions, quality)
                report["requests"].append(
                    {"request": f"{target}-{baseline}", "decisions": decisions, "outcome": outcome}
                )
        finally:
            conn.close()
    args.out.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"refits": len(report["refits"]), "requests": len(report["requests"]), **report["environment"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
