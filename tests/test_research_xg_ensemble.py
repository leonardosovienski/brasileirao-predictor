"""RESEARCH-XG — mecânica do experimento do ensemble de xG.

Não testa o VEREDITO (depende da base real do operador); testa que o
experimento é honesto: braços que de fato diferem, config isolada entre eles,
holdout recusado por padrão e o veredito respeitando primária + guardrails.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile
from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_predictor import db
from brasileirao_scripts import benchmark_predictor as bp
from brasileirao_scripts import research_xg_ensemble as rxg

TIMES = ["flamengo", "palmeiras", "gremio", "santos", "corinthians", "bahia"]


def _tmp_db(monkeypatch, rodadas: int = 90) -> None:
    """Liga sintética com o DDL REAL — a entrada do teste vem do PRODUTOR."""
    path = pathlib.Path(tempfile.mkdtemp()) / "m.db"
    conn = db.connect(str(path))
    eid = 0
    for rodada in range(rodadas):
        dia = datetime(2021, 4, 3, tzinfo=UTC) + timedelta(days=7 * rodada)
        pares = [(TIMES[0], TIMES[1]), (TIMES[2], TIMES[3]), (TIMES[4], TIMES[5])]
        if rodada % 2:
            pares = [(a, h) for h, a in pares]
        for j, (casa, fora) in enumerate(pares):
            d = dia.strftime("%Y-%m-%d")
            kickoff = (dia + timedelta(hours=16 + 2 * (j // 2))).isoformat(timespec="seconds")
            gc, gf = (rodada + j) % 4, (rodada + 2 * j) % 3
            conn.execute(
                "INSERT INTO matches (date, home_team, away_team, home_score, away_score, tournament, neutral)"
                " VALUES (?,?,?,?,?,?,0)",
                (d, casa, fora, gc, gf, "Brasileirão Série A"),
            )
            conn.execute(
                "INSERT INTO sofascore_matches (event_id, date, kickoff_at, home_team, away_team,"
                " home_score, away_score, home_xg, away_xg) VALUES (?,?,?,?,?,?,?,?,?)",
                (eid, d, kickoff, casa, fora, gc, gf, gc + 0.3, gf + 0.2),
            )
            eid += 1
    conn.commit()
    conn.close()
    monkeypatch.setattr(bp, "DB", path)


# ---------- isolamento da config entre braços ----------


def test_cfg_com_ensemble_forca_a_flag() -> None:
    cfg = {"ensemble_xg": {"enabled": False, "blend_weight": 0.5}}
    assert rxg._cfg_with_ensemble(cfg, True)["ensemble_xg"]["enabled"] is True
    assert rxg._cfg_with_ensemble(cfg, False)["ensemble_xg"]["enabled"] is False


def test_cfg_com_ensemble_nao_vaza_entre_bracos() -> None:
    """Cópia RASA deixaria `cfg['ensemble_xg']` compartilhado: os dois braços
    rodam no mesmo processo e um sobrescreveria a flag do outro — vazamento de
    configuração que nenhuma métrica denunciaria."""
    original = {"ensemble_xg": {"enabled": True, "blend_weight": 0.5}}
    ligado = rxg._cfg_with_ensemble(original, True)
    desligado = rxg._cfg_with_ensemble(original, False)
    assert ligado["ensemble_xg"]["enabled"] is True
    assert desligado["ensemble_xg"]["enabled"] is False
    assert original["ensemble_xg"]["enabled"] is True, "a config original foi mutada"


def test_cfg_com_ensemble_aceita_config_sem_a_secao() -> None:
    assert rxg._cfg_with_ensemble({}, True)["ensemble_xg"]["enabled"] is True


# ---------- veredito ----------


def _g(lo, hi):
    return {"ci95": [lo, hi]}


def test_veredito_refuta_quando_ic95_cruza_zero() -> None:
    status, detail = rxg._verdict(_g(-0.001, 0.004), {})
    assert status == "refutada"
    assert "indistinguível de sorte" in detail


def test_veredito_refuta_quando_desligar_piora() -> None:
    status, detail = rxg._verdict(_g(-0.009, -0.002), {})
    assert status == "refutada"
    assert "PIORA" in detail


def test_veredito_comprova_com_ic95_acima_de_zero() -> None:
    status, _ = rxg._verdict(_g(0.002, 0.007), {m: _g(0.001, 0.006) for m in rxg.GUARDRAIL_METRICS})
    assert status == "comprovada"


def test_veredito_refuta_quando_guardrail_piora_materialmente() -> None:
    """Primária boa não compra guardrail ruim — e 'ruim' é IC inteiro do lado
    ruim, não média ruim, senão ruído vira veto arbitrário."""
    status, detail = rxg._verdict(_g(0.002, 0.007), {"log_loss": _g(-0.009, -0.002)})
    assert status == "refutada"
    assert "log_loss" in detail


def test_veredito_inconclusivo_sem_ic() -> None:
    assert rxg._verdict(_g(None, None), {})[0] == "inconclusiva"


# ---------- os braços têm que diferir de verdade ----------


def test_bracos_produzem_previsoes_diferentes(monkeypatch) -> None:
    """Se ligar/desligar a flag não muda a previsão, não há experimento — foi o
    que aconteceu em 2026-08-22, quando duas execuções manuais do painel
    saíram com RPS idêntico porque o config.yaml não chegou a ser editado."""
    _tmp_db(monkeypatch)
    monkeypatch.setattr(bp, "MIN_HISTORY", 30)
    cfg = bp.load_config()
    obs = bp._load_observations("")

    on_rows, on_ev = rxg._arm(obs, 120.0, rxg._cfg_with_ensemble(cfg, True), "", "", "CONTROL")
    off_rows, off_ev = rxg._arm(obs, 120.0, rxg._cfg_with_ensemble(cfg, False), "", "", "TREATMENT")

    assert on_rows and len(on_rows) == len(off_rows)
    assert on_ev.ensemble_enabled is True
    assert off_ev.ensemble_enabled is False
    identicas = sum(1 for a, b in zip(on_rows, off_rows) if a["p_win"] == b["p_win"])
    assert identicas < len(on_rows), "os dois braços deram previsões idênticas — a flag não teve efeito"


def test_bracos_pareiam_jogo_a_jogo(monkeypatch) -> None:
    """Pareamento só vale sobre a MESMA sequência de jogos."""
    _tmp_db(monkeypatch)
    monkeypatch.setattr(bp, "MIN_HISTORY", 30)
    cfg = bp.load_config()
    obs = bp._load_observations("")
    on_rows, _ = rxg._arm(obs, 120.0, rxg._cfg_with_ensemble(cfg, True), "", "", "CONTROL")
    off_rows, _ = rxg._arm(obs, 120.0, rxg._cfg_with_ensemble(cfg, False), "", "", "TREATMENT")
    chave = lambda r: (r["date"], r["home"], r["away"])  # noqa: E731
    assert [chave(r) for r in on_rows] == [chave(r) for r in off_rows]


# ---------- holdout selado ----------


@pytest.mark.parametrize("period", ["2021-01-01,2025-12-31", "2021-01-01,2026-06-30", "2021-01-01,"])
def test_recusa_periodo_que_alcanca_o_holdout_selado(period, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["research_xg", "--period", period])
    assert rxg.main() == 1
