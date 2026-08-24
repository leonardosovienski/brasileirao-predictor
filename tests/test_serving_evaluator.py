"""Walk-forward da pilha de serving — paridade com `src/predict.py` sem vazar.

Fecha a lacuna de `docs/READINESS.md`: o painel media Dixon-Coles puro enquanto
o serving prevê `Ensemble(NB+DC, AtkDef-xG)`. Estes testes cobrem as duas
coisas que podem dar errado ao juntar os dois mundos: vazamento (o ajuste ver o
que ainda não aconteceu) e divergência (medir uma reimplementação em vez da
pilha real).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src import model, xg_model
from src.serving_evaluator import H9FrozenPolicyEvaluator, ServingStackEvaluator

TIMES = ["flamengo", "palmeiras", "gremio", "santos"]

CFG = {
    "tournament_name": "Brasileirão Série A",
    "elo": {
        "initial_rating": 1500,
        "home_advantage": 100,
        "window_years": 6,
        "form_half_life_years": 4.0,
        "k_factors": {"Brasileirão Série A": 30, "default": 30},
    },
    "model": {"calibration_window_years": 4, "goal_half_life_days": 360, "max_goals": 6},
    "ensemble_xg": {"enabled": True, "blend_weight": 0.5, "w_xg": 0.85, "half_life_years": 0.75, "ridge_reg": 1.0},
}


def _obs(n_rodadas: int = 60, *, simultaneo: bool = False, com_xg: bool = True) -> list[dict]:
    t0 = datetime(2021, 4, 3, 16, 0, tzinfo=UTC)
    out = []
    for r in range(n_rodadas):
        dia = t0 + timedelta(days=7 * r)
        pares = [(TIMES[0], TIMES[1]), (TIMES[2], TIMES[3])]
        if r % 2:
            pares = [(a, h) for h, a in pares]
        for j, (casa, fora) in enumerate(pares):
            kickoff = dia if simultaneo else dia + timedelta(hours=2 * j)
            hg, ag = (r + j) % 3, r % 3
            out.append(
                {
                    "home": casa,
                    "away": fora,
                    "kickoff": kickoff,
                    "date": kickoff.strftime("%Y-%m-%d"),
                    "tournament": "Brasileirão Série A",
                    "neutral": 0,
                    "result": {
                        "home_goals": hg,
                        "away_goals": ag,
                        "home_xg": (hg + 0.4) if com_xg else None,
                        "away_xg": (ag + 0.2) if com_xg else None,
                    },
                }
            )
    return out


def _cfg_sem_ensemble() -> dict:
    c = {k: (dict(v) if isinstance(v, dict) else v) for k, v in CFG.items()}
    c["ensemble_xg"] = dict(CFG["ensemble_xg"], enabled=False)
    return c


# ---------- não vaza ----------


def test_predicted_at_e_estritamente_anterior_ao_matures_at() -> None:
    ev = ServingStackEvaluator(CFG)
    results = ev.run(_obs(simultaneo=True), min_history=30, retrain_every=10)
    assert results
    for r in results:
        assert r["prediction"].predicted_at < r["prediction"].matures_at


def test_bloco_simultaneo_e_descartado_do_ajuste() -> None:
    ev = ServingStackEvaluator(CFG)
    ev.run(_obs(simultaneo=True), min_history=30, retrain_every=1)
    assert ev.blocked_observations > 0


def test_kickoffs_distintos_nao_cobram_pedagio() -> None:
    ev = ServingStackEvaluator(CFG)
    ev.run(_obs(simultaneo=False), min_history=30, retrain_every=1)
    assert ev.blocked_observations == 0


def test_xg_do_jogo_previsto_nao_chega_ao_predict_step() -> None:
    """O xG é desfecho: vive dentro de `result`, que a ABC remove antes de
    prever. Se algum dia migrar para o nível de cima, o modelo passaria a ver o
    xG do próprio jogo que está prevendo."""
    ev = ServingStackEvaluator(CFG)
    vistos: list[set[str]] = []
    inner = ev.predict_step

    def espiao(features):
        vistos.append(set(features))
        return inner(features)

    ev.predict_step = espiao  # type: ignore[method-assign]
    ev.run(_obs(), min_history=30, retrain_every=10)
    assert vistos
    for chaves in vistos:
        assert "result" not in chaves
        assert not {"home_xg", "away_xg"} & chaves


def test_ajuste_ignora_jogos_futuros_mesmo_recebendo_historico_maior() -> None:
    """Chamada direta de `_fit` com horizonte no meio da lista: o Elo não pode
    refletir partidas posteriores ao horizonte."""
    obs = _obs()
    ev_cedo = ServingStackEvaluator(CFG)
    ev_cedo._fit(obs, obs[40]["kickoff"])
    ev_tarde = ServingStackEvaluator(CFG)
    ev_tarde._fit(obs, obs[100]["kickoff"])
    assert ev_cedo.elo != ev_tarde.elo
    assert ev_cedo._trained_at is not None and ev_cedo._trained_at < obs[40]["kickoff"]


def test_serving_passa_peso_exponencial_por_recencia(monkeypatch) -> None:
    obs = _obs(n_rodadas=20)
    captured = {}
    original = model.fit_goal_model

    def spy(history, delta_xg=None, sample_weights=None):
        captured["weights"] = sample_weights
        return original(history, delta_xg=delta_xg, sample_weights=sample_weights)

    monkeypatch.setattr(model, "fit_goal_model", spy)
    ev = ServingStackEvaluator(_cfg_sem_ensemble())
    ev._fit(obs, obs[-1]["kickoff"] + timedelta(days=1))
    weights = captured["weights"]
    assert weights is not None
    assert weights[-1] == pytest.approx(1.0)
    assert weights[0] < weights[-1]
    assert weights[0] == pytest.approx(0.5 ** ((19 * 7) / 360))


def test_serving_usa_pesos_uniformes_quando_politica_e_null(monkeypatch) -> None:
    obs = _obs(n_rodadas=20)
    captured = {}
    original = model.fit_goal_model

    def spy(history, delta_xg=None, sample_weights=None):
        captured["weights"] = sample_weights
        return original(history, delta_xg=delta_xg, sample_weights=sample_weights)

    cfg = _cfg_sem_ensemble()
    cfg["model"] = dict(cfg["model"], goal_half_life_days=None)
    monkeypatch.setattr(model, "fit_goal_model", spy)
    ServingStackEvaluator(cfg)._fit(obs, obs[-1]["kickoff"] + timedelta(days=1))
    assert captured["weights"] == [1.0] * len(captured["weights"])


def test_serving_rejeita_half_life_nao_positiva() -> None:
    cfg = _cfg_sem_ensemble()
    cfg["model"] = dict(cfg["model"], goal_half_life_days=0)
    with pytest.raises(ValueError, match="goal_half_life_days"):
        ServingStackEvaluator(cfg)


def test_h9_evaluator_mantem_params_congelados_e_elo_asof() -> None:
    obs = _obs(n_rodadas=20)
    cfg = _cfg_sem_ensemble()
    frozen = (0.1, 0.2, 0.03, -0.04)
    cfg["h9_frozen_policy"] = {"params": frozen, "max_goals": 6}
    evaluator = H9FrozenPolicyEvaluator(cfg)
    evaluator._fit(obs, obs[-1]["kickoff"] + timedelta(days=1))
    assert evaluator.params == frozen
    assert evaluator.elo
    assert evaluator.ensemble_enabled is False


# ---------- paridade com o serving ----------


def test_previsao_bate_com_a_pilha_do_serving_recomposta_a_mao() -> None:
    """A previsão tem que ser exatamente `model.predict_match` + `xg_model.blend`
    com os parâmetros ajustados — se divergir, o painel voltou a medir outra
    coisa que não o que `src/predict.py` serve."""
    obs = _obs()
    ev = ServingStackEvaluator(CFG)
    ev._fit(obs[:100], obs[100]["kickoff"])
    alvo = obs[100]

    ponto = ev.predict_step({k: v for k, v in alvo.items() if k != "result"})

    base = model.predict_match(
        ev.elo[alvo["home"]],
        ev.elo[alvo["away"]],
        ev.params,
        CFG["elo"]["home_advantage"],
        max_goals=CFG["model"]["max_goals"],
    )
    rx = xg_model.predict(ev.xg_params, alvo["home"], alvo["away"], max_goals=CFG["model"]["max_goals"])
    esperado = xg_model.blend(base, rx, w_base=CFG["ensemble_xg"]["blend_weight"])

    assert ponto.value["home"] == pytest.approx(esperado["p_win"])
    assert ponto.value["draw"] == pytest.approx(esperado["p_draw"])
    assert ponto.value["away"] == pytest.approx(esperado["p_loss"])


def test_ensemble_ligado_marca_o_modelo_no_metadata() -> None:
    ev = ServingStackEvaluator(CFG)
    r = ev.run(_obs(), min_history=30, retrain_every=10)
    assert r[0]["prediction"].metadata["model"] == "Ensemble(NB+DC, AtkDef-xG)"
    assert r[0]["prediction"].metadata["ensemble"] is True


def test_ensemble_desligado_cai_no_baseline_nb_dc() -> None:
    """Com a flag off o painel tem que medir NegBin+DixonColes puro — o mesmo
    que o serving faria."""
    ev = ServingStackEvaluator(_cfg_sem_ensemble())
    r = ev.run(_obs(), min_history=30, retrain_every=10)
    assert ev.xg_params is None
    assert r[0]["prediction"].metadata["model"] == "NegBin+DixonColes"


def test_sem_xg_na_base_o_ajuste_ainda_roda() -> None:
    """`xg_model.fit` cai nos gols reais quando falta xG. Isso não pode virar
    exceção nem degradação silenciosa."""
    ev = ServingStackEvaluator(CFG)
    r = ev.run(_obs(com_xg=False), min_history=30, retrain_every=10)
    assert r
    assert ev.xg_fit_failures == 0


# ---------- robustez ----------


def test_time_estreante_nao_derruba_a_avaliacao() -> None:
    """O serving faz `sys.exit` em time desconhecido; num replay histórico isso
    mataria a avaliação inteira por causa de um promovido. Aqui ele entra com o
    rating inicial."""
    obs = _obs()
    estreante = dict(obs[-1])
    estreante["home"] = "novorizontino"
    ev = ServingStackEvaluator(CFG)
    ev._fit(obs[:100], obs[100]["kickoff"])
    ponto = ev.predict_step({k: v for k, v in estreante.items() if k != "result"})
    assert sum(ponto.value.values()) == pytest.approx(1.0)


def test_probabilidades_somam_um() -> None:
    ev = ServingStackEvaluator(CFG)
    for r in ev.run(_obs(), min_history=30, retrain_every=10):
        assert sum(r["prediction"].value.values()) == pytest.approx(1.0)


def test_primeiro_ajuste_sem_historico_utilizavel_falha_alto() -> None:
    t0 = datetime(2021, 4, 3, 16, 0, tzinfo=UTC)
    obs = [
        {
            "home": TIMES[i % 2],
            "away": TIMES[(i % 2) + 2],
            "kickoff": t0,
            "date": "2021-04-03",
            "tournament": "Brasileirão Série A",
            "neutral": 0,
            "result": {"home_goals": 1, "away_goals": 0, "home_xg": 1.2, "away_xg": 0.3},
        }
        for i in range(24)
    ]
    with pytest.raises(ValueError, match="insuficiente"):
        ServingStackEvaluator(CFG).run(obs, min_history=10, retrain_every=1)
