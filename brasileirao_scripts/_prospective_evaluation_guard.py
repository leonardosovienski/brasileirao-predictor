"""One-shot evaluation guard shared by the prospective H14/H15 entry points.

An exclusive claim precedes all reads and calculations. Success or failure keeps
the claim; only a below-threshold response releases it. A crash never authorizes
an automatic retry. Resolving a retained claim requires a governance decision.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class EvaluationBlocked(RuntimeError):
    """A previous report/attempt prevents another prospective evaluation."""


def claim_directory(*, trial: str, ledger_path: Path) -> Path:
    """Anchor state beside the canonical ledger, independently of other paths.

    The parent directory anchors the dataset and the key uses trial + canonical
    ledger basename. Moving that directory with its claim state preserves the
    lock. Neither registry path nor report destination authorizes another try.
    No ledger contents are read; deliberate dataset copies/renames are outside
    this filesystem guard and remain subject to the same governance policy.
    """
    ledger = Path(ledger_path).resolve()
    identity = json.dumps([trial, os.path.normcase(ledger.name)])
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return ledger.parent / ".prospective_evaluation_claims" / digest


def _claim_path(claim_dir: Path, prefix: str) -> Path:
    if not re.fullmatch(r"h(?:14|15)", prefix):
        raise ValueError("Unsupported prospective evaluation prefix.")
    return claim_dir / f".{prefix}_evaluation.claim.json"


def require_available(reports_dir: Path, prefix: str, *, claim_dir: Path) -> None:
    """Check before CLI dispatch; exclusive claim creation also closes races."""
    claim = _claim_path(claim_dir, prefix)
    if any(reports_dir.glob(f"{prefix}_avaliacao_*.json")) or claim.exists() or claim.is_symlink():
        raise EvaluationBlocked(
            f"{prefix.upper()}: relatório ou tentativa anterior já existe. "
            "Nenhuma avaliação foi executada; nova tentativa exige decisão explícita de governança."
        )


def evaluate_once(
    calculate: Callable[[], dict[str, Any]], *, reports_dir: Path, claim_dir: Path, prefix: str, trial: str
) -> dict[str, Any]:
    """Persist an exclusive report before exposing a completed calculation."""
    reports_dir = Path(reports_dir)
    claim_dir = Path(claim_dir)
    require_available(reports_dir, prefix, claim_dir=claim_dir)
    existed = claim_dir.exists()
    claim_dir.mkdir(parents=True, exist_ok=True)
    claim = _claim_path(claim_dir, prefix)
    try:
        stream = claim.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise EvaluationBlocked(
            f"{prefix.upper()}: outra tentativa já possui o claim exclusivo; nenhuma avaliação foi executada."
        ) from exc
    # A partially written claim is intentionally blocking after any failure.
    with stream:
        info = os.fstat(stream.fileno())
        identity = (info.st_dev, info.st_ino)
        json.dump(
            {
                "trial": trial,
                "attempt_id": uuid.uuid4().hex,
                "claimed_at_utc": datetime.now(UTC).isoformat(),
                "policy": "retained_on_success_error_or_crash; released_only_below_threshold",
            },
            stream,
            ensure_ascii=False,
            allow_nan=False,
        )
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    # Another, older implementation may have created a report before claiming.
    if any(reports_dir.glob(f"{prefix}_avaliacao_*.json")):
        raise EvaluationBlocked(f"{prefix.upper()}: relatório existente; nenhuma avaliação foi executada.")
    result = calculate()
    if result.get("status") == "AGUARDANDO_N":
        # Release only the exact file created above, never another caller's claim.
        info = claim.stat()
        if claim.is_symlink() or (info.st_dev, info.st_ino) != identity:
            raise EvaluationBlocked("Claim identity changed; refusing automatic release.")
        claim.unlink()
        if not existed:
            try:
                claim_dir.rmdir()  # only this newly created, now-empty directory
            except OSError:
                pass
        return result
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%S%fZ")
    report = reports_dir / f"{prefix}_avaliacao_{timestamp}.json"
    temporary = reports_dir / f".{report.name}.{uuid.uuid4().hex}.pending"
    temporary_identity = None
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            temporary_identity = (info.st_dev, info.st_ino)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Same-filesystem hardlink publishes the complete inode atomically and
        # refuses an existing name. Unsupported filesystems fail closed; never
        # fall back to a copy or rename that may overwrite a prior report.
        os.link(temporary, report)
    finally:
        if temporary_identity is not None and temporary.exists() and not temporary.is_symlink():
            info = temporary.stat()
            if (info.st_dev, info.st_ino) == temporary_identity:
                temporary.unlink()
    return result
