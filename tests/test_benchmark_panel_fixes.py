"""Correções do painel canônico (auditoria 2026-08-21).

Cobre: IC95 presente na métrica primária, bootstrap de bloco móvel em vez de
iid, calibration slope ponderado por `n` do bin, e `--baseline` realmente
ligado (em vez de argumento morto).
"""

from __future__ import annotations

import pytest

from scripts import benchmark_predictor as bp
from src.evaluator import BrasileiraoDixonColesEvaluator
from src.serving_evaluator import ServingStackEvaluator

# ---------- delta_ci95 no formato de saída (Roadmap §6) ----------


def test_metric_record_carrega_delta_ci95_quando_fornecido() -> None:
    rec = bp._metric_record("rps", 0.21, baseline_value=0.23, n=100, is_primary=True, delta_ci95=(-0.03, -0.01))
    assert rec["delta_ci95"] == [-0.03, -0.01]
    assert rec["delta"] == pytest.approx(-0.02)


def test_delta_ci95_tem_o_sinal_do_campo_delta() -> None:
    """`delta` é modelo - baseline (negativo = modelo melhor). O IC precisa
    apontar para o mesmo lado, senão o relatório se contradiz."""
    modelo = [0.10] * 300
    baseline = [0.20] * 300
    ci = bp._delta_ci95(modelo, baseline)
    assert ci is not None
    assert ci[0] < 0 and ci[1] < 0, "modelo melhor deve dar IC do delta negativo"

    skill = bp._skill_score_ci(modelo, baseline)
    assert skill is not None
    assert skill[0] > 0, "o mesmo ganho, na orientação de skill score, é positivo"
    assert ci == pytest.approx((-skill[1], -skill[0]))


def test_delta_ci95_recusa_series_desalinhadas() -> None:
    assert bp._delta_ci95([0.1, 0.2], [0.1]) is None
    assert bp._delta_ci95([], []) is None


def test_turnos_usam_primeiro_e_segundo_confronto_em_temporada_incompleta() -> None:
    rows = [
        {"season": "2026", "date": "2026-01-10", "home": "A", "away": "B"},
        {"season": "2026", "date": "2026-01-11", "home": "C", "away": "D"},
        {"season": "2026", "date": "2026-07-10", "home": "B", "away": "A"},
    ]

    bp._tag_turno(rows)

    assert [row["turno"] for row in rows] == ["T1", "T1", "T2"]


def test_turnos_falham_alto_com_terceiro_confronto_na_mesma_temporada() -> None:
    rows = [
        {"season": "2026", "date": f"2026-0{i + 1}-01", "home": home, "away": away}
        for i, (home, away) in enumerate((("A", "B"), ("B", "A"), ("A", "B")))
    ]

    with pytest.raises(ValueError, match="mais de dois confrontos"):
        bp._tag_turno(rows)


def test_metrica_de_turno_carrega_baseline_delta_ic_e_n() -> None:
    rows = [
        {
            "p_loss": 0.2,
            "p_draw": 0.3,
            "p_win": 0.5,
            "actual_1x2": 2,
            "_baseline_probs_1x2": [0.4, 0.3, 0.3],
        }
        for _ in range(30)
    ]

    result = bp._stratum_metrics(rows, baseline="climatology")

    assert result["n"] == 30
    assert result["baseline"] == "climatology"
    assert result["rps_delta"] < 0
    assert result["rps_delta_ci95"][1] < 0


def test_metrica_de_turno_reporta_ou_e_accuracy_apenas_como_diagnostico() -> None:
    rows = [
        {
            "p_loss": 0.2,
            "p_draw": 0.3,
            "p_win": 0.5,
            "actual_1x2": 2,
            "p_over": 0.7,
            "actual_over": 1,
        }
    ]

    result = bp._stratum_metrics(rows)

    assert result["brier_ou25"] == pytest.approx(0.18)
    assert result["diagnostic_accuracy_1x2"] == 1.0
    assert result["diagnostic_ou25_hit_rate"] == 1.0


# ---------- bootstrap de bloco, não iid ----------


def test_bootstrap_usa_bloco_movel() -> None:
    """iid estreita o IC e superestima significância em série temporal. O
    painel é a régua de promoção: tem que ser o instrumento conservador."""
    assert bp.BLOCK_LENGTH > 1
    ci = bp._bootstrap_mean_ci([0.05] * 300)
    assert ci is not None and ci[0] <= ci[1]


def test_bootstrap_mean_ci_vazio_e_none() -> None:
    assert bp._bootstrap_mean_ci([]) is None


# ---------- calibration slope ponderado ----------


def _rows_ou(pairs: list[tuple[float, int]]) -> list[dict]:
    return [{"p_over": p, "actual_over": y} for p, y in pairs]


def test_slope_ignora_bin_minusculo_fora_da_curva() -> None:
    """Um bin com pouquíssimos jogos não pode ter a mesma alavancagem de um bin
    cheio: sem peso, a cauda governa o guardrail."""
    bem_calibrado = [(0.3, 0) for _ in range(200)] + [(0.7, 1) for _ in range(200)]
    ruido_de_cauda = [(0.95, 0), (0.05, 1)]
    com_ruido = bp._guardrails_ou25(_rows_ou(bem_calibrado + ruido_de_cauda))
    sem_ruido = bp._guardrails_ou25(_rows_ou(bem_calibrado))
    assert com_ruido["calibration_slope"] is not None
    assert sem_ruido["calibration_slope"] is not None
    # 2 jogos não podem mover o slope tanto quanto 400 movem.
    assert abs(com_ruido["calibration_slope"] - sem_ruido["calibration_slope"]) < 0.35


def test_guardrails_sem_observacao_devolvem_none() -> None:
    g = bp._guardrails_ou25([])
    assert g == {"ece": None, "calibration_slope": None, "resolution": None, "sharpness": None}


# ---------- --baseline deixou de ser argumento morto ----------


def test_baseline_desconhecido_falha_alto() -> None:
    """A docstring do painel promete NotImplementedError para baseline não
    plugado — devolver skill score contra baseline fantasma seria pior que
    falhar."""
    with pytest.raises(NotImplementedError, match="elo_baseline"):
        bp.run(model_tag="qualquer", start="", end="", baseline="current_v3")


def test_climatology_e_o_baseline_suportado() -> None:
    assert "climatology" in bp.SUPPORTED_BASELINES
    assert "market_no_vig" in bp.SUPPORTED_BASELINES


def test_market_no_vig_e_shin_na_orientacao_do_rps() -> None:
    probs = bp._market_no_vig_probs({"market_odds_1x2": (2.0, 3.5, 4.0)})
    assert probs is not None
    assert sum(probs) == pytest.approx(1.0)
    assert probs[2] > probs[0]


def test_market_no_vig_rejeita_mercado_incompleto_ou_invalido() -> None:
    assert bp._market_no_vig_probs({"market_odds_1x2": (2.0, None, 4.0)}) is None
    assert bp._market_no_vig_probs({"market_odds_1x2": (2.0, 1.0, 4.0)}) is None


# ---------- seletor de motor (alinhamento painel × serving) ----------


def test_engine_desconhecido_falha_alto() -> None:
    with pytest.raises(NotImplementedError, match="engine"):
        bp._make_evaluator("regressao_magica", 120.0, None)


def test_engine_default_continua_sendo_dixon_coles() -> None:
    """Trocar o default de repente invalidaria as medições já feitas contra o
    motor histórico — inclusive a trial h11 em curso."""
    assert bp.DEFAULT_ENGINE == "dixon_coles"
    ev = bp._make_evaluator("dixon_coles", 120.0, None)
    assert isinstance(ev, BrasileiraoDixonColesEvaluator)


def test_engine_serving_instancia_a_pilha_de_producao() -> None:
    cfg = {
        "tournament_name": "Brasileirão Série A",
        "elo": {
            "initial_rating": 1500,
            "home_advantage": 100,
            "window_years": 6,
            "form_half_life_years": 4.0,
            "k_factors": {"default": 30},
        },
        "model": {"calibration_window_years": 4, "goal_half_life_days": 360, "max_goals": 6},
        "ensemble_xg": {"enabled": True, "blend_weight": 0.5},
    }
    ev = bp._make_evaluator("serving", 120.0, cfg)
    assert isinstance(ev, ServingStackEvaluator)
    assert ev.ensemble_enabled is True


def test_engine_serving_exige_config() -> None:
    """Sem config.yaml não há Elo, janela de calibração nem flag do ensemble —
    seguir em frente mediria um modelo que ninguém configurou."""
    with pytest.raises(SystemExit, match="config.yaml"):
        bp._make_evaluator("serving", 120.0, None)


# ---------- OU 2.5 vem do motor que produziu a linha (bug do --engine serving) ----------


def _liga_sintetica(monkeypatch, rodadas: int = 90) -> None:
    """Base pequena com o DDL REAL, kickoff de verdade e horários distintos.

    Não é dado de pesquisa — é o mínimo para que o PRODUTOR rode. O ponto do
    teste é justamente não fabricar as linhas do painel à mão: foi assim que o
    `KeyError: actual_ou25` da auditoria anterior passou batido."""
    import pathlib
    import tempfile
    from datetime import UTC, datetime, timedelta

    from src import db as _db

    times = ["flamengo", "palmeiras", "gremio", "santos", "corinthians", "bahia"]
    path = pathlib.Path(tempfile.mkdtemp()) / "m.db"
    conn = _db.connect(str(path))
    eid = 0
    for rodada in range(rodadas):
        dia = datetime(2021, 4, 3, tzinfo=UTC) + timedelta(days=7 * rodada)
        pares = [(times[0], times[1]), (times[2], times[3]), (times[4], times[5])]
        if rodada % 2:
            pares = [(a, h) for h, a in pares]
        for j, (casa, fora) in enumerate(pares):
            d = dia.strftime("%Y-%m-%d")
            # dois jogos no MESMO horário: é o caso que a guarda de bloco cobre
            kickoff = (dia + timedelta(hours=16 + 2 * (j // 2))).isoformat(timespec="seconds")
            gols_casa, gols_fora = (rodada + j) % 4, (rodada + 2 * j) % 3
            conn.execute(
                "INSERT INTO matches (date, home_team, away_team, home_score, away_score, tournament, neutral)"
                " VALUES (?,?,?,?,?,?,0)",
                (d, casa, fora, gols_casa, gols_fora, "Brasileirão Série A"),
            )
            conn.execute(
                "INSERT INTO sofascore_matches (event_id, date, kickoff_at, home_team, away_team,"
                " home_score, away_score, home_xg, away_xg) VALUES (?,?,?,?,?,?,?,?,?)",
                (eid, d, kickoff, casa, fora, gols_casa, gols_fora, gols_casa + 0.3, gols_fora + 0.2),
            )
            eid += 1
    conn.commit()
    conn.close()
    monkeypatch.setattr(bp, "DB", path)


def test_p_over_do_serving_vem_da_grade_servida() -> None:
    """A pilha de serving não é uma DC pura — ela entrega a própria P(over)."""
    assert bp._p_over_from({"lam": 1.4, "mu": 1.1, "p_over": 0.61}) == pytest.approx(0.61)


def test_p_over_do_dixon_coles_reconstroi_a_matriz() -> None:
    """No motor DC a matriz reconstruída É a distribuição certa."""
    p = bp._p_over_from({"lam": 1.4, "mu": 1.1, "rho": -0.05})
    assert 0.0 < p < 1.0


def test_p_over_falha_alto_sem_p_over_e_sem_rho() -> None:
    """Inventar um número plausível aqui contaminaria o guardrail de OU."""
    with pytest.raises(KeyError, match="p_over.*rho|rho"):
        bp._p_over_from({"lam": 1.4, "mu": 1.1})


def test_walkforward_serving_produz_linhas_de_ponta_a_ponta(monkeypatch) -> None:
    """Regressão do `KeyError: 'rho'` com `--engine serving`.

    Os testes existentes cobriam `_make_evaluator('serving', ...)` — que só
    CONSTRÓI o objeto — e o evaluator isolado. Nenhum rodava
    `_run_walkforward`, então o painel morria depois do walk-forward inteiro,
    ao montar as linhas. Mesma lição do `actual_ou25`: testar a peça não é
    testar o produtor."""
    _liga_sintetica(monkeypatch)
    monkeypatch.setattr(bp, "MIN_HISTORY", 30)
    cfg = bp.load_config()
    observations = bp._load_observations("")

    rows, ev = bp._run_walkforward(observations, half_life=120.0, retrain_every=20, engine="serving", cfg=cfg)

    assert rows, "walk-forward do serving não produziu linhas"
    assert isinstance(ev, ServingStackEvaluator)
    for r in rows:
        assert 0.0 < r["p_over"] < 1.0, "P(over 2.5) fora de (0,1)"
        assert r["p_win"] + r["p_draw"] + r["p_loss"] == pytest.approx(1.0, abs=1e-6)
        assert r["lambda_total"] > 0


# ---------- o relatório carimba o estado do ensemble (reprodutibilidade do P2) ----------


class _EvFake:
    """Duplo mínimo: só os atributos que o relatório lê do evaluator."""

    def __init__(self, **kw) -> None:
        self.__dict__.update(kw)


def test_ensemble_state_none_no_motor_sem_xg() -> None:
    """`dixon_coles` não tem ensemble — o campo não deve inventar um estado."""
    assert bp._ensemble_state(_EvFake(blocked_observations=0)) is None


def test_ensemble_state_carimba_ligado() -> None:
    st = bp._ensemble_state(_EvFake(ensemble_enabled=True, blend_weight=0.5))
    assert st == {"enabled": True, "blend_weight": 0.5}


def test_ensemble_state_carimba_desligado() -> None:
    """Com o ensemble desligado o `blend_weight` não descreve nada — reportá-lo
    sugeriria uma mistura que não aconteceu."""
    st = bp._ensemble_state(_EvFake(ensemble_enabled=False, blend_weight=0.5))
    assert st == {"enabled": False, "blend_weight": None}


def test_xg_fit_failures_none_quando_nem_foi_tentado() -> None:
    """Com a flag desligada, `_fit_xg` nunca é chamado e o contador fica em 0.
    Reportar 0 aí é indistinguível de "tentou e nunca falhou" — foi o que fez
    duas corridas do P2 parecerem a mesma medição."""
    assert bp._xg_fit_failures(_EvFake(ensemble_enabled=False, xg_fit_failures=0)) is None
    assert bp._xg_fit_failures(_EvFake(blocked_observations=0)) is None


def test_xg_fit_failures_conta_quando_foi_tentado() -> None:
    assert bp._xg_fit_failures(_EvFake(ensemble_enabled=True, xg_fit_failures=0)) == 0
    assert bp._xg_fit_failures(_EvFake(ensemble_enabled=True, xg_fit_failures=7)) == 7


def test_relatorio_do_serving_carimba_o_ensemble_de_ponta_a_ponta(monkeypatch) -> None:
    """Dois relatórios de `--engine serving`, um com ensemble e outro sem,
    precisam ser distinguíveis pelo CONTEÚDO do JSON."""
    _liga_sintetica(monkeypatch)
    monkeypatch.setattr(bp, "MIN_HISTORY", 30)
    # A flag é FORÇADA nos dois braços, não lida do config.yaml: `enabled` é
    # estado de produção e muda (mudou, em 2026-08-22). Um teste que herda esse
    # valor passa ou falha conforme a operação, não conforme o código.
    base = bp.load_config()
    cfg_on = {**base, "ensemble_xg": {**(base.get("ensemble_xg") or {}), "enabled": True}}
    cfg_off = {**base, "ensemble_xg": {**(base.get("ensemble_xg") or {}), "enabled": False}}
    observations = bp._load_observations("")

    _rows, ev_on = bp._run_walkforward(observations, half_life=120.0, retrain_every=20, engine="serving", cfg=cfg_on)
    assert bp._ensemble_state(ev_on)["enabled"] is True
    assert bp._xg_fit_failures(ev_on) is not None

    _rows, ev_off = bp._run_walkforward(observations, half_life=120.0, retrain_every=20, engine="serving", cfg=cfg_off)
    assert bp._ensemble_state(ev_off)["enabled"] is False
    assert bp._xg_fit_failures(ev_off) is None
