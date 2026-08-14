"""report_h9_execution_quality — leitura somente-leitura de
data/research/h9_emission_attempts.jsonl (gravado por emit_h9_shadow.py a
CADA fixture avaliada, não só as emitidas).

Responde duas perguntas de "prova de executabilidade" que nenhum outro
relatório do projeto responde ainda:

    1. Disponibilidade real da odd do book aprovado no instante da decisão —
       quantos JOGOS terminam em EMITTED vs BLOCKED_NO_STABLE_BOOKMAKER
       (sem casa aprovada no ledger de estabilidade) vs NO_EXECUTABLE_QUOTE
       (casa aprovada não tinha cotação elegível para aquele jogo).
    2. Diferença entre o melhor preço observado (qualquer bookmaker coletado,
       mesma seleção, mesmo instante) e o preço realmente aceito (só o book
       aprovado) — slippage_vs_best negativo = aceitamos pior preço do que
       o mercado oferecia; positivo/zero = o book aprovado já era o melhor.

`emit_h9_shadow.py` roda a cada ~15min e grava UMA linha por (jogo, execução)
enquanto o jogo estiver na janela de decisão (~105min) — um jogo pode gerar
várias tentativas antes de emitir (ou nunca emitir). As taxas de disponibilidade
são calculadas por JOGO (o último status visto, com EMITTED vencendo qualquer
tentativa anterior), não por linha bruta — senão um jogo que emite na 3ª
tentativa conta como maioria de falhas e distorce a taxa pra baixo.
`total_raw_evaluations` preserva a contagem bruta de ticks só como contexto
operacional (quanto polling aconteceu), não entra em nenhuma taxa.

Não abre matches.db, não decide nada, não escreve nada.

Uso:
    python scripts/report_h9_execution_quality.py
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ATTEMPTS_PATH = ROOT / "data" / "research" / "h9_emission_attempts.jsonl"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _final_status_by_event(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reduz a série de tentativas por jogo a UMA linha: a primeira que
    emitiu, se alguma emitiu (ticks seguintes, sempre ALREADY_EMITTED, não
    sobrescrevem); senão, a última tentativa vista. Linhas sem `event_id`
    são descartadas — não há por onde agrupá-las."""
    final: dict[Any, dict[str, Any]] = {}
    for row in rows:
        event_id = row.get("event_id")
        if event_id is None:
            continue
        if final.get(event_id, {}).get("status") == "EMITTED":
            continue
        final[event_id] = row
    return list(final.values())


def report(attempts_path: Path = ATTEMPTS_PATH) -> dict[str, Any]:
    rows = _load_jsonl(attempts_path)
    per_event = _final_status_by_event(rows)
    total = len(per_event)
    status_counts = Counter(r.get("status") for r in per_event)

    def _rate(status: str) -> float | None:
        return (status_counts.get(status, 0) / total) if total else None

    slippage = [float(r["slippage_vs_best"]) for r in per_event if "slippage_vs_best" in r]
    matched_or_beat_best = sum(1 for s in slippage if s >= 0)

    return {
        "schema_version": "h9-execution-quality/v2",
        "total_raw_evaluations": len(rows),
        "total_games": total,
        "status_counts": dict(status_counts),
        "emission_rate": _rate("EMITTED"),
        "blocked_no_stable_bookmaker_rate": _rate("BLOCKED_NO_STABLE_BOOKMAKER"),
        "no_executable_quote_rate": _rate("NO_EXECUTABLE_QUOTE"),
        "slippage_vs_best_price": {
            "n": len(slippage),
            "mean": round(st.fmean(slippage), 6) if slippage else None,
            "median": round(st.median(slippage), 6) if slippage else None,
            "matched_or_beat_best_rate": (matched_or_beat_best / len(slippage)) if slippage else None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
