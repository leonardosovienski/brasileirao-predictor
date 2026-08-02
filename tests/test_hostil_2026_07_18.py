"""Auditoria hostil 2026-07-18 — testes que protegem as correções de robustez.

Eixos cobertos: odds zero/negativas/NaN/Inf no Shin; odds-placeholder do
Sofascore (1.0/1.0/1.0) no _market_probs; liquidação duplicada intra-execução
na sombra; CLV com odd de fechamento inválida; linha inteira (push) na sombra;
placar negativo no record_result; banco truncado; leitura concorrente em WAL.

Nenhum teste aqui altera parâmetro científico — só valida que entrada
inválida produz FALHA CLARA ou exclusão explícita, nunca número errado calado.
"""

import importlib.util
import json
import math
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

from src import db  # noqa: E402
from src.math_utils import shin_probabilities  # noqa: E402
from src.predict import _market_probs  # noqa: E402
from src.settle import record_result  # noqa: E402

spec = importlib.util.spec_from_file_location("sombra_hostil", ROOT / "scripts" / "sombra.py")
sombra = importlib.util.module_from_spec(spec)
sys.modules["sombra_hostil"] = sombra
spec.loader.exec_module(sombra)


# --- Shin: odds degeneradas falham em voz alta -------------------------------


@pytest.mark.parametrize(
    "odds",
    [
        [0.0, 2.0],  # zero: antes ZeroDivisionError cru
        [-1.5, 2.0],  # negativa: antes prob negativa calada
        [float("nan"), 2.0],  # NaN: antes contaminava tudo em silêncio
        [float("inf"), 2.0],  # Inf: pi=0 distorcia a normalização
        [2.0, None],  # ausente dentro da lista
    ],
)
def test_shin_rejeita_odd_invalida_com_erro_claro(odds):
    with pytest.raises(ValueError, match="odd inválida"):
        shin_probabilities(odds)


def test_shin_continua_correto_para_odds_validas():
    p, z, over = shin_probabilities([1.9, 1.9])
    assert p[0] == pytest.approx(0.5, abs=1e-9)
    assert math.isfinite(z) and math.isfinite(over)
    assert p.sum() == pytest.approx(1.0)


# --- _market_probs: linha-placeholder 1.0/1.0/1.0 não vira mercado ----------


def _conn_com_placeholder(tmp_path, com_valida=False):
    conn = db.connect(str(tmp_path / "t.db"))
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, date, home_team, away_team, "
        "odds_home, odds_draw, odds_away, odds_over, odds_under) "
        "VALUES (1, '2026-02-25', 'Bahia', 'Chapecoense', 1.0, 1.0, 1.0, 2.0, 1.8)"
    )
    if com_valida:
        conn.execute(
            "INSERT INTO sofascore_matches (event_id, date, home_team, away_team, "
            "odds_home, odds_draw, odds_away, odds_over, odds_under) "
            "VALUES (2, '2026-07-17', 'Bahia', 'Chapecoense', 2.1, 3.3, 3.6, 2.35, 1.6)"
        )
    conn.commit()
    return conn


def test_market_probs_ignora_placeholder_1x2_todo_em_1(tmp_path):
    conn = _conn_com_placeholder(tmp_path)
    # única linha do confronto é placeholder → sem mercado (antes: p=1/3 fake)
    assert _market_probs(conn, "Bahia", "Chapecoense") is None


def test_market_probs_escolhe_a_linha_valida_e_pula_a_placeholder(tmp_path):
    conn = _conn_com_placeholder(tmp_path, com_valida=True)
    mk = _market_probs(conn, "Bahia", "Chapecoense")
    assert mk is not None
    assert mk["odds_home"] == 2.1  # a linha real, não a placeholder
    assert 0 < mk["p_home"] < 1 and math.isfinite(mk["p_over"])


# --- sombra: liquidação duplicada intra-execução -----------------------------


def _cfg():
    return {
        "backtest": {"min_edge": 0.02, "max_edge": 0.15, "over_under_line": 2.5},
        "model": {"max_goals": 12},
        "elo": {"home_advantage": 100},
    }


def _banco_com_jogo_encerrado(tmp_path, c_over=1.9, c_under=1.9):
    conn = db.connect(str(tmp_path / "s.db"))
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, date, home_team, away_team, "
        "home_score, away_score, odds_over, odds_under) "
        "VALUES (10, '2026-07-16', 'Casa', 'Fora', 2, 1, ?, ?)",
        (c_over, c_under),
    )
    conn.commit()
    return conn


def _pick(**kw):
    base = {
        "captured_at": "2026-07-10T00:00:00+00:00",
        "event_id": 10,
        "date": "2026-07-16",
        "home": "Casa",
        "away": "Fora",
        "market": "ou2.5",
        "selection": "under",
        "odd": 1.95,
        "edge": 0.03,
        "model_prob": 0.55,
        "trial": "h3-ou25-sombra-2026",
    }
    base.update(kw)
    return base


def test_settle_nao_liquida_pick_duplicado_duas_vezes(tmp_path):
    conn = _banco_com_jogo_encerrado(tmp_path)
    picks = tmp_path / "p.jsonl"
    results = tmp_path / "r.jsonl"
    # ledger com o MESMO pick duplicado (edição manual / captura concorrente)
    with open(picks, "w", encoding="utf-8") as f:
        f.write(json.dumps(_pick()) + "\n")
        f.write(json.dumps(_pick()) + "\n")
    n = sombra.settle(_cfg(), conn, picks, results, "h3-ou25-sombra-2026")
    res = sombra._load_jsonl(results)
    assert n == 1 and len(res) == 1  # antes: 2 settlements, PNL dobrado


def test_settle_rerun_continua_idempotente(tmp_path):
    conn = _banco_com_jogo_encerrado(tmp_path)
    picks = tmp_path / "p.jsonl"
    results = tmp_path / "r.jsonl"
    with open(picks, "w", encoding="utf-8") as f:
        f.write(json.dumps(_pick()) + "\n")
    assert sombra.settle(_cfg(), conn, picks, results, "t") == 1
    assert sombra.settle(_cfg(), conn, picks, results, "t") == 0
    assert len(sombra._load_jsonl(results)) == 1


# --- sombra: CLV com odd de fechamento inválida ------------------------------


@pytest.mark.parametrize(
    "c_over,c_under",
    [
        (float("nan"), 1.9),  # NaN: antes CLV=NaN entrava no ledger
        (-2.0, 1.9),  # negativa: antes CLV absurdo calado
        (1.0, 1.0),  # placeholder do Sofascore
    ],
)
def test_settle_com_fechamento_invalido_liquida_sem_clv(tmp_path, c_over, c_under):
    conn = _banco_com_jogo_encerrado(tmp_path, c_over, c_under)
    picks = tmp_path / "p.jsonl"
    results = tmp_path / "r.jsonl"
    with open(picks, "w", encoding="utf-8") as f:
        f.write(json.dumps(_pick()) + "\n")
    n = sombra.settle(_cfg(), conn, picks, results, "t")
    res = sombra._load_jsonl(results)
    assert n == 1 and len(res) == 1
    assert res[0]["clv"] is None  # indisponível ≠ inventado
    assert res[0]["won"] in (0, 1) and math.isfinite(res[0]["pnl"])


# --- sombra: linha inteira (push) falha em voz alta --------------------------


def test_settle_recusa_linha_inteira(tmp_path):
    conn = _banco_com_jogo_encerrado(tmp_path)
    cfg = _cfg()
    cfg["backtest"]["over_under_line"] = 3.0
    with pytest.raises(SystemExit, match="linha INTEIRA"):
        sombra.settle(cfg, conn, tmp_path / "p.jsonl", tmp_path / "r.jsonl", "t")


def test_capture_recusa_linha_inteira(tmp_path):
    conn = _banco_com_jogo_encerrado(tmp_path)
    cfg = _cfg()
    cfg["backtest"]["over_under_line"] = 3.0
    with pytest.raises(SystemExit, match="linha INTEIRA"):
        sombra._capture_funil(cfg, conn, lambda h, a: None, tmp_path / "p.jsonl", "t")


# --- record_result: placar negativo ------------------------------------------


def test_record_result_rejeita_placar_negativo(tmp_path):
    with pytest.raises(ValueError, match="negativo"):
        record_result("Casa", "Fora", -1, 2, path=tmp_path / "res.jsonl", pred_path=tmp_path / "none.jsonl")
    assert not (tmp_path / "res.jsonl").exists()  # nada foi gravado


# --- banco truncado: falha clara, nunca leitura silenciosa -------------------


def test_banco_truncado_falha_claramente(tmp_path):
    corrupto = tmp_path / "corrupto.db"
    corrupto.write_bytes(b"SQLite format 3\x00" + b"\x00" * 64)  # header cortado
    conn = db.connect(str(corrupto), read_only=True)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("SELECT * FROM sofascore_matches").fetchall()


# --- concorrência: leitor read-only convive com escritor WAL -----------------


def test_leitor_read_only_ve_dado_commitado_durante_escrita(tmp_path):
    caminho = str(tmp_path / "conc.db")
    escritor = db.connect(caminho)
    escritor.execute(
        "INSERT INTO sofascore_matches (event_id, date, home_team, away_team) VALUES (1, '2026-01-01', 'A', 'B')"
    )
    escritor.commit()
    leitor = db.connect(caminho, read_only=True)
    # escritor segue inserindo depois que o leitor abriu
    escritor.execute(
        "INSERT INTO sofascore_matches (event_id, date, home_team, away_team) VALUES (2, '2026-01-02', 'C', 'D')"
    )
    escritor.commit()
    n = leitor.execute("SELECT COUNT(*) FROM sofascore_matches").fetchone()[0]
    assert n >= 1  # nunca 'database is locked'
    with pytest.raises(sqlite3.OperationalError):
        leitor.execute("INSERT INTO current_elo (team, elo) VALUES ('X', 1500)")
