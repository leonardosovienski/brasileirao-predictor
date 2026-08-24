"""JSONL append-only para paper-trading, sem qualquer caminho de execução real."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.research.prospective_validation.contracts import PaperPick, PaperSettlement


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n")


def append_pick(path: Path, pick: PaperPick) -> None:
    if any(row.get("pick_id") == pick.pick_id for row in _rows(path)):
        raise ValueError("duplicate pick_id")
    _append(path, {"kind": "pick", **pick.model_dump(mode="json"), "record_hash": pick.record_hash})


def append_settlement(path: Path, settlement: PaperSettlement, pick: PaperPick) -> None:
    settlement.assert_matches(pick)
    if any(row.get("kind") == "settlement" and row.get("pick_id") == pick.pick_id for row in _rows(path)):
        raise ValueError("duplicate settlement")
    _append(path, {"kind": "settlement", **settlement.model_dump(mode="json")})
