"""PRÉ-REGISTRO da pilha de serving vs. climatologia.

O valor deste script é ser CEGO: ele congela um desenho e não olha dados. Um
pré-registro que mede é pré-registro só no nome. Estes testes protegem essa
propriedade, o gate declarado e o schema do registro.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
from datetime import UTC, datetime

import pytest
from predictor_core.contracts.registry import TrialRegistry, validate_trials

from brasileirao_scripts import prereg_serving_vs_climatologia as prereg

# ---------- o script não pode olhar dados ----------


def test_nao_importa_nada_que_leia_o_banco() -> None:
    """`_load_observations` e `_run_walkforward` são as portas para os dados. Se
    aparecerem aqui, alguém transformou o pré-registro em medição."""
    fonte = pathlib.Path(prereg.__file__).read_text(encoding="utf-8")
    corpo = fonte.split('"""', 2)[2]  # fora do docstring, que CITA os números
    for proibido in ("_load_observations", "_run_walkforward", "sqlite3", "matches.db"):
        assert proibido not in corpo, f"o pré-registro não pode tocar em {proibido}"


def test_dry_run_nao_grava_no_registro(monkeypatch, capsys) -> None:
    alvo = pathlib.Path(tempfile.mkdtemp()) / "trials.json"
    monkeypatch.setattr(prereg, "TRIALS", alvo)
    assert prereg.main(["--dry-run"]) == 0
    assert not alvo.exists(), "--dry-run gravou no registro"
    saida = json.loads(capsys.readouterr().out)
    assert saida["trial"] == prereg.TRIAL_NAME


# ---------- o desenho congelado ----------


def test_params_declaram_o_motor_e_o_ensemble_desligado() -> None:
    """A hipótese é sobre a pilha SEM o ensemble — a h12 mostrou que ligado ele
    piora tudo. Se este campo virar True, é outra hipótese."""
    p = prereg._params("2026-08-22")
    assert p["engine"] == "serving"
    assert p["ensemble_xg_enabled"] is False
    assert p["primary_metric"] == "rps"
    assert p["baseline"] == "climatology"


def test_ponto_unico_de_avaliacao_sem_olhadas_intermediarias() -> None:
    """Olhar e parar quando dá significativo infla falso-positivo. O desenho
    declara um n mínimo e proíbe avaliação intermediária."""
    p = prereg._params("2026-08-22")
    assert p["avaliacoes_intermediarias"] is False
    assert p["min_n_avaliacao"] == prereg.MIN_N_AVALIACAO
    assert prereg.MIN_N_AVALIACAO > prereg.N_PODER_MARGINAL, (
        "o ponto de avaliação tem que ser MAIOR que o n de poder marginal — "
        "avaliar em ~50% de poder produz inconclusiva não-informativa"
    )


def test_notes_declaram_o_gate_antes_dos_dados() -> None:
    n = prereg._notes("2026-08-22")
    assert "GATE" in n
    assert "inteiramente abaixo de zero" in n
    assert "controle negativo" in n
    assert "NÃO AUTORIZA CAPITAL" in n
    assert "Resultado ainda não medido" in n


def test_notes_registram_que_a_amostra_de_2021_2024_ja_tinha_sido_vista() -> None:
    """A honestidade do registro depende de dizer POR QUE é prospectivo."""
    n = prereg._notes("2026-08-22")
    assert "NÃO é confirmatório" in n or "NÃO é confirmatório" in n.replace(" ", " ")
    assert "SELADO" in n and "Regra 7" in n


# ---------- schema do registro ----------


def test_registro_conforma_ao_schema_do_core(monkeypatch) -> None:
    """Coorte prospectiva tem fim ABERTO — o schema aceita um dos lados None,
    e é assim que o registro sabe que ela ainda está acumulando."""
    alvo = pathlib.Path(tempfile.mkdtemp()) / "trials.json"
    alvo.write_text("[]", encoding="utf-8")
    # O registro do core EXIGE um atestado de poder válido em disco, ao lado do
    # trials.json — não basta o fingerprint. Reusa o atestado real do repo
    # (metric='rps', mesmo pipeline) em vez de fabricar um: fabricar aqui seria
    # testar contra a invenção, que foi o erro da auditoria do `actual_ou25`.
    real = pathlib.Path(prereg.ROOT) / "data" / "trials.harness_attestation.json"
    atestado = json.loads(real.read_text(encoding="utf-8"))
    if datetime.fromisoformat(atestado["expires_at"]) <= datetime.now(UTC):
        pytest.skip("atestado do repo expirado — renove com attest_rps_power()")
    (alvo.parent / "trials.harness_attestation.json").write_text(
        json.dumps(atestado, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(prereg, "TRIALS", alvo)
    monkeypatch.setattr(prereg, "attest_rps_power", lambda: atestado)

    assert prereg.main([]) == 0

    trials = TrialRegistry(alvo).load()
    assert validate_trials(trials) == []
    t = next(x for x in trials if x["name"] == prereg.TRIAL_NAME)
    assert t["status"] == "pre-registrada"
    assert t["metric"] == "rps"
    assert t["test_period"][1] is None, "coorte prospectiva precisa de fim aberto"
    assert t["sharpe"] is None


def test_nome_da_trial_sem_espacos() -> None:
    """`name` é identidade no schema do core: str não-vazia, sem espaços."""
    assert prereg.TRIAL_NAME and " " not in prereg.TRIAL_NAME


@pytest.mark.parametrize("campo", ["rps", "delta", "IC95", "0.213339"])
def test_params_nao_carregam_resultado(campo: str) -> None:
    """Nenhum número medido pode entrar em `params` — params é a identidade do
    desenho. O resultado de 2021-2024 vive nas notas como MOTIVAÇÃO, declarado
    como já-visto, nunca como achado desta trial."""
    if campo == "rps":
        return  # 'rps' é legítimo em params (primary_metric)
    assert campo not in json.dumps(prereg._params("2026-08-22"), ensure_ascii=False)
