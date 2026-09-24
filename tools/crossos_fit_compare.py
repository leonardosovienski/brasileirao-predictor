"""BR-F018: compara dois relatórios de tools/crossos_fit_report.py (ex.: ubuntu-latest × windows-latest).

Tolerâncias declaradas antes de medir (predictor-qualification,
qualification/brasileirao/BR_F018_FIX_PLAN.json, commit 497715f):
  * parâmetros do ajuste (qualquer valor sob a chave "params"): |Δ| <= 1e-6;
  * todo outro número de ponto flutuante (probabilidades, lambdas, Elo, climatologia, scores,
    Δ, IC, ROI, líquido): |Δ| <= 1e-9;
  * inteiros, textos, booleanos, nulos e a estrutura (chaves, tamanhos): exatamente iguais.
A seção "environment" (plataforma e versões) não é comparada.

Uso: python tools/crossos_fit_compare.py <a.json> <b.json> [--out <json>]   (exit 1 se violar)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PARAM_ATOL = 1e-6
FLOAT_ATOL = 1e-9


def walk(a, b, path: str, in_params: bool, stats: dict, violations: list) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            violations.append(
                {
                    "path": path,
                    "why": "chaves diferentes",
                    "only_a": sorted(set(a) - set(b))[:5],
                    "only_b": sorted(set(b) - set(a))[:5],
                }
            )
            return
        for key in sorted(a):
            if path == "" and key == "environment":
                continue
            walk(a[key], b[key], f"{path}/{key}", in_params or key == "params", stats, violations)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            violations.append({"path": path, "why": f"tamanhos {len(a)} x {len(b)}"})
            return
        for index, (x, y) in enumerate(zip(a, b, strict=True)):
            walk(x, y, f"{path}[{index}]", in_params, stats, violations)
        return
    if isinstance(a, float) or isinstance(b, float):
        if (
            isinstance(a, bool)
            or isinstance(b, bool)
            or not isinstance(a, (int, float))
            or not isinstance(b, (int, float))
        ):
            violations.append({"path": path, "why": "tipos diferentes"})
            return
        kind = "params" if in_params else "float"
        gap = abs(float(a) - float(b))
        stats[kind]["compared"] += 1
        stats[kind]["max_abs_diff"] = max(stats[kind]["max_abs_diff"], gap)
        stats[kind]["differing"] += gap > 0.0
        if gap > (PARAM_ATOL if in_params else FLOAT_ATOL):
            violations.append({"path": path, "why": f"|Δ| = {gap:.3e}"})
        return
    stats["exact"]["compared"] += 1
    if a != b:
        stats["exact"]["differing"] += 1
        violations.append({"path": path, "why": "valor discreto diferente"})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    a = json.loads(args.a.read_text(encoding="utf-8"))
    b = json.loads(args.b.read_text(encoding="utf-8"))
    stats = {
        "params": {"compared": 0, "differing": 0, "max_abs_diff": 0.0, "atol": PARAM_ATOL},
        "float": {"compared": 0, "differing": 0, "max_abs_diff": 0.0, "atol": FLOAT_ATOL},
        "exact": {"compared": 0, "differing": 0},
    }
    violations: list = []
    walk(a, b, "", False, stats, violations)
    doc = {
        "schema": "brasileirao/CROSSOS_FIT_COMPARE/1",
        "a": {"file": args.a.name, **a.get("environment", {})},
        "b": {"file": args.b.name, **b.get("environment", {})},
        "stats": stats,
        "violations": len(violations),
        "first_violations": violations[:20],
        "within_tolerance": not violations,
    }
    text = json.dumps(doc, indent=1, ensure_ascii=False)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
