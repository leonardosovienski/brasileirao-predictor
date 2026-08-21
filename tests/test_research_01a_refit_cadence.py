"""RESEARCH-01A — mecânica do experimento de cadência de reajuste.

Não testa o VEREDITO (isso depende da base real do operador); testa que o
experimento é honesto: braços pareados jogo a jogo, uma variável só, holdout
de 2025 recusado por padrão, e o veredito respeitando primária + guardrails.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from scripts import research_01a_refit_cadence as r01a
from scripts.benchmark_predictor import _kickoff, _load_observations

# ---------- kickoff real vs. fallback ----------


def test_kickoff_usa_o_horario_real_quando_existe() -> None:
    got = _kickoff("2026-08-20", "2026-08-20T22:30:00+00:00")
    assert got == datetime(2026, 8, 20, 22, 30, tzinfo=UTC)


def test_kickoff_cai_para_meia_noite_utc_sem_horario() -> None:
    """Sem hora, a rodada inteira vira um bloco simultâneo — perder histórico é
    a leitura honesta; inventar uma ordem é que seria leakage."""
    assert _kickoff("2026-08-20", None) == datetime(2026, 8, 20, 0, 0, tzinfo=UTC)


def test_kickoff_normaliza_sufixo_z() -> None:
    assert _kickoff("2026-08-20", "2026-08-20T22:30:00Z") == datetime(2026, 8, 20, 22, 30, tzinfo=UTC)


# ---------- ordenação por relógio ----------


def _seed_db(path, *, com_kickoff: bool) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE matches (date TEXT, home_team TEXT, away_team TEXT, home_score INT, away_score INT,"
        " PRIMARY KEY (date, home_team, away_team));"
        "CREATE TABLE sofascore_matches (event_id INTEGER PRIMARY KEY, date TEXT, kickoff_at TEXT,"
        " home_team TEXT, away_team TEXT);"
    )
    # Mesmo dia, horários DECRESCENTES na ordem de inserção: se o carregador
    # ordenasse por `date`, a ordem da lista sairia invertida no relógio.
    jogos = [
        ("2021-04-03", "flamengo", "palmeiras", "2021-04-03T21:00:00+00:00"),
        ("2021-04-03", "gremio", "santos", "2021-04-03T18:00:00+00:00"),
        ("2021-04-03", "bahia", "vasco", "2021-04-03T16:00:00+00:00"),
    ]
    for i, (d, h, a, k) in enumerate(jogos):
        conn.execute("INSERT INTO matches VALUES (?,?,?,?,?)", (d, h, a, 1, 0))
        if com_kickoff:
            conn.execute("INSERT INTO sofascore_matches VALUES (?,?,?,?,?)", (i, d, k, h, a))
    conn.commit()
    conn.close()


def test_observacoes_saem_ordenadas_pelo_relogio(tmp_path, monkeypatch) -> None:
    db = tmp_path / "m.db"
    _seed_db(db, com_kickoff=True)
    monkeypatch.setattr("scripts.benchmark_predictor.DB", db)
    obs = _load_observations("")
    assert [o["kickoff"].hour for o in obs] == [16, 18, 21]
    assert all(o["has_real_kickoff"] for o in obs)


def test_sem_kickoff_marca_o_fallback(tmp_path, monkeypatch) -> None:
    """`has_real_kickoff` alimenta `kickoff_coverage` no relatório — sem ele o
    operador não sabe quanta guarda de bloco foi cobrada por dado faltando."""
    db = tmp_path / "m.db"
    _seed_db(db, com_kickoff=False)
    monkeypatch.setattr("scripts.benchmark_predictor.DB", db)
    obs = _load_observations("")
    assert not any(o["has_real_kickoff"] for o in obs)
    assert {o["kickoff"] for o in obs} == {datetime(2021, 4, 3, tzinfo=UTC)}


# ---------- pareamento e veredito ----------


def test_ganho_pareado_tem_sinal_de_melhora_do_tratamento() -> None:
    """Ganho = perda do control menos perda do treatment: positivo = tratamento
    melhor. Sinal trocado inverteria todo veredito silenciosamente."""
    control = [0.30] * 200
    treatment = [0.20] * 200
    out = r01a._paired_gain(control, treatment)
    assert out["mean_gain"] == pytest.approx(0.10)
    assert out["ci95"][0] > 0


def test_perdas_pareadas_saem_uma_por_jogo() -> None:
    rows = [
        {"p_loss": 0.2, "p_draw": 0.3, "p_win": 0.5, "actual_1x2": 2, "p_over": 0.6, "actual_ou25": 1},
        {"p_loss": 0.5, "p_draw": 0.3, "p_win": 0.2, "actual_1x2": 0, "p_over": 0.4, "actual_ou25": 0},
    ]
    losses = r01a._paired_losses(rows)
    assert set(losses) == {"rps", "brier_1x2", "log_loss", "brier_ou25"}
    assert all(len(v) == len(rows) for v in losses.values())


def test_veredito_refuta_quando_ic95_cruza_zero() -> None:
    primary = {"ci95": [-0.001, 0.002]}
    status, detail = r01a._verdict(primary, {})
    assert status == "refutada"
    assert "cruza zero" in detail


def test_veredito_refuta_quando_guardrail_piora_materialmente() -> None:
    """RPS melhorar não compra o direito de degradar log-loss — Regra 3: o
    ganho tem que vir do mecanismo, não de um trade-off escondido."""
    primary = {"ci95": [0.001, 0.004]}
    guardrails = {"log_loss": {"ci95": [-0.02, -0.005]}}
    status, detail = r01a._verdict(primary, guardrails)
    assert status == "refutada"
    assert "guardrail" in detail


def test_veredito_comprova_com_primaria_positiva_e_guardrails_intactos() -> None:
    primary = {"ci95": [0.001, 0.004]}
    guardrails = {"log_loss": {"ci95": [-0.001, 0.003]}}
    status, _ = r01a._verdict(primary, guardrails)
    assert status == "comprovada"


def test_guardrail_apenas_ruidoso_nao_veta() -> None:
    """IC95 que cruza zero é ruído, não piora material — vetar com isso vira
    veto arbitrário e reabre a porta pro cherry-picking."""
    primary = {"ci95": [0.001, 0.004]}
    guardrails = {"brier_1x2": {"ci95": [-0.004, 0.006]}}
    status, _ = r01a._verdict(primary, guardrails)
    assert status == "comprovada"


# ---------- holdout selado ----------


@pytest.mark.parametrize("period", ["2021-01-01,2025-06-30", "2021-01-01,2026-12-31", "2021-01-01,"])
def test_recusa_periodo_que_alcanca_o_holdout_selado(period, monkeypatch) -> None:
    """Regra 7: usar 2025 para escolher cadência faz 2025 deixar de ser holdout.
    O script recusa em vez de confiar na disciplina de quem digita."""
    import sys

    monkeypatch.setattr(sys, "argv", ["research_01a", "--period", period])
    assert r01a.main() == 1


def test_periodo_dentro_do_desenvolvimento_passa_da_trava(monkeypatch) -> None:
    """A trava não pode barrar o período legítimo — senão o experimento não roda."""
    import sys

    monkeypatch.setattr(sys, "argv", ["research_01a", "--period", "2021-01-01,2024-12-31", "--pre-register-only"])
    chamou: dict = {}
    monkeypatch.setattr(r01a, "load_config", lambda: {})
    monkeypatch.setattr(r01a, "attest_rps_power", lambda: {"pipeline_fingerprint": "deadbeef"})

    class _FakeRegistry:
        def __init__(self, *a, **kw) -> None: ...

        def register(self, name, **kw):
            chamou["name"] = name
            chamou["status"] = kw.get("status")
            return []

    monkeypatch.setattr(r01a, "TrialRegistry", _FakeRegistry)
    assert r01a.main() == 0
    assert chamou["name"] == r01a.TRIAL_NAME
    assert chamou["status"] == "pre-registrada"


# ---------- identidade da trial ----------


def test_params_carregam_a_variavel_manipulada() -> None:
    """Os params SÃO a identidade da configuração no registro do core: se a
    cadência não estiver ali, dois experimentos diferentes colidiriam na mesma
    trial e o DSR pararia de descontá-los separadamente."""
    params = r01a._trial_params("2021-01-01", "2024-12-31")
    assert params["variable"] == "retrain_every"
    assert params["control"] == r01a.CONTROL_RETRAIN
    assert params["treatment"] == r01a.TREATMENT_RETRAIN
    assert params["control"] != params["treatment"]
