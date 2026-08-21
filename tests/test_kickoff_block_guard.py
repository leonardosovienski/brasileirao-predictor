"""Guarda de bloco de kickoff no walk-forward (pré-requisito do RESEARCH-01A).

A ABC prequential do core fatia por ÍNDICE. Rodada de futebol tem jogos
SIMULTÂNEOS, e `matches.date` é data-sem-hora: sem guarda, o enésimo jogo de um
bloco treina com resultados que ainda não tinham acontecido. O viés cresce
quando o refit fica mais frequente — justamente a variável que o RESEARCH-01A
manipula —, então o braço TREATMENT ganharia de graça.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.evaluator import BrasileiraoDixonColesEvaluator

TEAMS = ["flamengo", "palmeiras", "gremio", "santos"]


def _round_robin_blocks(n_blocks: int, *, simultaneous: bool) -> list[dict]:
    """Blocos de 2 jogos. `simultaneous=True` dá o MESMO kickoff aos 3 (o caso
    real da rodada e o caso degenerado da data-sem-hora)."""
    t0 = datetime(2021, 4, 3, 16, 0, tzinfo=UTC)
    obs = []
    for b in range(n_blocks):
        block_start = t0 + timedelta(days=7 * b)
        pairs = [(TEAMS[0], TEAMS[1]), (TEAMS[2], TEAMS[3])]
        if b % 2:
            pairs = [(a, h) for h, a in pairs]
        for j, (home, away) in enumerate(pairs):
            kickoff = block_start if simultaneous else block_start + timedelta(hours=2 * j)
            obs.append(
                {
                    "home": home,
                    "away": away,
                    "kickoff": kickoff,
                    "result": {"home_goals": (b + j) % 4, "away_goals": (b + 2 * j) % 3},
                }
            )
    return obs


class _SpyEvaluator(BrasileiraoDixonColesEvaluator):
    """Registra o kickoff mais recente REALMENTE usado em cada ajuste."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.fit_horizons: list[tuple[datetime, datetime]] = []

    def _fit(self, history, horizon):  # type: ignore[override]
        super()._fit(history, horizon)
        if self._trained_at is not None:
            self.fit_horizons.append((self._trained_at, horizon))


@pytest.mark.parametrize("retrain_every", [1, 4, 9])
def test_treino_nunca_alcanca_o_kickoff_do_alvo(retrain_every: int) -> None:
    """Invariante central: nenhum ajuste usa jogo com kickoff >= o do alvo."""
    obs = _round_robin_blocks(24, simultaneous=True)
    ev = _SpyEvaluator(half_life_days=120, max_goals=4)
    ev.run(obs, min_history=16, retrain_every=retrain_every)
    assert ev.fit_horizons, "nenhum ajuste aconteceu"
    for trained_at, horizon in ev.fit_horizons:
        assert trained_at < horizon, f"treinou até {trained_at} para prever {horizon}"


def test_bloco_simultaneo_e_efetivamente_descartado() -> None:
    """Com kickoffs idênticos dentro do bloco, a guarda TEM que morder."""
    obs = _round_robin_blocks(24, simultaneous=True)
    ev = BrasileiraoDixonColesEvaluator(half_life_days=120, max_goals=4)
    ev.run(obs, min_history=16, retrain_every=1)
    assert ev.blocked_observations > 0


def test_kickoffs_distintos_nao_descartam_nada() -> None:
    """Com horários distintos, treinar no jogo de sábado para prever o de
    domingo é legítimo — a guarda não pode cobrar pedágio à toa."""
    obs = _round_robin_blocks(24, simultaneous=False)
    ev = BrasileiraoDixonColesEvaluator(half_life_days=120, max_goals=4)
    ev.run(obs, min_history=16, retrain_every=1)
    assert ev.blocked_observations == 0


def test_predicted_at_e_estritamente_anterior_ao_matures_at() -> None:
    """O contrato do core exige >=; a guarda promete o > estrito."""
    obs = _round_robin_blocks(24, simultaneous=True)
    ev = BrasileiraoDixonColesEvaluator(half_life_days=120, max_goals=4)
    results = ev.run(obs, min_history=16, retrain_every=5)
    assert results
    for r in results:
        pred = r["prediction"]
        assert pred.predicted_at < pred.matures_at


def test_cadencia_de_refit_continua_valendo() -> None:
    """O fit preguiçoso não pode virar refit a cada passo por acidente: a
    cadência do core é a variável do experimento e precisa ser respeitada."""
    obs = _round_robin_blocks(40, simultaneous=False)
    frequente = _SpyEvaluator(half_life_days=120, max_goals=4)
    frequente.run(obs, min_history=16, retrain_every=1)
    raro = _SpyEvaluator(half_life_days=120, max_goals=4)
    raro.run(obs, min_history=16, retrain_every=20)
    assert len(frequente.fit_horizons) > len(raro.fit_horizons)
    assert len(raro.fit_horizons) <= len(frequente.fit_horizons) // 5


def test_primeiro_ajuste_sem_historico_utilizavel_falha_alto() -> None:
    """Se o bloco engolir todo o histórico ANTES do primeiro ajuste, não há o
    que reutilizar — estourar é melhor que prever com parâmetro fantasma."""
    t0 = datetime(2021, 4, 3, 16, 0, tzinfo=UTC)
    obs = [
        {
            "home": TEAMS[i % 2],
            "away": TEAMS[(i % 2) + 2],
            "kickoff": t0,  # TUDO no mesmo instante
            "result": {"home_goals": 1, "away_goals": 0},
        }
        for i in range(24)
    ]
    ev = BrasileiraoDixonColesEvaluator(half_life_days=120, max_goals=4)
    with pytest.raises(ValueError, match="insuficiente"):
        ev.run(obs, min_history=16, retrain_every=1)
