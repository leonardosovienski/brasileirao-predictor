"""evaluator — walk-forward Dixon-Coles sobre o PrequentialEvaluator do core (H4).

Herda de `predictor_core.testing.prequential.PrequentialEvaluator` (v1.3.0):
o CORE controla o fatiamento temporal (train_step só vê o passado estrito;
predict_step recebe a observação SEM o target_key) — anti-leakage estrutural,
não disciplinar. Este módulo só implementa os dois hooks de domínio.

Formato de observação (uma por jogo, ORDENADA por kickoff — responsabilidade
do chamador, como documenta a ABC):

    {
        "home": "flamengo", "away": "palmeiras",
        "kickoff": datetime aware-UTC,
        "result": {"home_goals": 2, "away_goals": 1},   # <- target_key
    }

Os gols realizados vivem DENTRO de `result` de propósito: a ABC remove só o
target_key das features, então qualquer campo de resultado fora dele vazaria
para o predict_step. `train_step` lê `result` do histórico (que chega completo);
`predict_step` recebe {home, away, kickoff} e nada mais.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from predictor_core.contracts.points import PredictionPoint
from predictor_core.testing.prequential import PrequentialEvaluator

from src.dixon_coles import DixonColesMatrix, fit_dixon_coles_parameters

__all__ = ["BrasileiraoDixonColesEvaluator"]

_DEFAULT_STRENGTH = 1.0  # time nunca visto no histórico: força neutra (média=1)


class BrasileiraoDixonColesEvaluator(PrequentialEvaluator):
    """Avaliação prequential do Dixon-Coles no Brasileirão.

    ev = BrasileiraoDixonColesEvaluator(half_life_days=120)
    results = ev.run(observations, min_history=60, retrain_every=10)
    # cada item: {"index", "prediction": PredictionPoint, "actual": result}

    `prediction` é um `predictor_core.contracts.points.PredictionPoint`:
      predicted_at = kickoff do último jogo do histórico (o instante em que o
                     modelo "sabia" o que sabia — usar utcnow() aqui quebraria
                     a reprodutibilidade do replay);
      matures_at   = kickoff do jogo previsto (invariante matures_at >=
                     predicted_at é checada pelo próprio contrato);
      value        = {"home", "draw", "away"} somando 1 (ordinal p/ rps);
      metadata     = times, rho, gamma e ξ vigentes.
    """

    def __init__(self, half_life_days: float, *, max_goals: int = 10) -> None:
        super().__init__(target_key="result")
        if half_life_days <= 0:
            raise ValueError(f"half_life_days deve ser > 0 (recebido {half_life_days})")
        self.xi: float = math.log(2.0) / half_life_days
        self.max_goals: int = max_goals
        self.fitted_parameters: dict[str, Any] | None = None
        self._trained_at: datetime | None = None

    # --- hooks do Template Method (core controla o fatiamento) --------------

    def train_step(self, history: list[dict[str, Any]]) -> None:
        """Ajusta (α, β, γ, ρ) por WNLL sobre o passado estrito recebido do core."""
        cutoff: datetime = max(h["kickoff"] for h in history)
        games = [
            {
                "home": h["home"],
                "away": h["away"],
                "home_goals": h["result"]["home_goals"],
                "away_goals": h["result"]["away_goals"],
                "days_ago": (cutoff - h["kickoff"]).total_seconds() / 86400.0,
            }
            for h in history
        ]
        self.fitted_parameters = fit_dixon_coles_parameters(games, self.xi, max_goals=self.max_goals)
        self._trained_at = cutoff

    def predict_step(self, features: dict[str, Any]) -> PredictionPoint:
        """Monta a DixonColesMatrix do confronto e devolve o PredictionPoint 1X2."""
        if self.fitted_parameters is None or self._trained_at is None:
            raise RuntimeError(
                "predict_step antes de train_step — a ABC do core nunca faz isso; chamada manual fora de ordem"
            )
        p = self.fitted_parameters
        home, away = str(features["home"]), str(features["away"])
        alpha_h = p["attack"].get(home, _DEFAULT_STRENGTH)
        alpha_a = p["attack"].get(away, _DEFAULT_STRENGTH)
        beta_h = p["defense"].get(home, _DEFAULT_STRENGTH)
        beta_a = p["defense"].get(away, _DEFAULT_STRENGTH)
        lam = alpha_h * beta_a * p["home_advantage"]
        mu = alpha_a * beta_h
        rho = self._clamp_rho(p["rho"], lam, mu)
        matrix = DixonColesMatrix(lam, mu, rho, max_goals=self.max_goals)
        return PredictionPoint(
            predicted_at=self._trained_at,
            matures_at=features["kickoff"],
            value=matrix.outcome_probs(),
            metadata={
                "home": home,
                "away": away,
                "rho": rho,
                "home_advantage": p["home_advantage"],
                "xi": self.xi,
            },
        )

    # --- interno -------------------------------------------------------------

    @staticmethod
    def _clamp_rho(rho: float, lam: float, mu: float, margin: float = 1e-6) -> float:
        """O ρ global foi ajustado sobre os (λ, μ) do treino; um confronto novo
        pode ter médias que estreitam a faixa da Eq. 4.3. Clampa para dentro da
        faixa válida DESTE confronto em vez de explodir na construção."""
        lo, hi = DixonColesMatrix.valid_rho_bounds(lam, mu)
        return min(max(rho, lo + margin), hi - margin)
