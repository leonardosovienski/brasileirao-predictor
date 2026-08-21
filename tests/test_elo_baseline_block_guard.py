"""Guarda de bloco de kickoff no H₀ (Elo puro).

`EloBaselineEvaluator` reajusta a CADA passo (`retrain_every` default = 1), o
que é o pior caso possível para leakage de bloco simultâneo: sem guarda, toda
previsão de uma rodada treinaria com os resultados dos jogos vizinhos que ainda
não apitaram. Como este é o baseline contra o qual o Dixon-Coles precisa provar
valor, o leakage aqui INFLA o H₀ e faz o modelo parecer pior do que é.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.elo_baseline import EloBaselineEvaluator

TEAMS = ["flamengo", "palmeiras", "gremio", "santos"]


def _blocks(n_blocks: int, *, simultaneous: bool) -> list[dict]:
    t0 = datetime(2021, 4, 3, 16, 0, tzinfo=UTC)
    obs = []
    for b in range(n_blocks):
        start = t0 + timedelta(days=7 * b)
        pairs = [(TEAMS[0], TEAMS[1]), (TEAMS[2], TEAMS[3])]
        if b % 2:
            pairs = [(a, h) for h, a in pairs]
        for j, (home, away) in enumerate(pairs):
            obs.append(
                {
                    "home": home,
                    "away": away,
                    "kickoff": start if simultaneous else start + timedelta(hours=2 * j),
                    "result": {"home_goals": (b + j) % 3, "away_goals": (b + 2 * j) % 3},
                }
            )
    return obs


def test_predicted_at_e_estritamente_anterior_ao_matures_at() -> None:
    results = EloBaselineEvaluator().run(_blocks(40, simultaneous=True), min_history=10)
    assert results
    for r in results:
        assert r["prediction"].predicted_at < r["prediction"].matures_at


def test_bloco_simultaneo_e_descartado_do_treino() -> None:
    ev = EloBaselineEvaluator()
    ev.run(_blocks(40, simultaneous=True), min_history=10)
    assert ev.blocked_observations > 0


def test_kickoffs_distintos_nao_descartam_nada() -> None:
    ev = EloBaselineEvaluator()
    ev.run(_blocks(40, simultaneous=False), min_history=10)
    assert ev.blocked_observations == 0


def test_taxa_de_empate_sai_do_historico_truncado() -> None:
    """`draw_rate` vira P(empate) direto. Se fosse medida no histórico completo
    incluiria empates do próprio bloco previsto — leakage na probabilidade mais
    sensível do 1X2."""
    ev = EloBaselineEvaluator()
    ev.run(_blocks(40, simultaneous=True), min_history=10)
    assert 0.0 <= ev.draw_rate <= 1.0


def test_primeiro_ajuste_sem_historico_utilizavel_falha_alto() -> None:
    """Sem ratings anteriores para reutilizar, prever seria inventar. E o
    `draws / len(history)` do ajuste dividiria por zero."""
    t0 = datetime(2021, 4, 3, 16, 0, tzinfo=UTC)
    obs = [
        {
            "home": TEAMS[i % 2],
            "away": TEAMS[(i % 2) + 2],
            "kickoff": t0,
            "result": {"home_goals": 1, "away_goals": 0},
        }
        for i in range(20)
    ]
    with pytest.raises(ValueError, match="insuficiente"):
        EloBaselineEvaluator().run(obs, min_history=10)


def test_probabilidades_somam_um() -> None:
    results = EloBaselineEvaluator().run(_blocks(40, simultaneous=False), min_history=10)
    for r in results:
        v = r["prediction"].value
        assert sum(v.values()) == pytest.approx(1.0)
