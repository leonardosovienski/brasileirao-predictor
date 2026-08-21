"""elo_baseline — H₀ do Brasileirão: Elo puro → 1X2, sem gols, sem decaimento.

O baseline determinístico contra o qual o Dixon-Coles (H4) precisa provar
valor. É deliberadamente SIMPLES: ratings Elo clássicos (K fixo, vantagem de
casa em pontos de rating) e a probabilidade de empate tirada da FREQUÊNCIA
histórica da liga — nenhuma correlação de placar, nenhum peso temporal,
nenhum parâmetro ajustado por verossimilhança. Se o DC não bater ISTO com
significância, a complexidade extra não se paga.

Herda do mesmo `PrequentialEvaluator` do core que o avaliador DC usa: as duas
séries de previsão saem do MESMO fatiamento temporal (mesmo min_history, mesma
ordem de observações), o que garante o pareamento jogo-a-jogo do bootstrap por
construção — sem join frágil por ID.

GUARDA DE BLOCO DE KICKOFF
--------------------------
Mesma guarda de `src/evaluator.py`, pela mesma razão — e aqui ela pesa MAIS.
A ABC fatia por ÍNDICE, e este avaliador reajusta a cada passo (`retrain_every`
default = 1): sem guarda, TODA previsão de um bloco simultâneo treinaria com os
resultados dos jogos vizinhos que ainda não apitaram. Como este é o H₀ contra o
qual o Dixon-Coles precisa provar valor, o leakage aqui inflaria o baseline e
faria o DC parecer PIOR do que é — o espelho exato do risco do lado do modelo.

Correção idêntica à do DC: `train_step` só ENFILEIRA o histórico; o ajuste sai
no `predict_step`, que conhece o kickoff do alvo e trunca em `kickoff < alvo`.

Mapeamento Elo → 1X2 (dado p = expectativa Elo do mandante e d̄ = taxa
histórica de empates do treino):
    P(empate) = d̄
    P(casa)   = p · (1 − d̄)
    P(fora)   = (1 − p) · (1 − d̄)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from predictor_core.contracts.points import PredictionPoint
from predictor_core.testing.prequential import PrequentialEvaluator

__all__ = ["EloBaselineEvaluator"]

_INITIAL_RATING = 1500.0


class EloBaselineEvaluator(PrequentialEvaluator):
    """H₀: Elo puro no formato de observação do domínio (result = target blindado).

    ev = EloBaselineEvaluator()                     # K=20, casa=+80 pontos
    results = ev.run(observations, min_history=200)
    """

    def __init__(self, *, k: float = 20.0, home_advantage_elo: float = 80.0) -> None:
        super().__init__(target_key="result")
        self.k: float = k
        self.home_advantage_elo: float = home_advantage_elo
        self.ratings: dict[str, float] = {}
        self.draw_rate: float = 0.0
        self._trained_at: datetime | None = None
        self._pending_history: list[dict[str, Any]] | None = None
        self.blocked_observations: int = 0  # jogos do mesmo bloco descartados do treino
        self.deferred_refits: int = 0  # refits adiados por histórico insuficiente

    # --- hooks do Template Method --------------------------------------------

    def train_step(self, history: list[dict[str, Any]]) -> None:
        """ENFILEIRA o histórico — não ajusta aqui.

        O ajuste precisa do kickoff do alvo para truncar o bloco simultâneo (ver
        GUARDA DE BLOCO DE KICKOFF no topo), e o alvo só chega no `predict_step`."""
        self._pending_history = list(history)

    def _fit(self, history: list[dict[str, Any]], horizon: datetime) -> None:
        """Reconstrói os ratings do zero sobre os jogos com kickoff < `horizon`
        (determinístico: mesma história → mesmos ratings) e mede a taxa de
        empates do treino."""
        usable = [h for h in history if h["kickoff"] < horizon]
        if not usable:
            # Bloco engoliu o histórico inteiro: mantém os ratings anteriores e
            # tenta de novo no próximo passo, em vez de dividir por zero em
            # `draws / len(history)`.
            self.deferred_refits += 1
            if self._trained_at is None:
                raise ValueError(
                    f"histórico anterior a {horizon.isoformat()} insuficiente para o primeiro "
                    f"ajuste (0 jogos utilizáveis de {len(history)}) — aumente min_history ou "
                    "verifique a ordenação por kickoff"
                )
            return
        self.blocked_observations += len(history) - len(usable)
        history = usable
        ratings: dict[str, float] = {}
        draws = 0
        for h in history:
            home, away = h["home"], h["away"]
            hg = h["result"]["home_goals"]
            ag = h["result"]["away_goals"]
            r_h = ratings.get(home, _INITIAL_RATING)
            r_a = ratings.get(away, _INITIAL_RATING)
            expected = self._expected(r_h + self.home_advantage_elo, r_a)
            score = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
            if hg == ag:
                draws += 1
            ratings[home] = r_h + self.k * (score - expected)
            ratings[away] = r_a + self.k * (expected - score)
        self.ratings = ratings
        self.draw_rate = draws / len(history)
        self._trained_at = max(h["kickoff"] for h in history)

    def predict_step(self, features: dict[str, Any]) -> PredictionPoint:
        if self._pending_history is not None:
            self._fit(self._pending_history, features["kickoff"])
            self._pending_history = None
        if self._trained_at is None:
            raise RuntimeError("predict_step antes de train_step")
        r_h = self.ratings.get(str(features["home"]), _INITIAL_RATING)
        r_a = self.ratings.get(str(features["away"]), _INITIAL_RATING)
        p = self._expected(r_h + self.home_advantage_elo, r_a)
        d = self.draw_rate
        return PredictionPoint(
            predicted_at=self._trained_at,
            matures_at=features["kickoff"],
            value={"home": p * (1.0 - d), "draw": d, "away": (1.0 - p) * (1.0 - d)},
            metadata={
                "home": features["home"],
                "away": features["away"],
                "model": "elo_baseline",
                "k": self.k,
                "home_advantage_elo": self.home_advantage_elo,
            },
        )

    # --- interno --------------------------------------------------------------

    @staticmethod
    def _expected(rating_home: float, rating_away: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((rating_away - rating_home) / 400.0))
