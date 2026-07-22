"""Backfill histórico point-in-time, isolado do banco vivo.

Este módulo não conhece ``matches.db`` como destino de escrita. Ele oferece
somente três camadas explícitas: raw imutável, curated com proveniência e
views de avaliação PIT. Fontes sem odds temporalmente reconstruíveis podem ser
usadas para cobertura de resultados, mas são marcadas como inelegíveis para
avaliação econômica.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Iterable
import uuid

from predictor_core.data.contracts import DataUnavailableError

RAW_SCHEMA_VERSION = "pit-raw/1.0"
CURATED_SCHEMA_VERSION = "pit-curated/1.0"
CLOSING_DEFINITION_VERSION = "closing-v1:last-valid-pre-kickoff-by-bookmaker"
MAPPING_VERSION = "brasileirao-club-aliases/1.0"

SOURCE_REGISTER = {
    "sofascore": {"status": "SOURCE_ACCEPTED", "economic": True},
    "api_football": {"status": "SOURCE_QUARANTINED", "economic": False},
    "sportmonks": {"status": "SOURCE_PENDING_REVIEW", "economic": False},
}

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
    PRIMARY KEY(source, source_match_id)
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
    raw_odds REAL NOT NULL CHECK(raw_odds > 1.0 AND raw_odds < 1000.0),
    normalized_probability REAL,
    is_closing INTEGER NOT NULL DEFAULT 0 CHECK(is_closing IN (0,1)),
    closing_definition_version TEXT,
    mapping_version TEXT NOT NULL,
    mapping_status TEXT NOT NULL,
    data_quality_status TEXT NOT NULL,
    backfill_batch_id TEXT NOT NULL,
    provenance_hash TEXT NOT NULL,
    PRIMARY KEY(source, source_match_id, bookmaker, market, selection, captured_at)
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
    return parsed.astimezone(timezone.utc)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def connect_curated(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def preserve_raw(raw: bytes | str | Path, destination: str | Path, *,
                 source: str, source_version: str | None,
                 retrieved_at: str, license: str | None,
                 parser_version: str, row_count: int | None,
                 temporal_coverage: str | None, batch_id: str | None = None) -> dict[str, Any]:
    """Grava o arquivo exatamente uma vez e retorna manifesto verificável."""
    _utc(retrieved_at, "retrieved_at")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"raw imutável já existe: {destination}")
    if isinstance(raw, Path):
        data = raw.read_bytes()
    elif isinstance(raw, str):
        data = raw.encode("utf-8")
    else:
        data = bytes(raw)
    destination.write_bytes(data)
    return {
        "schema_version": RAW_SCHEMA_VERSION,
        "batch_id": batch_id or uuid.uuid4().hex,
        "source": source, "path": str(destination),
        "source_version": source_version, "retrieved_at": retrieved_at,
        "sha256": _hash_bytes(data), "file_size": len(data),
        "row_count": row_count, "temporal_coverage": temporal_coverage,
        "license": license, "parser_version": parser_version,
    }


def verify_raw(path: str | Path, manifest: dict[str, Any]) -> None:
    data = Path(path).read_bytes()
    if manifest.get("schema_version") != RAW_SCHEMA_VERSION:
        raise ValueError("manifesto raw incompatível")
    if manifest.get("sha256") != _hash_bytes(data):
        raise ValueError("hash raw divergente")
    if manifest.get("file_size") != len(data):
        raise ValueError("tamanho raw divergente")


def register_raw(conn: sqlite3.Connection, manifest: dict[str, Any]) -> None:
    verify_raw(manifest["path"], manifest)
    conn.execute("""INSERT INTO raw_files VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        manifest["batch_id"], manifest["source"], manifest["path"],
        manifest.get("source_version"), manifest["retrieved_at"],
        manifest["sha256"], manifest["file_size"], manifest.get("row_count"),
        manifest.get("temporal_coverage"), manifest.get("license"),
        manifest["parser_version"]))
    conn.commit()


def resolve_entity(source: str, raw_name: str, aliases: dict[str, str],
                   known: set[str], *, mapping_version: str = MAPPING_VERSION,
                   reviewed_at: str | None = None) -> tuple[str | None, str]:
    """Resolve explicit alias only; nunca faz fuzzy-match silencioso."""
    if raw_name in known:
        return raw_name, "EXACT"
    if raw_name in aliases:
        canonical = aliases[raw_name]
        if canonical not in known:
            return None, "REJECTED"
        return canonical, "RULE_BASED"
    candidates = [name for name in known if name.casefold() == raw_name.casefold()]
    if len(candidates) == 1:
        return candidates[0], "RULE_BASED"
    if len(candidates) > 1:
        return None, "AMBIGUOUS"
    return None, "REJECTED"


def insert_entity_mapping(conn: sqlite3.Connection, *, source: str,
                           raw_name: str, canonical_name: str | None,
                           rule: str, status: str, reviewed_at: str | None,
                           evidence: str | None) -> None:
    if status not in {"EXACT", "RULE_BASED", "MANUAL_CONFIRMED", "AMBIGUOUS", "REJECTED"}:
        raise ValueError("mapping_status inválido")
    conn.execute("INSERT OR REPLACE INTO entity_mappings VALUES (?,?,?,?,?,?,?,?)",
                 (source, raw_name, canonical_name, rule, MAPPING_VERSION,
                  status, reviewed_at, evidence))
    conn.commit()


def _provenance(row: dict[str, Any]) -> str:
    encoded = json.dumps(row, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return _hash_bytes(encoded)


def curate_match(conn: sqlite3.Connection, row: dict[str, Any], *,
                 aliases: dict[str, str], known: set[str], batch_id: str,
                 ingested_at: str) -> str:
    required = ("source", "source_match_id", "kickoff_at", "home_team", "away_team")
    if any(not row.get(field) for field in required):
        raise ValueError("partida curada sem campos obrigatórios")
    kickoff = _utc(row["kickoff_at"], "kickoff_at")
    ingested = _utc(ingested_at, "ingested_at")
    home, hs = resolve_entity(row["source"], row["home_team"], aliases, known)
    away, aws = resolve_entity(row["source"], row["away_team"], aliases, known)
    if hs in {"AMBIGUOUS", "REJECTED"} or aws in {"AMBIGUOUS", "REJECTED"}:
        raise DataUnavailableError("partida rejeitada: entidade sem resolução inequívoca")
    if home == away:
        raise DataUnavailableError("mandante e visitante resolvem para o mesmo clube")
    canonical_id = row.get("canonical_match_id") or (
        f"{kickoff.isoformat()}|{home}|{away}")
    payload = {**row, "canonical_match_id": canonical_id, "home_team": home,
               "away_team": away, "mapping_version": MAPPING_VERSION,
               "mapping_status": "EXACT" if hs == aws == "EXACT" else "RULE_BASED",
               "batch_id": batch_id}
    conn.execute("""INSERT INTO curated_matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(source,source_match_id) DO UPDATE SET
        canonical_match_id=excluded.canonical_match_id,kickoff_at=excluded.kickoff_at,
        ingested_at=excluded.ingested_at,home_team=excluded.home_team,
        away_team=excluded.away_team,home_goals=excluded.home_goals,
        away_goals=excluded.away_goals,mapping_status=excluded.mapping_status,
        data_quality_status=excluded.data_quality_status,
        backfill_batch_id=excluded.backfill_batch_id,provenance_hash=excluded.provenance_hash""",
        (row["source"], str(row["source_match_id"]), canonical_id,
         kickoff.isoformat(), ingested.isoformat(), row["home_team"], row["away_team"],
         home, away, row.get("home_goals"), row.get("away_goals"),
         MAPPING_VERSION, payload["mapping_status"], row.get("data_quality_status", "OK"),
         batch_id, _provenance(payload)))
    conn.commit()
    return canonical_id


def valid_price(value: Any) -> bool:
    return isinstance(value, (int, float)) and value == value and value != float("inf") and value > 1.0


def curate_odds(conn: sqlite3.Connection, row: dict[str, Any], *,
                canonical_match_id: str, batch_id: str,
                mapping_status: str = "EXACT") -> None:
    """Insere uma observação de preço com todos os relógios PIT explícitos."""
    required = ("source", "source_match_id", "kickoff_at", "observed_at",
                "available_at", "captured_at", "bookmaker", "market",
                "selection", "raw_odds")
    if any(row.get(field) in (None, "") for field in required):
        raise ValueError("odd curada sem campo obrigatório")
    kickoff = _utc(row["kickoff_at"], "kickoff_at")
    observed = _utc(row["observed_at"], "observed_at")
    available = _utc(row["available_at"], "available_at")
    captured = _utc(row["captured_at"], "captured_at")
    if not valid_price(row["raw_odds"]):
        raise ValueError("raw_odds inválida")
    if available > captured or captured >= kickoff:
        raise ValueError("odd não é pré-evento ou available_at posterior à captura")
    if row.get("published_at") is not None:
        _utc(row["published_at"], "published_at")
    payload = {**row, "canonical_match_id": canonical_match_id,
               "batch_id": batch_id, "mapping_version": MAPPING_VERSION}
    conn.execute("""INSERT INTO curated_odds VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (row["source"], str(row["source_match_id"]), canonical_match_id,
         kickoff.isoformat(), observed.isoformat(), row.get("published_at"),
         available.isoformat(), captured.isoformat(), row["bookmaker"],
         row["market"], row["selection"], float(row["raw_odds"]),
         row.get("normalized_probability"), int(row.get("is_closing", 0)),
         row.get("closing_definition_version"), MAPPING_VERSION, mapping_status,
         row.get("data_quality_status", "OK"), batch_id, _provenance(payload)))
    conn.commit()


def choose_closing(rows: Iterable[dict[str, Any]], *, kickoff_at: str,
                   bookmaker: str, market: str, selection: str,
                   max_window_hours: float = 72.0) -> dict[str, Any] | None:
    """Última cotação válida antes do kickoff, com janela explícita."""
    kickoff = _utc(kickoff_at, "kickoff_at")
    candidates = []
    for row in rows:
        if row.get("bookmaker") != bookmaker or row.get("market") != market \
                or row.get("selection") != selection or not valid_price(row.get("raw_odds")):
            continue
        captured = _utc(row.get("captured_at"), "captured_at")
        if captured >= kickoff or (kickoff - captured).total_seconds() > max_window_hours * 3600:
            continue
        candidates.append((captured, row))
    if not candidates:
        return None
    _, chosen = max(candidates, key=lambda item: item[0])
    return {**chosen, "is_closing": 1,
            "closing_definition_version": CLOSING_DEFINITION_VERSION}


def pit_eligible(*, available_at: str, predicted_at: str,
                 kickoff_at: str) -> bool:
    available = _utc(available_at, "available_at")
    predicted = _utc(predicted_at, "predicted_at")
    kickoff = _utc(kickoff_at, "kickoff_at")
    return available <= predicted < kickoff


def evaluation_view(conn: sqlite3.Connection, *, predicted_at: str) -> list[sqlite3.Row]:
    """View somente de partidas curadas disponíveis antes da decisão."""
    _utc(predicted_at, "predicted_at")
    conn.row_factory = sqlite3.Row
    return conn.execute("""SELECT * FROM curated_matches
      WHERE kickoff_at > ? AND ingested_at <= ?
        ORDER BY kickoff_at, canonical_match_id""", (predicted_at, predicted_at)).fetchall()


def walk_forward_splits(rows: Iterable[dict[str, Any]], *,
                        development_end: str, validation_end: str,
                        test_end: str) -> dict[str, list[dict[str, Any]]]:
    """Divide por data sem permitir reuso do holdout final."""
    bounds = [_utc(value, name) for value, name in (
        (development_end, "development_end"),
        (validation_end, "validation_end"), (test_end, "test_end"))]
    if not bounds[0] < bounds[1] < bounds[2]:
        raise ValueError("limites walk-forward devem ser estritamente crescentes")
    output = {"development": [], "validation": [], "test": []}
    for row in rows:
        event = _utc(row.get("kickoff_at"), "kickoff_at")
        if event < bounds[0]:
            output["development"].append(row)
        elif event < bounds[1]:
            output["validation"].append(row)
        elif event < bounds[2]:
            output["test"].append(row)
    return output


def cluster_bootstrap_mean(rows: Iterable[dict[str, Any]], field: str,
                           *, iterations: int = 2000, seed: int = 13) -> dict[str, float] | None:
    """IC95 agrupado por rodada/clube; nunca trata partidas do mesmo cluster como independentes."""
    import random
    grouped: dict[Any, list[float]] = {}
    for row in rows:
        value, cluster = row.get(field), row.get("cluster")
        if isinstance(value, (int, float)) and value == value and cluster is not None:
            grouped.setdefault(cluster, []).append(float(value))
    if not grouped:
        return None
    clusters = list(grouped.values())
    means = []
    rng = random.Random(seed)
    for _ in range(iterations):
        sampled = [rng.choice(clusters) for _ in clusters]
        values = [value for cluster in sampled for value in cluster]
        means.append(sum(values) / len(values))
    means.sort()
    return {"mean": sum(v for cluster in clusters for v in cluster) /
            sum(len(cluster) for cluster in clusters),
            "lower_95": means[max(0, int(iterations * 0.025))],
            "upper_95": means[min(iterations - 1, int(iterations * 0.975))],
            "clusters": len(clusters), "iterations": iterations}


def quality_gate(observations: Iterable[dict[str, Any]], *, min_matured: int = 100) -> dict[str, Any]:
    """Relatório conservador: quantidade jamais promove capital automaticamente."""
    rows = list(observations)
    eligible = [row for row in rows if row.get("pit_valid") is True
                and row.get("matured") is True]
    cluster_counts: dict[Any, int] = {}
    club_counts: dict[Any, int] = {}
    for row in eligible:
        cluster_counts[row.get("cluster")] = cluster_counts.get(row.get("cluster"), 0) + 1
        for club in row.get("clubs", ()): club_counts[club] = club_counts.get(club, 0) + 1
    total = len(eligible)
    n = max(total, 1)
    hhi = sum((count / n) ** 2 for count in club_counts.values()) if total else None
    return {
        "status": "GATE_PASSED_FOR_PROSPECTIVE_SHADOW" if total >= min_matured
        else "INSUFFICIENT_SAMPLE",
        "eligible_matches": total, "predictions_emitted": len(rows),
        "matured_labels": total, "clusters": len(cluster_counts),
        "club_hhi": hhi,
        "roi_ic95": cluster_bootstrap_mean(eligible, "pnl"),
        "clv_ic95": cluster_bootstrap_mean(eligible, "clv"),
        "brier_ic95": cluster_bootstrap_mean(eligible, "brier"),
        "capital_enabled": False,
    }
