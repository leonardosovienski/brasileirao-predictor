"""Modelo atk/def-xG + ensemble (src/xg_model.py) — fit sintético, predição,
blend, hook de serving (flag OFF = baseline byte a byte) e cache no banco."""

import math

import pytest

from src import db, model, xg_model


# ---------------------------------------------------------------- fixtures
def _liga_sintetica():
    """Mini-liga com um time forte, um fraco e dois medianos — round-robin
    duplo repetido para dar massa ao ajuste. Placares determinísticos."""
    placar = {
        ("Forte", "Fraco"): (4, 0),
        ("Fraco", "Forte"): (0, 3),
        ("Forte", "MedioA"): (2, 0),
        ("MedioA", "Forte"): (1, 2),
        ("Forte", "MedioB"): (3, 1),
        ("MedioB", "Forte"): (0, 2),
        ("MedioA", "MedioB"): (1, 1),
        ("MedioB", "MedioA"): (1, 1),
        ("MedioA", "Fraco"): (2, 0),
        ("Fraco", "MedioA"): (0, 1),
        ("MedioB", "Fraco"): (2, 1),
        ("Fraco", "MedioB"): (1, 2),
    }
    matches = []
    mes = 1
    for rodada in range(4):  # 4 voltas = 48 jogos
        for (h, a), (hs, as_) in placar.items():
            matches.append((f"2025-{mes:02d}-15", h, a, hs, as_))
        mes += 2
    return sorted(matches)


@pytest.fixture
def xgp():
    m = _liga_sintetica()
    # xG = placar com ruído zero (teste de mecânica, não de robustez)
    xg = {(d, h, a): (float(hs), float(as_)) for d, h, a, hs, as_ in m}
    return xg_model.fit(m, xg, "2025-08-01")


# ---------------------------------------------------------------- fit
def test_fit_ordena_forcas(xgp):
    assert xgp is not None and xgp["ok"]
    assert xgp["atk"]["Forte"] > xgp["atk"]["MedioA"] > xgp["atk"]["Fraco"]
    assert xgp["def"]["Forte"] > xgp["def"]["Fraco"]


def test_fit_vazio_devolve_none():
    assert xg_model.fit([], {}, "2025-08-01") is None


def test_fit_sem_xg_cai_nos_gols():
    """Jogo ausente do xg_map usa os gols reais — sem crash, sem viés."""
    m = _liga_sintetica()
    p = xg_model.fit(m, {}, "2025-08-01")
    assert p["ok"]
    assert p["atk"]["Forte"] > p["atk"]["Fraco"]


def test_fit_e_serializavel(xgp):
    import json

    blob = json.dumps(xgp)  # cache do cron é JSON
    assert json.loads(blob)["mu"] == pytest.approx(xgp["mu"])


# ---------------------------------------------------------------- predict
def test_predict_probs_consistentes(xgp):
    r = xg_model.predict(xgp, "Forte", "Fraco")
    assert r["p_win"] + r["p_draw"] + r["p_loss"] == pytest.approx(1.0, abs=1e-9)
    assert r["p_win"] > 0.5  # forte em casa é favorito claro
    assert r["lambda_a"] > r["lambda_b"]


def test_predict_time_desconhecido_e_media(xgp):
    """Time fora do ajuste recebe força 0 (média da liga) — não explode."""
    r = xg_model.predict(xgp, "Promovido", "OutroNovo")
    assert r["p_win"] + r["p_draw"] + r["p_loss"] == pytest.approx(1.0, abs=1e-9)
    # dois times médios: só o mando separa
    assert r["lambda_a"] / r["lambda_b"] == pytest.approx(math.exp(xgp["ha"]), rel=1e-6)


def test_predict_neutro_remove_mando(xgp):
    rn = xg_model.predict(xgp, "MedioA", "MedioB", neutral=True)
    rc = xg_model.predict(xgp, "MedioA", "MedioB", neutral=False)
    assert rn["lambda_a"] < rc["lambda_a"]  # sem mando, ataque de A cai
    # em campo neutro a ordem dos times é irrelevante (simetria exata)
    rn_inv = xg_model.predict(xgp, "MedioB", "MedioA", neutral=True)
    assert rn["lambda_a"] == pytest.approx(rn_inv["lambda_b"], rel=1e-9)
    assert rn["p_win"] == pytest.approx(rn_inv["p_loss"], rel=1e-9)


# ---------------------------------------------------------------- blend
def _base_result():
    return model.predict_match(1600, 1500, (0.2, 0.7, 1e-4, 0.01), 100.0, max_goals=12)


def test_blend_extremos(xgp):
    rb = _base_result()
    rx = xg_model.predict(xgp, "Forte", "Fraco")
    b1 = xg_model.blend(rb, rx, w_base=1.0)
    assert b1["p_win"] == pytest.approx(rb["p_win"], abs=1e-9)
    b0 = xg_model.blend(rb, rx, w_base=0.0)
    assert b0["p_win"] == pytest.approx(rx["p_win"], abs=1e-9)


def test_blend_meio_soma_um_e_marca_ensemble(xgp):
    rb = _base_result()
    rx = xg_model.predict(xgp, "Forte", "Fraco")
    b = xg_model.blend(rb, rx, w_base=0.5)
    assert b["ensemble"] is True
    assert b["p_win"] + b["p_draw"] + b["p_loss"] == pytest.approx(1.0, abs=1e-9)
    assert min(rb["p_win"], rx["p_win"]) <= b["p_win"] <= max(rb["p_win"], rx["p_win"])
    assert b["lambda_a"] == pytest.approx(0.5 * rb["lambda_a"] + 0.5 * rx["lambda_a"])
    # OU e BTTS vêm da MESMA grade blended (consistência interna)
    assert 0.0 < b["over"][2.5] < 1.0


# ------------------------------------------------------- cache no banco
def test_save_load_xg_params_roundtrip(tmp_path, xgp):
    conn = db.connect(str(tmp_path / "t.db"))
    db.save_xg_params(conn, xgp, 48, "hash123", "2025-08-01T00:00:00+00:00")
    loaded, n, h, at = db.load_xg_params(conn)
    assert loaded["atk"]["Forte"] == pytest.approx(xgp["atk"]["Forte"])
    assert (n, h) == (48, "hash123")


def test_load_xg_params_vazio(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    assert db.load_xg_params(conn) is None


# ------------------------------------------------------- hook de serving
def test_maybe_blend_desligado_devolve_intocado():
    rb = _base_result()
    out = xg_model.maybe_blend(rb, None, {"ensemble_xg": {"enabled": False}}, "A", "B", False)
    assert out is rb  # MESMO objeto, zero mutação


def test_maybe_blend_sem_secao_config():
    rb = _base_result()
    assert xg_model.maybe_blend(rb, None, {}, "A", "B", False) is rb


def test_maybe_blend_ligado_sem_cache_degrada(tmp_path, capsys):
    conn = db.connect(str(tmp_path / "t.db"))
    rb = _base_result()
    out = xg_model.maybe_blend(rb, conn, {"ensemble_xg": {"enabled": True}}, "A", "B", False)
    assert out is rb  # degrada pro baseline
    assert "sem cache" in capsys.readouterr().err


def test_maybe_blend_ligado_com_cache_blenda(tmp_path, xgp):
    conn = db.connect(str(tmp_path / "t.db"))
    db.save_xg_params(conn, xgp, 48, "h", "2025-08-01T00:00:00+00:00")
    rb = _base_result()
    out = xg_model.maybe_blend(rb, conn, {"ensemble_xg": {"enabled": True}}, "Forte", "Fraco", False)
    assert out is not rb and out.get("ensemble") is True
    assert out["p_win"] + out["p_draw"] + out["p_loss"] == pytest.approx(1.0, abs=1e-9)


def test_maybe_blend_nunca_lanca(tmp_path, capsys):
    """Cache corrompido não derruba o serving — degrada com aviso."""
    conn = db.connect(str(tmp_path / "t.db"))
    db.save_xg_params(conn, {"lixo": 1}, 0, "h", "x")  # sem atk/def/mu
    rb = _base_result()
    out = xg_model.maybe_blend(rb, conn, {"ensemble_xg": {"enabled": True}}, "A", "B", False)
    assert out is rb
    assert "falhou" in capsys.readouterr().err


# ------------------------------------------------------- cron
def test_config_hash_inclui_recencia_e_flag_do_ensemble():
    """Recência e ensemble alteram o hash para impedir cache incompatível."""
    from src.cron_update_models import config_hash

    cfg = {
        "elo": {"k": 1},
        "model": {"calibration_window_years": 4, "goal_half_life_days": 360},
    }
    h0 = config_hash(cfg)
    cfg2 = dict(cfg, ensemble_xg={"enabled": False})
    assert config_hash(cfg2) == h0
    cfg3 = dict(cfg, ensemble_xg={"enabled": True})
    assert config_hash(cfg3) != h0
    cfg4 = {**cfg, "model": {**cfg["model"], "goal_half_life_days": 180}}
    assert config_hash(cfg4) != h0


def test_cache_is_current_requires_matching_hash_and_completed_count():
    from src.cron_update_models import cache_is_current, config_hash

    cfg = {
        "elo": {"k": 1},
        "model": {"calibration_window_years": 4, "goal_half_life_days": 360},
    }

    class Conn:
        def execute(self, _sql):
            return self

        def fetchone(self):
            return (10,)

    current = (0.1, 0.2, 0.3, 0.0, 10, config_hash(cfg), "now")
    assert cache_is_current(cfg, Conn(), current)
    assert not cache_is_current(cfg, Conn(), (*current[:4], 9, *current[5:]))
    assert not cache_is_current(cfg, Conn(), (*current[:5], "wrong", current[6]))
