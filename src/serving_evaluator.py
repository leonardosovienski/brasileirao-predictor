"""serving_evaluator — walk-forward do MODELO QUE REALMENTE SERVE.

Fecha a lacuna estrutural registrada em `docs/READINESS.md`: o painel canônico
media `BrasileiraoDixonColesEvaluator` (Poisson + Dixon-Coles puro), mas
`src/predict.py` serve `Ensemble(NB+DC, AtkDef-xG)` — Binomial Negativa com
ensemble de xG. Modelos diferentes em distribuição E em features. Promover
trial contra uma régua que não mede o que prevê significa que um GO pode não
transferir, e um NO-GO pode estar escondendo ganho real.

Este avaliador reconstrói a MESMA pilha do serving a cada reajuste:

    ratings.compute_ratings   → Elo (com a janela `elo.window_years`)
    model.fit_goal_model      → (a, b, alpha, rho) por MLE na janela de
                                calibração (`model.calibration_window_years`)
    model.predict_match       → grade NB+DC do confronto
    xg_model.fit / predict    → forças atk/def-xG
    xg_model.blend            → mistura das GRADES, como o serving faz

POR QUE NÃO DÁ PRA REUSAR O CACHE DO CRON
-----------------------------------------
`src/cron_update_models.py` ajusta com TODOS os jogos disputados da janela do
banco. Em produção isso é honesto — o cron roda "agora", e agora só existe
passado. Num backtest seria vazamento massivo: usar o mesmo cache para prever
2021 e 2024 daria ao modelo de 2021 o conhecimento de 2024. Por isso a pilha é
reajustada aqui dentro do laço, sobre o histórico truncado, em vez de lida do
cache.

GUARDA DE BLOCO DE KICKOFF
--------------------------
Mesma de `src/evaluator.py` e `src/elo_baseline.py`: `train_step` só ENFILEIRA
o histórico e o ajuste sai no `predict_step`, que conhece o kickoff do alvo e
trunca em `kickoff < alvo`. Rodada tem jogos simultâneos; sem isso o Elo e a
calibração absorveriam resultados que ainda não aconteceram.

PARIDADE, NÃO REIMPLEMENTAÇÃO
-----------------------------
Todas as etapas chamam as MESMAS funções do serving. Nada é reescrito aqui —
uma cópia divergiria com o tempo e o painel voltaria a medir outra coisa.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

from predictor_core.contracts.points import PredictionPoint
from predictor_core.testing.prequential import PrequentialEvaluator

from src import dynamic_strength, model, ratings, xg_model

__all__ = ["DynamicStrengthServingEvaluator", "ServingStackEvaluator"]


class ServingStackEvaluator(PrequentialEvaluator):
    """Walk-forward da pilha de serving.

    ev = ServingStackEvaluator(cfg)
    results = ev.run(observations, min_history=200, retrain_every=100)

    Formato de observação — o de `src/evaluator.py` MAIS os campos que a pilha
    de serving consome:

        {
            "home": "flamengo", "away": "palmeiras",
            "kickoff": datetime aware-UTC, "date": "2024-04-13",
            "tournament": "Brasileirão Série A", "neutral": 0,
            "result": {
                "home_goals": 2, "away_goals": 1,
                "home_xg": 1.7, "away_xg": 0.9,      # None é aceito
            },
        }

    `home_xg`/`away_xg` vivem DENTRO de `result` de propósito, pelo mesmo
    motivo dos gols em `src/evaluator.py`: a ABC remove só o `target_key` antes
    do `predict_step`, então campo de DESFECHO no nível de cima chegaria à
    previsão do próprio jogo. Aninhados, alimentam o AJUSTE a partir do
    histórico (passado estrito) e ficam invisíveis na hora de prever.
    """

    def __init__(self, cfg: dict[str, Any], *, max_goals: int | None = None) -> None:
        super().__init__(target_key="result")
        self.cfg = cfg
        self.max_goals: int = int(max_goals or cfg["model"]["max_goals"])
        self.goal_half_life_days: float | None = cfg["model"]["goal_half_life_days"]
        model.exponential_recency_weights([], "2000-01-01", self.goal_half_life_days)
        ecfg = (cfg.get("ensemble_xg") or {}) if cfg else {}
        self.ensemble_enabled: bool = bool(ecfg.get("enabled"))
        self.blend_weight: float = float(ecfg.get("blend_weight", 0.5))
        self.elo: dict[str, float] = {}
        self.params: tuple | None = None
        self.xg_params: dict[str, Any] | None = None
        self._trained_at: datetime | None = None
        self._pending_history: list[dict[str, Any]] | None = None
        self.blocked_observations: int = 0
        self.deferred_refits: int = 0
        self.xg_fit_failures: int = 0
        self.dynamic_states: dict[str, dict[str, float]] | None = None
        self.dynamic_cfg: dict[str, Any] | None = None

    # --- hooks do Template Method --------------------------------------------

    def train_step(self, history: list[dict[str, Any]]) -> None:
        """ENFILEIRA — o ajuste precisa do kickoff do alvo (guarda de bloco)."""
        self._pending_history = list(history)

    def predict_step(self, features: dict[str, Any]) -> PredictionPoint:
        if self._pending_history is not None:
            self._fit(self._pending_history, features["kickoff"])
            self._pending_history = None
        if self.params is None or self._trained_at is None:
            raise RuntimeError("predict_step antes de train_step — chamada fora de ordem")

        home, away = str(features["home"]), str(features["away"])
        neutral = bool(features.get("neutral"))
        adv = 0.0 if neutral else float(self.cfg["elo"]["home_advantage"])
        base = float(self.cfg["elo"]["initial_rating"])
        # Time sem rating (promovido, primeira aparição) cai no rating inicial —
        # o serving faz sys.exit aqui, o que num replay histórico mataria a
        # avaliação toda por causa de um clube estreante.
        r = model.predict_match(
            self.elo.get(home, base),
            self.elo.get(away, base),
            self.params,
            adv,
            max_goals=self.max_goals,
        )
        if self.dynamic_states is not None:
            corr_home, corr_away = dynamic_strength.corrections(self.dynamic_states, home, away)
            a, b, alpha, rho, _theta = model._unpack_params(self.params)
            diff = (self.elo.get(home, base) + adv - self.elo.get(away, base)) / 400.0
            lam_home = math.exp(a + b * diff + corr_home)
            lam_away = math.exp(a - b * diff + corr_away)
            grid = model._score_grid(lam_home, lam_away, alpha, rho, self.max_goals)
            r = {
                "lambda_a": lam_home,
                "lambda_b": lam_away,
                "total_goals": lam_home + lam_away,
                **model._grid_stats(grid, self.max_goals),
            }
        if self.xg_params is not None:
            rx = xg_model.predict(self.xg_params, home, away, neutral=neutral, max_goals=self.max_goals)
            r = xg_model.blend(r, rx, w_base=self.blend_weight)

        return PredictionPoint(
            predicted_at=self._trained_at,
            matures_at=features["kickoff"],
            value={"home": r["p_win"], "draw": r["p_draw"], "away": r["p_loss"]},
            metadata={
                "home": home,
                "away": away,
                "lam": r["lambda_a"],
                "mu": r["lambda_b"],
                # Diagnóstico PIT: diferença Elo efetiva já inclui mando (ou
                # sua remoção em campo neutro). Expor o valor permite que
                # controles negativos estratifiquem força sem reconstruir
                # ratings com risco de divergência/lookahead.
                "effective_elo_diff": self.elo.get(home, base) + adv - self.elo.get(away, base),
                # P(over 2.5) da PRÓPRIA grade servida — Negativa Binomial com
                # correção DC e, quando o ensemble está ligado, misturada com a
                # grade de xG. Reconstruir uma DixonColesMatrix a partir de
                # (lam, mu) no consumidor daria uma distribuição DIFERENTE da
                # que produziu o 1X2 logo acima: o OU e o 1X2 do mesmo relatório
                # deixariam de vir da mesma distribuição, que é exatamente o que
                # `xg_model.blend` mistura grades (e não probabilidades) para
                # garantir. Este evaluator não expõe `rho` porque a pilha de
                # serving não é uma DC pura — quem consome deve usar este campo.
                "p_over": float(r["over"][2.5]),
                "p_btts": float(r["btts"]),
                "ensemble": bool(r.get("ensemble")),
                "model": "Ensemble(NB+DC, AtkDef-xG)" if r.get("ensemble") else "NegBin+DixonColes",
            },
        )

    # --- ajuste ---------------------------------------------------------------

    def _fit(self, history: list[dict[str, Any]], horizon: datetime) -> None:
        usable = [h for h in history if h["kickoff"] < horizon]
        if len(usable) < 2:
            self.deferred_refits += 1
            if self.params is None:
                raise ValueError(
                    f"histórico anterior a {horizon.isoformat()} insuficiente para o primeiro "
                    f"ajuste ({len(usable)} de {len(history)}) — aumente min_history ou verifique "
                    "a ordenação por kickoff"
                )
            return
        self.blocked_observations += len(history) - len(usable)

        rows = [
            (
                h["date"],
                h["home"],
                h["away"],
                h["result"]["home_goals"],
                h["result"]["away_goals"],
                h.get("tournament") or self.cfg.get("tournament_name"),
                int(bool(h.get("neutral"))),
            )
            for h in usable
        ]
        # Mesmos dois cortes do cron, mas RELATIVOS ao último jogo do histórico
        # truncado — não à data de hoje. É o que dá paridade train/serve num
        # replay: em 2022 o cron teria visto uma janela terminando em 2022.
        asof = rows[-1][0]
        rows = self._window(rows, self.cfg["elo"].get("window_years"), asof)
        elo, hist = ratings.compute_ratings(rows, self.cfg["elo"], asof=horizon.date())
        cal_cut = _cut(asof, self.cfg["model"]["calibration_window_years"])
        hist_cal_rows = [(h, r) for h, r in zip(hist, rows) if r[0] >= cal_cut]
        hist_cal = [h for h, _r in hist_cal_rows]
        fit_rows = [r for _h, r in hist_cal_rows]
        if not hist_cal:
            hist_cal, fit_rows = hist, rows
        weights = model.exponential_recency_weights([r[0] for r in fit_rows], asof, self.goal_half_life_days)
        self.elo = elo
        self.params = model.fit_goal_model(hist_cal, sample_weights=weights)
        self.dynamic_states = self._fit_dynamic(hist, rows) if self.dynamic_cfg is not None else None
        self.xg_params = self._fit_xg(usable, asof) if self.ensemble_enabled else None
        self._trained_at = max(h["kickoff"] for h in usable)

    def _fit_dynamic(self, hist: list[tuple], rows: list[tuple]) -> dict[str, dict[str, float]]:
        if self.params is None or self.dynamic_cfg is None:
            raise RuntimeError("ajuste dinâmico exige parâmetros e configuração")
        return dynamic_strength.fit(
            hist,
            self.params,
            ((r[1], r[2]) for r in rows),
            alpha_short=float(self.dynamic_cfg["alpha_short"]),
            alpha_long=float(self.dynamic_cfg["alpha_long"]),
            ridge_reg=float(self.dynamic_cfg.get("ridge_reg", 1.0)),
            eps=float(self.dynamic_cfg.get("eps", 0.1)),
        )

    def _fit_xg(self, usable: list[dict[str, Any]], asof: str) -> dict[str, Any] | None:
        """Ajusta as forças atk/def-xG. Falha de ajuste degrada para o baseline
        puro, como `xg_model.maybe_blend` faz no serving — mas CONTA a
        degradação: um painel que silencia isso mediria o baseline achando que
        mede o ensemble."""
        matches = [
            (h["date"], h["home"], h["away"], h["result"]["home_goals"], h["result"]["away_goals"]) for h in usable
        ]
        xg_map = {
            (h["date"][:10], h["home"], h["away"]): (
                h["result"].get("home_xg"),
                h["result"].get("away_xg"),
            )
            for h in usable
        }
        try:
            return xg_model.fit(matches, xg_map, asof, self.cfg.get("ensemble_xg"))
        except Exception:
            self.xg_fit_failures += 1
            return None

    @staticmethod
    def _window(rows: list[tuple], window_years: float | None, asof: str) -> list[tuple]:
        if not window_years:
            return rows
        cut = _cut(asof, window_years)
        return [r for r in rows if r[0] >= cut] or rows


class DynamicStrengthServingEvaluator(ServingStackEvaluator):
    """Braço de pesquisa: serving atual + estados atk/def curto e longo."""

    def __init__(self, cfg: dict[str, Any], *, max_goals: int | None = None) -> None:
        super().__init__(cfg, max_goals=max_goals)
        self.dynamic_cfg = dict(cfg.get("dynamic_strength") or {})
        if not self.dynamic_cfg:
            raise ValueError("dynamic_strength ausente da configuracao")


class H9FrozenPolicyEvaluator(ServingStackEvaluator):
    """Exact H9 sports policy: live/as-of Elo plus frozen goal parameters."""

    def __init__(self, cfg: dict[str, Any], *, max_goals: int | None = None) -> None:
        frozen = cfg.get("h9_frozen_policy") or {}
        raw = frozen.get("params")
        if not isinstance(raw, (list, tuple)) or len(raw) != 4:
            raise ValueError("h9_frozen_policy.params deve conter a/b/alpha/rho")
        super().__init__(cfg, max_goals=max_goals or frozen.get("max_goals"))
        self.frozen_params = tuple(float(value) for value in raw)
        self.ensemble_enabled = False

    def _fit(self, history: list[dict[str, Any]], horizon: datetime) -> None:
        usable = [h for h in history if h["kickoff"] < horizon]
        if len(usable) < 2:
            self.deferred_refits += 1
            if self.params is None:
                raise ValueError("histórico insuficiente para política H9")
            return
        self.blocked_observations += len(history) - len(usable)
        rows = [
            (
                h["date"],
                h["home"],
                h["away"],
                h["result"]["home_goals"],
                h["result"]["away_goals"],
                h.get("tournament") or self.cfg.get("tournament_name"),
                int(bool(h.get("neutral"))),
            )
            for h in usable
        ]
        rows = self._window(rows, self.cfg["elo"].get("window_years"), rows[-1][0])
        self.elo, _history = ratings.compute_ratings(rows, self.cfg["elo"], asof=horizon.date())
        self.params = self.frozen_params
        self.xg_params = None
        self.dynamic_states = None
        self._trained_at = max(h["kickoff"] for h in usable)


def _cut(asof: str, years: float) -> str:
    return (date.fromisoformat(asof[:10]) - timedelta(days=int(float(years) * 365.25))).isoformat()
