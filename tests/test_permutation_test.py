"""Controle negativo do pipeline — mecânica do teste de permutação.

Não roda o walk-forward completo (isso é execução de operador, custa horas);
testa que o instrumento é honesto: o embaralhamento destrói o vínculo
time↔desfecho SEM mexer nas marginais, o veredito lê o sinal certo, e o
holdout selado é recusado.
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest

from scripts import permutation_test as pt

TIMES = ["flamengo", "palmeiras", "gremio", "santos"]


def _obs(n: int = 200) -> list[dict]:
    t0 = datetime(2021, 4, 3, 16, 0, tzinfo=UTC)
    out = []
    for i in range(n):
        kickoff = t0 + timedelta(days=3 * i)
        out.append(
            {
                "home": TIMES[i % 4],
                "away": TIMES[(i + 1) % 4],
                "kickoff": kickoff,
                "date": kickoff.strftime("%Y-%m-%d"),
                "result": {"home_goals": i % 4, "away_goals": (i * 3) % 3},
            }
        )
    return out


# ---------- o embaralhamento ----------


def test_permutacao_preserva_as_marginais_da_liga() -> None:
    """A climatologia é feita das marginais. Se elas mudassem, o baseline do
    controle negativo deixaria de ser comparável ao dos dados reais e o teste
    não provaria nada."""
    obs = _obs()
    perm = pt._permute(obs, seed=1)
    original = Counter((o["result"]["home_goals"], o["result"]["away_goals"]) for o in obs)
    embaralhado = Counter((o["result"]["home_goals"], o["result"]["away_goals"]) for o in perm)
    assert original == embaralhado


def test_permutacao_mantem_o_placar_inteiro_junto() -> None:
    """`result` viaja inteiro: embaralhar gols separadamente mataria a
    correlação entre placares e mudaria a distribuição conjunta."""
    obs = _obs()
    perm = pt._permute(obs, seed=2)
    pares_orig = {id(o["result"]) for o in obs}
    assert all(id(o["result"]) in pares_orig for o in perm)


def test_permutacao_desassocia_time_de_desfecho() -> None:
    obs = _obs()
    perm = pt._permute(obs, seed=3)
    assert [o["home"] for o in obs] == [o["home"] for o in perm], "a ordem das partidas não muda"
    assert [o["result"] for o in obs] != [o["result"] for o in perm], "os desfechos têm que se mover"


def test_permutacao_nao_altera_a_ordem_temporal() -> None:
    """Embaralhar kickoff quebraria o walk-forward em vez de testá-lo."""
    obs = _obs()
    perm = pt._permute(obs, seed=4)
    assert [o["kickoff"] for o in obs] == [o["kickoff"] for o in perm]


def test_permutacao_e_deterministica_por_seed() -> None:
    obs = _obs()
    assert pt._permute(obs, 7) == pt._permute(obs, 7)
    assert pt._permute(obs, 7) != pt._permute(obs, 8)


def test_permutacao_nao_muta_a_entrada() -> None:
    obs = _obs()
    antes = [o["result"] for o in obs]
    pt._permute(obs, seed=9)
    assert [o["result"] for o in obs] == antes


# ---------- leitura do skill ----------


def _rows(probs_por_jogo, desfechos) -> list[dict]:
    return [
        {"date": str(i), "p_loss": p[0], "p_draw": p[1], "p_win": p[2], "actual_1x2": y}
        for i, (p, y) in enumerate(zip(probs_por_jogo, desfechos))
    ]


def test_modelo_igual_a_climatologia_nao_bate_a_climatologia() -> None:
    """Caso-limite: reproduzir a climatologia prequential não é skill."""
    desfechos = [2] * 120 + [1] * 60 + [0] * 120
    seed_rows = _rows([[1 / 3, 1 / 3, 1 / 3]] * 300, desfechos)
    baseline = pt._climatology_probs(seed_rows)
    out = pt._skill_vs_climatology(_rows(baseline, desfechos))
    assert out["skill_score"] == pytest.approx(0.0, abs=1e-9)
    assert out["beats_climatology"] is False


def test_modelo_com_sinal_real_bate_a_climatologia() -> None:
    """Sem isso o teste passaria por ser cego, não por ser correto."""
    desfechos = [2 if i % 2 else 0 for i in range(300)]
    probs = [[0.05, 0.05, 0.90] if y == 2 else [0.90, 0.05, 0.05] for y in desfechos]
    out = pt._skill_vs_climatology(_rows(probs, desfechos))
    assert out["skill_score"] > 0.5
    assert out["beats_climatology"] is True


# ---------- holdout selado ----------


@pytest.mark.parametrize("period", ["2021-01-01,2025-06-30", "2021-01-01,2026-12-31", "2021-01-01,"])
def test_recusa_periodo_que_alcanca_o_holdout(period, monkeypatch) -> None:
    """Um controle negativo consome o holdout tanto quanto um experimento."""
    monkeypatch.setattr(sys, "argv", ["permutation_test", "--period", period])
    assert pt.main() == 1


def test_recusa_zero_permutacoes(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["permutation_test", "--permutations", "0"])
    with pytest.raises(SystemExit):
        pt.main()
