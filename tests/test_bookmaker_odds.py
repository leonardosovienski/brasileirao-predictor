"""Identidade entre The Odds API e Sofascore, e fechamento por bookmaker.

Parear a partida errada contamina odd, resultado e CLV de uma vez — por isso
todo caminho de ambiguidade tem teste, e todos exigem falha fechada.
"""

from brasileirao_predictor.data.bookmaker_odds import (
    closing_quote,
    fold,
    load_snapshots,
    match_fixture,
    persist_snapshots,
    resolve_team,
)

CONHECIDOS = [
    "Grêmio",
    "Fluminense",
    "São Paulo",
    "Atlético Mineiro",
    "Atlético Goianiense",
    "Red Bull Bragantino",
    "Vitória",
    "Athletico",
]


def _fixture(event_id, home, away, kickoff):
    return {"event_id": event_id, "home_team": home, "away_team": away, "kickoff_at": kickoff}


def test_fold_remove_acento_e_caixa():
    assert fold("São Paulo") == fold("Sao Paulo") == "sao paulo"
    assert fold("  Vitória ") == "vitoria"


def test_fold_nao_colide_times_distintos():
    assert fold("Atlético Mineiro") != fold("Atlético Goianiense")


def test_nome_exato():
    assert resolve_team("Grêmio", CONHECIDOS) == ("Grêmio", "EXACT")


def test_acento_ausente_resolve_quando_unico():
    assert resolve_team("Sao Paulo", CONHECIDOS) == ("São Paulo", "RULE_BASED")
    assert resolve_team("Atletico Mineiro", CONHECIDOS) == ("Atlético Mineiro", "RULE_BASED")
    assert resolve_team("Vitoria", CONHECIDOS) == ("Vitória", "RULE_BASED")


def test_alias_explicito_para_nome_comercial_diferente():
    assert resolve_team("Bragantino-SP", CONHECIDOS) == ("Red Bull Bragantino", "RULE_BASED")
    assert resolve_team("Athletico-PR", CONHECIDOS) == ("Athletico", "RULE_BASED")


def test_nome_desconhecido_falha_fechado():
    assert resolve_team("Clube Inexistente", CONHECIDOS) == (None, "REJECTED")


def test_alias_para_time_fora_da_base_falha_fechado():
    assert resolve_team("Bragantino-SP", ["Grêmio"]) == (None, "REJECTED")


def test_ambiguidade_de_dobra_falha_fechado():
    """Sem caixa exata, se dois canônicos dobram para a mesma chave: ninguém."""
    assert resolve_team("UNIAO", ["União", "Uniao"]) == (None, "AMBIGUOUS")


def test_caixa_exata_tem_precedencia_sobre_a_dobra():
    """Havendo o nome idêntico, ele resolve mesmo com um homônimo dobrável."""
    assert resolve_team("Uniao", ["União", "Uniao"]) == ("Uniao", "EXACT")


def test_casa_fixture_com_acento_divergente():
    fx = [_fixture(1, "São Paulo", "Grêmio", "2026-07-26T21:30:00+00:00")]
    row = {
        "home_team": "Sao Paulo",
        "away_team": "Grêmio",
        "kickoff_at": "2026-07-26T21:30:00+00:00",
    }
    achado, status = match_fixture(row, fx)
    assert achado["event_id"] == 1 and status == "RULE_BASED"


def test_kickoff_distante_nao_casa():
    fx = [_fixture(1, "Grêmio", "Fluminense", "2026-07-26T21:30:00+00:00")]
    row = {
        "home_team": "Grêmio",
        "away_team": "Fluminense",
        "kickoff_at": "2026-07-30T21:30:00+00:00",
    }
    assert match_fixture(row, fx) == (None, "sem_fixture")


def test_placeholder_de_meia_noite_da_api_ainda_casa():
    """A The Odds API publica 00:00 UTC enquanto o horário não é confirmado.

    Caso real de 2026-07-25: Botafogo x Grêmio veio 00:00 contra 18:00 do
    Sofascore. O apito gravado no pick é sempre o do Sofascore."""
    fx = [_fixture(9, "Botafogo", "Grêmio", "2026-07-29T18:00:00+00:00")]
    row = {
        "home_team": "Botafogo",
        "away_team": "Grêmio",
        "kickoff_at": "2026-07-29T00:00:00+00:00",
    }
    achado, _ = match_fixture(row, fx)
    assert achado["event_id"] == 9


def test_alias_sem_h_do_athletico():
    assert resolve_team("Atletico Paranaense", CONHECIDOS) == ("Athletico", "RULE_BASED")


def test_mesmo_confronto_duas_vezes_na_janela_e_ambiguo():
    fx = [
        _fixture(1, "Grêmio", "Fluminense", "2026-07-26T18:00:00+00:00"),
        _fixture(2, "Grêmio", "Fluminense", "2026-07-26T22:00:00+00:00"),
    ]
    row = {
        "home_team": "Grêmio",
        "away_team": "Fluminense",
        "kickoff_at": "2026-07-26T20:00:00+00:00",
    }
    assert match_fixture(row, fx) == (None, "fixture_ambiguo")


def test_mando_invertido_nao_casa():
    """Grêmio x Fluminense nao e' Fluminense x Grêmio."""
    fx = [_fixture(1, "Grêmio", "Fluminense", "2026-07-26T21:30:00+00:00")]
    row = {
        "home_team": "Fluminense",
        "away_team": "Grêmio",
        "kickoff_at": "2026-07-26T21:30:00+00:00",
    }
    assert match_fixture(row, fx)[0] is None


def test_persistencia_e_idempotente(tmp_path):
    path = tmp_path / "snaps.jsonl"
    linha = {
        "event_id": 1,
        "selection": "over",
        "odds_captured_at": "2026-07-26T10:00:00+00:00",
        "market": "ou2.5",
        "odd": 1.95,
    }
    assert persist_snapshots(path, [linha]) == 1
    assert persist_snapshots(path, [linha]) == 0  # retry não duplica
    assert len(load_snapshots(path)) == 1


def test_persistencia_nao_colapsa_bookmaker_ou_mercado(tmp_path):
    path = tmp_path / "snaps.jsonl"
    base = {
        "source": "odds",
        "source_event_id": "e",
        "event_id": 1,
        "bookmaker": "a",
        "market": "ou2.5",
        "selection": "over",
        "line": 2.5,
        "odds_captured_at": "2026-07-26T10:00:00+00:00",
        "odd": 1.95,
    }
    assert persist_snapshots(path, [base, {**base, "bookmaker": "b"}]) == 2
    assert persist_snapshots(path, [{**base, "market": "ou1.5_1h", "line": 1.5}]) == 1


def _snap(captured, odd, selection="over"):
    return {
        "event_id": 1,
        "market": "ou2.5",
        "selection": selection,
        "odds_captured_at": captured,
        "odd": odd,
    }


def test_fechamento_pega_a_ultima_antes_do_apito():
    snaps = [
        _snap("2026-07-26T10:00:00+00:00", 1.90),
        _snap("2026-07-26T20:00:00+00:00", 2.05),
        _snap("2026-07-26T15:00:00+00:00", 1.95),
    ]
    achado = closing_quote(snaps, event_id=1, market="ou2.5", selection="over", kickoff_at="2026-07-26T21:30:00+00:00")
    assert achado["odd"] == 2.05


def test_fechamento_ignora_cotacao_pos_apito():
    snaps = [_snap("2026-07-26T22:00:00+00:00", 2.50)]
    assert (
        closing_quote(
            snaps,
            event_id=1,
            market="ou2.5",
            selection="over",
            kickoff_at="2026-07-26T21:30:00+00:00",
        )
        is None
    )


def test_fechamento_ignora_odd_invalida():
    snaps = [_snap("2026-07-26T20:00:00+00:00", 1.0)]
    assert (
        closing_quote(
            snaps,
            event_id=1,
            market="ou2.5",
            selection="over",
            kickoff_at="2026-07-26T21:30:00+00:00",
        )
        is None
    )


def test_fechamento_nao_mistura_selecao():
    snaps = [_snap("2026-07-26T20:00:00+00:00", 2.05, selection="under")]
    assert (
        closing_quote(
            snaps,
            event_id=1,
            market="ou2.5",
            selection="over",
            kickoff_at="2026-07-26T21:30:00+00:00",
        )
        is None
    )
