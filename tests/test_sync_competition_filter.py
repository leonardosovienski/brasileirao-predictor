"""O espelho sofascore → matches só copia as competições configuradas.

Sem o filtro, o SELECT varria `sofascore_matches` inteira e carimbava
`tournament_name` em tudo. Hoje a config só tem Série A, então nada quebra —
mas o Roadmap §7/RESEARCH-05 pede histórico de Série B para prior de promovido,
e no dia que ele entrar na mesma base seria espelhado COMO SE fosse Série A,
envenenando ratings e calibração em silêncio.
"""

from __future__ import annotations

import sqlite3

from brasileirao_scripts.sync_matches_from_sofascore import sync
from brasileirao_predictor import db

SERIE_A = "Brasileirão Série A 2024"
SERIE_B = "Brasileirão Série B 2024"


def _conn() -> sqlite3.Connection:
    conn = db.connect(":memory:")  # DDL REAL — schema fabricado no teste diverge do de produção
    linhas = [
        (1, SERIE_A, "2024-04-13", "flamengo", "palmeiras", 2, 1),
        (2, SERIE_A, "2024-04-14", "gremio", "santos", None, None),
        (3, SERIE_B, "2024-04-13", "novorizontino", "mirassol", 1, 0),
    ]
    conn.executemany(
        "INSERT INTO sofascore_matches (event_id, competition, date, home_team, away_team,"
        " home_score, away_score) VALUES (?,?,?,?,?,?,?)",
        linhas,
    )
    conn.commit()
    return conn


def test_so_a_competicao_configurada_e_espelhada() -> None:
    conn = _conn()
    played, fixtures = sync(conn, "Brasileirão Série A", [SERIE_A])
    assert (played, fixtures) == (1, 1)
    times = {r[0] for r in conn.execute("SELECT home_team FROM matches")}
    assert "novorizontino" not in times, "Série B vazou para `matches`"


def test_competicao_extra_configurada_entra() -> None:
    """O filtro não pode ser um hard-code de Série A: quem manda é a config."""
    conn = _conn()
    played, _ = sync(conn, "Brasileirão", [SERIE_A, SERIE_B])
    assert played == 2


def test_upsert_e_idempotente() -> None:
    conn = _conn()
    primeiro = sync(conn, "Brasileirão Série A", [SERIE_A])
    segundo = sync(conn, "Brasileirão Série A", [SERIE_A])
    assert primeiro == segundo
    assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 2
