from datetime import datetime, timedelta

import numpy as np
from bet_engine import (
    detect_arb,
    detect_ev,
    devig_power,
    devig_proportional,
    devig_shin,
    dsr,
    overround,
    power_analysis_n,
    psr,
    roi_ic_bootstrap,
    sharpe_de_retornos,
)

ODDS_EQUIL = [2.55, 3.20, 2.90]
ODDS_FAV = [1.57, 3.90, 5.75]
ODDS_ZEBRA = [1.25, 5.50, 11.0]


class TestDevig:
    def test_somam_um(self):
        for odds in [ODDS_EQUIL, ODDS_FAV, ODDS_ZEBRA, [1.95, 1.85]]:
            assert abs(devig_proportional(odds).sum() - 1) < 1e-9
            assert abs(devig_power(odds).sum() - 1) < 1e-9
            p, z = devig_shin(odds)
            assert abs(p.sum() - 1) < 1e-9 and 0 < z < 1

    def test_shin_infla_favorito(self):
        """Shin deve dar prob maior ao favorito que o proporcional (corrige FLB)."""
        p_shin, _ = devig_shin(ODDS_ZEBRA)
        assert p_shin[0] > devig_proportional(ODDS_ZEBRA)[0]

    def test_overround(self):
        assert abs(overround([2.0, 2.0]) - 1.0) < 1e-9


class TestEV:
    def test_detecta_edge_real(self):
        ts = datetime(2026, 8, 20, 19, 30)
        a = detect_ev(
            [1.90, 3.40, 4.20],
            [2.05, 3.30, 4.10],
            "CasaA",
            "EV1",
            "1X2",
            ["h", "d", "a"],
            ev_threshold=0.03,
            ts_now=ts,
            ts_pin=ts,
        )
        assert len(a) == 1 and a[0].selection == "h" and a[0].ev > 0.03

    def test_staleness_bloqueia(self):
        t0 = datetime(2026, 8, 20, 19, 30)
        a = detect_ev(
            [1.90, 3.40, 4.20],
            [2.05, 3.30, 4.10],
            "CasaA",
            "EV2",
            "1X2",
            ["h", "d", "a"],
            ts_now=t0 + timedelta(minutes=10),
            ts_pin=t0,
        )
        assert a == []

    def test_sem_edge_sem_alerta(self):
        a = detect_ev([1.90, 3.40, 4.20], [1.80, 3.20, 3.90], "CasaA", "EV3", "1X2", ["h", "d", "a"], ev_threshold=0.03)
        assert a == []


class TestArb:
    def test_arb_encontrada(self):
        r = detect_arb({"A": [2.10, 3.30, 3.60], "B": [1.95, 3.60, 3.40], "P": [2.00, 3.40, 4.30]}, ["h", "d", "a"])
        assert r["arb"] and r["profit_pct"] > 0.5
        assert abs(sum(leg[3] for leg in r["legs"]) - 1.0) < 1e-6

    def test_sem_arb(self):
        r = detect_arb({"A": [1.85, 3.30, 4.00], "B": [1.90, 3.25, 3.95]}, ["h", "d", "a"])
        assert not r["arb"]


class TestEstatistica:
    def test_power_cresce_com_odd(self):
        assert power_analysis_n(0.03, 3.2) > power_analysis_n(0.03, 1.9)

    def test_power_cai_com_edge(self):
        assert power_analysis_n(0.05, 1.9) < power_analysis_n(0.02, 1.9)

    def test_dsr_penaliza_trials(self):
        rng = np.random.default_rng(0)
        rets = rng.normal(0.02, 1.0, 500)
        sr = sharpe_de_retornos(rets)
        assert dsr(50, sr, 500) < psr(sr, 0, 500)

    def test_roi_ic(self):
        """Edge de 10% com 3000 apostas deve ter IC acima de zero
        (parâmetros compatíveis com power analysis: edge 10%, odd ~1.9)."""
        rng = np.random.default_rng(1)
        rets = rng.normal(0.10, 1.0, 3000)
        media, ic = roi_ic_bootstrap(rets)
        assert ic[0] > 0

    def test_sem_edge_ic_cobre_zero(self):
        rng = np.random.default_rng(2)
        rets = rng.normal(0.0, 1.0, 500)
        media, ic = roi_ic_bootstrap(rets)
        assert ic[0] <= 0 <= ic[1]
