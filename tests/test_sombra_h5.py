"""H5 (sombra do ensemble): captura paralela à H3, arquivos separados,
flag desligada = zero efeito, settle parametrizado."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("sombra", ROOT / "brasileirao_scripts" / "sombra.py")
sombra = importlib.util.module_from_spec(spec)
sys.modules["sombra"] = sombra
spec.loader.exec_module(sombra)

from brasileirao_predictor import db, model, xg_model  # noqa: E402


def _cfg(enabled=True):
    return {
        "backtest": {"min_edge": 0.02, "max_edge": 0.15, "over_under_line": 2.5},
        "model": {"max_goals": 12},
        "elo": {"home_advantage": 100},
        "ensemble_xg": {"enabled": enabled, "blend_weight": 0.5},
    }


PARAMS = (0.2, 0.7, 1e-4, 0.0)
XGP = {
    "mu": 0.35,
    "ha": 0.30,
    "alpha": 1e-4,
    "rho": 0.0,
    "atk": {"Casa": 0.4, "Fora": -0.1},
    "def": {"Casa": 0.1, "Fora": -0.3},
}


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Banco com 1 fixture futuro + caches; arquivos de sombra em tmp."""
    conn = db.connect(str(tmp_path / "t.db"))
    db.save_elo(conn, [("Casa", 1550), ("Fora", 1450)])
    db.save_params(conn, *PARAMS, 10, "h", "2026-01-01T00:00:00+00:00")
    db.save_xg_params(conn, XGP, 10, "h", "2026-01-01T00:00:00+00:00")

    # odds calculadas pra dar edge de exatamente +5% no OVER de cada modelo
    rb = model.predict_match(1550, 1450, PARAMS, 100.0, max_goals=12)
    rx = xg_model.predict(XGP, "Casa", "Fora", max_goals=12)
    p_base = rb["over"][2.5]
    p_ens = xg_model.blend(rb, rx, w_base=0.5)["over"][2.5]
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, "
        "home_team, away_team, odds_over, odds_under) VALUES "
        "(1, 'T', '2027', '2027-01-01', 'Casa', 'Fora', ?, ?)",
        (round(1.0 / (p_base - 0.05), 3), 1.01),
    )
    # Os dois fixtures ficam a uma SEMANA de distância de propósito: o mesmo par
    # (mandante, visitante) a 1 dia de intervalo não existe em Série A, e cai na
    # trava de ambiguidade de `match_fixture` (que é o comportamento correto).
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, "
        "home_team, away_team, odds_over, odds_under) VALUES "
        "(2, 'T', '2027', '2027-01-08', 'Casa', 'Fora', ?, ?)",
        (round(1.0 / (p_ens - 0.05), 3), 1.01),
    )
    conn.commit()
    db.update_kickoff(conn, 1, 1_798_761_600)
    db.update_kickoff(conn, 2, 1_798_761_600 + 7 * 86_400)

    monkeypatch.setattr(sombra, "PICKS", tmp_path / "p3.jsonl")
    monkeypatch.setattr(sombra, "RESULTS", tmp_path / "r3.jsonl")
    monkeypatch.setattr(sombra, "PICKS_H5", tmp_path / "p5.jsonl")
    monkeypatch.setattr(sombra, "RESULTS_H5", tmp_path / "r5.jsonl")
    monkeypatch.setenv("BRASILEIRAO_BOOKMAKER", "test-bookmaker")

    # A captura agora exige que o env var bata com o bookmaker congelado no
    # pré-registro (trials.json) — registro de teste isolado, coerente com
    # "test-bookmaker" usado neste fixture.
    trials_path = tmp_path / "trials.json"
    trials_path.write_text(
        json.dumps(
            [
                {"name": sombra.TRIAL, "params": {"bookmaker": "test-bookmaker"}},
                {"name": sombra.TRIAL_H5, "params": {"bookmaker": "test-bookmaker"}},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sombra, "TRIALS_PATH", trials_path)

    # Desde 2026-07-25 a odd do pick vem do BOOK designado (The Odds API), não
    # mais do agregado do Sofascore. O provider é substituído por um duplo que
    # devolve exatamente as odds desenhadas acima para os 2 fixtures.
    monkeypatch.setattr(sombra, "SNAPSHOTS_PATH", tmp_path / "book_snaps.jsonl")
    kickoffs = dict(conn.execute("SELECT event_id, kickoff_at FROM sofascore_matches").fetchall())
    odds_desenhadas = dict(conn.execute("SELECT event_id, odds_over FROM sofascore_matches").fetchall())

    class _ProviderDuplo:
        def __init__(self, *a, **k):
            pass

        def fetch_ou25(self, *, retrieved_at=None):
            linhas = []
            for event_id in (1, 2):
                for selection, price in (("over", odds_desenhadas[event_id]), ("under", 1.01)):
                    linhas.append(
                        {
                            "source": "the_odds_api",
                            "source_event_id": f"api-{event_id}",
                            "bookmaker": "test-bookmaker",
                            "market": "ou2.5",
                            "selection": selection,
                            "decimal_odds": float(price),
                            "odds_captured_at": "2026-12-31T10:00:00+00:00",
                            "retrieved_at": "2026-12-31T10:00:00+00:00",
                            "canonical_match_id": f"the_odds_api:api-{event_id}",
                            "raw_payload_hash": "0" * 64,
                            "adapter_version": "the-odds-api/1",
                            "data_quality_status": "PROSPECTIVE_ELIGIBLE",
                            "kickoff_at": kickoffs[event_id],
                            "home_team": "Casa",
                            "away_team": "Fora",
                        }
                    )
            return linhas

    monkeypatch.setattr(sombra, "TheOddsApiProvider", _ProviderDuplo)
    return conn, tmp_path, p_base, p_ens


def test_h3_e_h5_capturam_em_arquivos_separados(ambiente):
    conn, tmp, p_base, p_ens = ambiente
    n3 = sombra.capture(_cfg(), conn)
    n5 = sombra.capture_h5(_cfg(), conn)
    assert n3 >= 1 and n5 >= 1
    p3 = sombra._load_jsonl(tmp / "p3.jsonl")
    p5 = sombra._load_jsonl(tmp / "p5.jsonl")
    # nomes vêm das constantes do módulo: a coorte muda de identidade quando a
    # fonte da odd muda, e o teste não deve travar o nome de uma coorte antiga
    assert all(p["trial"] == sombra.TRIAL for p in p3)
    assert all(p["trial"] == sombra.TRIAL_H5 for p in p5)
    assert "pinnacle" in sombra.TRIAL and "pinnacle" in sombra.TRIAL_H5
    # cada população usa a probabilidade do PRÓPRIO motor (evento 1 tem odd
    # desenhada pro edge do baseline; evento 2, pro edge do ensemble)
    over3 = {p["event_id"]: p["model_prob"] for p in p3 if p["selection"] == "over"}
    over5 = {p["event_id"]: p["model_prob"] for p in p5 if p["selection"] == "over"}
    assert over3[1] == pytest.approx(p_base, abs=1e-4)
    assert over5[2] == pytest.approx(p_ens, abs=1e-4)
    assert p_base != pytest.approx(p_ens, abs=1e-3)  # motores de fato diferem
    assert all(p["predicted_at"] == p["captured_at"] for p in p3 + p5)
    # proveniência REAL: a odd vem do book, e o pick carrega a identidade da
    # fonte que a forneceu — não mais o agregado do Sofascore com rótulo falso
    assert all(p["kickoff_at"] and p["odds_source"] == "the_odds_api" for p in p3 + p5)
    assert all(
        p["bookmaker"] == "test-bookmaker"
        and p["source"] == "the_odds_api"
        and p["canonical_match_id"].startswith("the_odds_api:")
        for p in p3 + p5
    )
    assert all(p["capture_turn"] == "manual" for p in p3 + p5)


def test_flag_desligada_h5_nao_roda(ambiente):
    conn, tmp, _pb, _pe = ambiente
    assert sombra.capture_h5(_cfg(enabled=False), conn) == 0
    assert not (tmp / "p5.jsonl").exists()


def test_sem_cache_xg_h5_pula_com_aviso(ambiente, capsys):
    conn, tmp, _pb, _pe = ambiente
    conn.execute("DELETE FROM xg_model_parameters")
    conn.commit()
    assert sombra.capture_h5(_cfg(), conn) == 0
    assert "sem cache" in capsys.readouterr().out
    assert not (tmp / "p5.jsonl").exists()


def test_settle_h5_parametrizado(ambiente):
    conn, tmp, _pb, _pe = ambiente
    sombra.capture_h5(_cfg(), conn)
    conn.execute("UPDATE sofascore_matches SET home_score=3, away_score=1")
    conn.commit()
    n = sombra.settle(_cfg(), conn, tmp / "p5.jsonl", tmp / "r5.jsonl", "h5-ensemble-xg-sombra-2026")
    assert n >= 1
    res = sombra._load_jsonl(tmp / "r5.jsonl")
    assert all(r["trial"] == "h5-ensemble-xg-sombra-2026" for r in res)
    over = [r for r in res if r["selection"] == "over"]
    assert over and all(r["won"] == 1 for r in over)  # 3+1 > 2.5
    assert all(r["odds_close"] is not None for r in over)
    assert all(r["costs"]["status"] == "not_applicable_shadow_no_execution" for r in res)
    # e a população da H3 continua intocada
    assert not (tmp / "r3.jsonl").exists()


def test_captura_bloqueada_quando_bookmaker_diverge_do_registrado(ambiente, monkeypatch, capsys):
    """Env var != bookmaker congelado na trial -> bloqueio fail-closed, não
    captura silenciosa sob um trial_id que não corresponde à odd usada."""
    conn, tmp, _pb, _pe = ambiente
    monkeypatch.setenv("BRASILEIRAO_BOOKMAKER", "outro-book-qualquer")
    assert sombra.capture(_cfg(), conn) == 0
    assert "diverge do bookmaker pré-registrado" in capsys.readouterr().out
    assert not (tmp / "p3.jsonl").exists()


def test_h5_registrada_no_trials():
    """O pré-registro precisa existir ANTES da coleta (governança)."""
    import json

    trials = json.loads((ROOT / "data" / "trials.json").read_text(encoding="utf-8"))
    h5 = [t for t in trials if t["name"] == "h5-ensemble-xg-sombra-2026"]
    assert len(h5) == 1
    assert h5[0]["params"]["market"] == "ou25"
    assert h5[0]["sharpe"] is None  # resultado ainda não existe
    # e o registro da H1 segue com o sharpe observado (denominador do DSR)
    h1 = [t for t in trials if t["name"] == "h1-ou25-edge-2-15-walkforward"]
    assert h1[0]["sharpe"] == pytest.approx(0.0722)
