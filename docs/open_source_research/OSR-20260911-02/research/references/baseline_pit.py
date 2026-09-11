from __future__ import annotations
import math,hashlib,json,sqlite3
from typing import Any
from collections.abc import Iterable
from datetime import UTC,datetime

CLOSING_DEFINITION_VERSION = "closing-v2:last-observed-state-single-contract"


MAPPING_VERSION = "brasileirao-club-aliases/1.0"


SCHEMA = """
CREATE TABLE IF NOT EXISTS curated_matches (
    source TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    canonical_match_id TEXT NOT NULL,
    kickoff_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    raw_home_team TEXT NOT NULL,
    raw_away_team TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_goals INTEGER,
    away_goals INTEGER,
    mapping_version TEXT NOT NULL,
    mapping_status TEXT NOT NULL CHECK(mapping_status IN
      ('EXACT','RULE_BASED','MANUAL_CONFIRMED','AMBIGUOUS','REJECTED')),
    data_quality_status TEXT NOT NULL,
    backfill_batch_id TEXT NOT NULL,
    provenance_hash TEXT NOT NULL,
    match_status TEXT NOT NULL,
    PRIMARY KEY(source, source_match_id, ingested_at, provenance_hash)
);
CREATE INDEX IF NOT EXISTS idx_curated_match_key
  ON curated_matches(canonical_match_id, kickoff_at);

CREATE TABLE IF NOT EXISTS curated_odds (
    source TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    canonical_match_id TEXT NOT NULL,
    kickoff_at TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    published_at TEXT,
    available_at TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    raw_odds REAL CHECK(raw_odds IS NULL OR raw_odds > 1.0),
    normalized_probability REAL,
    is_closing INTEGER NOT NULL DEFAULT 0 CHECK(is_closing IN (0,1)),
    closing_definition_version TEXT,
    mapping_version TEXT NOT NULL,
    mapping_status TEXT NOT NULL,
    data_quality_status TEXT NOT NULL,
    backfill_batch_id TEXT NOT NULL,
    provenance_hash TEXT NOT NULL,
    period TEXT NOT NULL,
    line REAL,
    line_key TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY(source, source_match_id, bookmaker, market, selection, period, line_key, captured_at, provenance_hash)
);
CREATE INDEX IF NOT EXISTS idx_curated_odds_pit
  ON curated_odds(canonical_match_id, market, selection, bookmaker, captured_at);

CREATE TABLE IF NOT EXISTS entity_mappings (
    source TEXT NOT NULL,
    raw_name TEXT NOT NULL,
    canonical_name TEXT,
    rule TEXT NOT NULL,
    mapping_version TEXT NOT NULL,
    mapping_status TEXT NOT NULL,
    reviewed_at TEXT,
    evidence TEXT,
    PRIMARY KEY(source, raw_name, mapping_version)
);

CREATE TABLE IF NOT EXISTS raw_files (
    batch_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    path TEXT NOT NULL,
    source_version TEXT,
    retrieved_at TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    row_count INTEGER,
    temporal_coverage TEXT,
    license TEXT,
    parser_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS curated_schema (version TEXT PRIMARY KEY);
INSERT OR IGNORE INTO curated_schema VALUES ('pit-curated/2.0');
PRAGMA user_version=2;
"""


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} deve ser ISO-8601 com timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} inválido") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} deve conter timezone")
    return parsed.astimezone(UTC)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _provenance(row: dict[str, Any]) -> str:
    encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )
    return _hash_bytes(encoded)


def valid_price(value: Any) -> bool:
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value > 1.0
    except OverflowError:
        return False


def curate_odds(
    conn: sqlite3.Connection,
    row: dict[str, Any],
    *,
    canonical_match_id: str,
    batch_id: str,
    mapping_status: str = "EXACT",
) -> None:
    """Insere uma observação de preço com todos os relógios PIT explícitos."""
    required = (
        "source",
        "source_match_id",
        "kickoff_at",
        "observed_at",
        "available_at",
        "captured_at",
        "bookmaker",
        "market",
        "selection",
    )
    if any(row.get(field) in (None, "") for field in required):
        raise ValueError("odd curada sem campo obrigatório")
    kickoff = _utc(row["kickoff_at"], "kickoff_at")
    observed = _utc(row["observed_at"], "observed_at")
    available = _utc(row["available_at"], "available_at")
    captured = _utc(row["captured_at"], "captured_at")
    status = row.get("status", "UNKNOWN")
    period = row.get("period", "UNKNOWN")
    if status not in {"ACTIVE", "SUSPENDED", "CLOSED", "INVALID", "UNKNOWN"}:
        raise ValueError("status de preço inválido")
    if period not in {"FT", "1H", "2H", "UNKNOWN"}:
        raise ValueError("período de preço inválido")
    price = row.get("raw_odds")
    if (price is not None and not valid_price(price)) or (status == "ACTIVE" and price is None):
        raise ValueError("raw_odds inválida")
    line = row.get("line")
    if line is not None and (isinstance(line, bool) or not isinstance(line, (int, float)) or not math.isfinite(line)):
        raise ValueError("linha deve ser finita ou desconhecida")
    line_key = "" if line is None else str(float(line) if line != 0 else 0.0)
    normalized = row.get("normalized_probability")
    if normalized is not None and (
        isinstance(normalized, bool)
        or not isinstance(normalized, (int, float))
        or not math.isfinite(normalized)
        or not 0 <= normalized <= 1
    ):
        raise ValueError("probabilidade normalizada inválida")
    if available > captured or captured >= kickoff:
        raise ValueError("odd não é pré-evento ou available_at posterior à captura")
    if observed > captured:
        raise ValueError("observed_at posterior à captura")
    published = None
    if row.get("published_at") is not None:
        published = _utc(row["published_at"], "published_at")
        if published > captured:
            raise ValueError("published_at posterior à captura")
    payload = {
        **row,
        "canonical_match_id": canonical_match_id,
        "batch_id": batch_id,
        "mapping_version": MAPPING_VERSION,
    }
    conn.execute(
        """INSERT OR IGNORE INTO curated_odds VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            row["source"],
            str(row["source_match_id"]),
            canonical_match_id,
            kickoff.isoformat(),
            observed.isoformat(),
            published.isoformat() if published is not None else None,
            available.isoformat(),
            captured.isoformat(),
            row["bookmaker"],
            row["market"],
            row["selection"],
            float(price) if price is not None else None,
            normalized,
            int(row.get("is_closing", 0)),
            row.get("closing_definition_version"),
            MAPPING_VERSION,
            mapping_status,
            row.get("data_quality_status", "OK"),
            batch_id,
            _provenance(payload),
            period,
            line,
            line_key,
            status,
        ),
    )
    conn.commit()


def choose_closing(
    rows: Iterable[dict[str, Any]],
    *,
    kickoff_at: str,
    bookmaker: str,
    market: str,
    selection: str,
    max_window_hours: float = 72.0,
) -> dict[str, Any] | None:
    """Último estado observado de um único contrato; nunca prova execução.

    O chamador deve separar fonte, evento, período e linha. Identidade ausente
    ou misturada é erro. Estado final inválido, desconhecido ou conflitante
    implica abstenção, sem procurar uma cotação ativa anterior.
    """
    if (
        isinstance(max_window_hours, bool)
        or not isinstance(max_window_hours, (int, float))
        or not math.isfinite(max_window_hours)
        or max_window_hours <= 0
    ):
        raise ValueError("janela deve ser positiva e finita")
    kickoff = _utc(kickoff_at, "kickoff_at")
    candidates = []
    identities = set()
    for row in rows:
        if row.get("bookmaker") != bookmaker or row.get("market") != market or row.get("selection") != selection:
            continue
        captured = _utc(row.get("captured_at"), "captured_at")
        for field in ("observed_at", "available_at", "published_at"):
            if row.get(field) is not None and _utc(row[field], field) > captured:
                raise ValueError(f"{field} posterior à captura")
        if row.get("kickoff_at") is not None and _utc(row["kickoff_at"], "kickoff_at") != kickoff:
            raise ValueError("kickoff do contrato diverge da referência")
        if captured >= kickoff or (kickoff - captured).total_seconds() > max_window_hours * 3600:
            continue
        required = ("source", "source_match_id", "period")
        if any(not isinstance(row.get(field), str) or not row[field].strip() for field in required):
            raise ValueError("closing requer identidade, fonte e período explícitos")
        identities.add(
            tuple(row.get(field) for field in ("source", "source_match_id", "canonical_match_id", "line", "period"))
        )
        candidates.append((captured, row))
    if len(identities) > 1:
        raise ValueError("closing mistura eventos, fontes ou contratos")
    if not candidates:
        return None
    latest = max(captured for captured, _ in candidates)
    states = [row for captured, row in candidates if captured == latest]
    signatures = {(row.get("raw_odds"), row.get("status"), row.get("data_quality_status", "OK")) for row in states}
    if len(signatures) != 1:
        return None
    chosen = states[0]
    if (
        not valid_price(chosen.get("raw_odds"))
        or chosen.get("status") != "ACTIVE"
        or chosen.get("period") not in {"FT", "1H", "2H"}
        or chosen.get("data_quality_status", "OK") != "OK"
    ):
        return None
    return {
        **chosen,
        "is_closing": 1,
        "closing_definition_version": CLOSING_DEFINITION_VERSION,
        "closing_scope": "last_observed_state_not_commercial_closing",
        "economic_evidence_eligible": False,
    }


def pit_eligible(*, available_at: str, predicted_at: str, kickoff_at: str) -> bool:
    available = _utc(available_at, "available_at")
    predicted = _utc(predicted_at, "predicted_at")
    kickoff = _utc(kickoff_at, "kickoff_at")
    return available <= predicted < kickoff


def evaluation_view(conn: sqlite3.Connection, *, predicted_at: str) -> list[dict[str, Any]]:
    """Latest admissible receipt per source event; never arbitrate tied conflicts.

    Rank before the kickoff filter: a newer cancellation/postponement must not
    resurrect an older version just because the older date matches a filter.
    This is a source view, not a label-admission or trading authorization.
    """
    predicted_at = _utc(predicted_at, "predicted_at").isoformat()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT * FROM (SELECT *, DENSE_RANK() OVER (
            PARTITION BY source, source_match_id ORDER BY ingested_at DESC) AS receipt_rank
            FROM curated_matches WHERE ingested_at <= ?) WHERE receipt_rank=1""",
        (predicted_at,),
    ).fetchall()
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in rows:
        row = {k: raw[k] for k in raw.keys() if k != "receipt_rank"}
        key = (row["source"], row["source_match_id"])
        previous = selected.get(key)

        def material(r):
            return {k: v for k, v in r.items() if k not in {"provenance_hash", "backfill_batch_id"}}

        if previous is not None and material(previous) != material(row):
            raise ValueError("revisões de partida conflitantes no mesmo recebimento")
        selected[key] = row
    return sorted(
        [
            r
            for r in selected.values()
            if r["kickoff_at"] > predicted_at and r["match_status"] in {"SCHEDULED", "UNKNOWN"}
        ],
        key=lambda r: (r["kickoff_at"], r["canonical_match_id"]),
    )
