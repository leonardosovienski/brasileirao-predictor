"""emit_h9_shadow: janela de decisão, Elo vivo x parâmetros congelados,
casamento de fixture, e idempotência via o próprio ledger da H9."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from brasileirao_predictor import db, model
from brasileirao_scripts import emit_h9_shadow as job

KICKOFF = datetime(2027, 3, 1, 19, 0, tzinfo=UTC)
ELO_HOME, ELO_AWAY, HOME_ADV = 1550, 1450, 100.0
PARAMS = (0.2, 0.7, 1e-4, 0.0)


def _p_over(params=PARAMS) -> float:
    return model.predict_match(ELO_HOME, ELO_AWAY, params, HOME_ADV, max_goals=12)["over"][2.5]


def _odd_for_edge(p_over: float, edge: float = 0.05) -> float:
    return round(1.0 / (p_over - edge), 4)


def _trials_json(path: Path, *, a=0.2, b=0.7, alpha=1e-4, rho=0.0, max_goals=12) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "name": job.TRIAL,
                    "params": {"model": {"a": a, "b": b, "alpha": alpha, "rho": rho, "max_goals": max_goals}},
                }
            ]
        ),
        encoding="utf-8",
    )


def _quote(source_event_id="odds-1", bookmaker="williamhill", selection="over", odds=1.90, captured=None) -> dict:
    captured = captured or (KICKOFF - timedelta(minutes=60))
    return {
        "source_event_id": source_event_id,
        "bookmaker": bookmaker,
        "market": "ou2.5",
        "selection": selection,
        "decimal_odds": odds,
        "odds_captured_at": captured.isoformat(timespec="seconds"),
        "retrieved_at": captured.isoformat(timespec="seconds"),
        "home_team": "Casa",
        "away_team": "Fora",
        "kickoff_at": KICKOFF.isoformat(timespec="seconds"),
    }


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    dbpath = tmp_path / "t.db"
    conn = db.connect(str(dbpath))
    db.save_elo(conn, [("Casa", ELO_HOME), ("Fora", ELO_AWAY)])
    db.save_params(
        conn,
        *PARAMS,
        0,
        "test-config",
        (KICKOFF - timedelta(hours=7)).isoformat(timespec="seconds"),
    )
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, kickoff_at) "
        "VALUES (1, 'T', '2027', ?, 'Casa', 'Fora', ?)",
        (KICKOFF.date().isoformat(), KICKOFF.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()

    trials_path = tmp_path / "trials.json"
    _trials_json(trials_path)
    stability_path = tmp_path / "stability.jsonl"
    stability_path.write_text("", encoding="utf-8")
    market_obs_path = tmp_path / "market_observations.jsonl"
    ledger_path = tmp_path / "h9.jsonl"
    attempts_path = tmp_path / "h9_emission_attempts.jsonl"

    monkeypatch.setattr(job, "approved_bookmaker", lambda stability_path=None: "williamhill")
    monkeypatch.setattr(job, "load_config", lambda: {"database": str(dbpath), "elo": {"home_advantage": HOME_ADV}})

    return {
        "db_path": dbpath,
        "trials_path": trials_path,
        "stability_path": stability_path,
        "market_obs_path": market_obs_path,
        "ledger_path": ledger_path,
        "attempts_path": attempts_path,
    }


def _write_quotes(path: Path, quotes: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(q) for q in quotes) + "\n", encoding="utf-8")


def _run(ambiente, **overrides):
    kwargs = dict(
        trials_path=ambiente["trials_path"],
        stability_path=ambiente["stability_path"],
        market_obs_path=ambiente["market_obs_path"],
        ledger_path=ambiente["ledger_path"],
        attempts_path=ambiente["attempts_path"],
        db_path=ambiente["db_path"],
    )
    kwargs.update(overrides)
    return job.run(**kwargs)


def test_emits_pick_when_fixture_is_in_decision_window(ambiente):
    odd = _odd_for_edge(_p_over())
    _write_quotes(ambiente["market_obs_path"], [_quote(selection="over", odds=odd)])
    outcomes = _run(ambiente, now=KICKOFF - timedelta(minutes=60))
    assert len(outcomes) == 1
    assert outcomes[0]["status"] == "EMITTED"
    assert outcomes[0]["home"] == "Casa" and outcomes[0]["away"] == "Fora"
    ledger_rows = [json.loads(line) for line in ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()]
    assert len(ledger_rows) == 1
    assert ledger_rows[0]["bookmaker"] == "williamhill"
    assert ledger_rows[0]["capital_enabled"] is False
    assert ledger_rows[0]["elo_policy"] == "current_elo"
    assert len(ledger_rows[0]["policy_fingerprint"]) == 16


def test_ignores_fixture_outside_decision_window(ambiente):
    odd = _odd_for_edge(_p_over())
    _write_quotes(
        ambiente["market_obs_path"], [_quote(selection="over", odds=odd, captured=KICKOFF - timedelta(hours=6))]
    )
    outcomes = _run(ambiente, now=KICKOFF - timedelta(hours=6))  # bem antes da janela H-1.5
    assert outcomes == []
    assert not ambiente["ledger_path"].exists()


def test_fixture_in_window_without_market_observation_is_audited(ambiente):
    outcomes = _run(ambiente, now=KICKOFF - timedelta(minutes=60))
    assert outcomes[0]["status"] == "NO_MARKET_OBSERVATION"
    assert _attempts_rows(ambiente)[0]["status"] == "NO_MARKET_OBSERVATION"


def test_missing_elo_team_is_audited(ambiente):
    conn = db.connect(str(ambiente["db_path"]))
    conn.execute("DELETE FROM current_elo WHERE team='Fora'")
    conn.commit()
    conn.close()
    _write_quotes(ambiente["market_obs_path"], [_quote()])

    outcomes = _run(ambiente, now=KICKOFF - timedelta(minutes=60))
    assert outcomes[0]["status"] == "MISSING_ELO_TEAM"
    assert _attempts_rows(ambiente)[0]["missing_elo_teams"] == ["Fora"]


def test_stale_model_cache_fails_before_emission(ambiente):
    conn = db.connect(str(ambiente["db_path"]))
    db.save_params(conn, *PARAMS, 0, "test-config", (KICKOFF - timedelta(days=1)).isoformat())
    conn.commit()
    conn.close()

    with pytest.raises(RuntimeError, match="cache de modelo stale"):
        _run(ambiente, now=KICKOFF - timedelta(minutes=60))


def test_second_run_in_window_is_idempotent(ambiente):
    odd = _odd_for_edge(_p_over())
    _write_quotes(ambiente["market_obs_path"], [_quote(selection="over", odds=odd)])
    now = KICKOFF - timedelta(minutes=60)
    first = _run(ambiente, now=now)
    second = _run(ambiente, now=now)
    assert first[0]["status"] == "EMITTED"
    assert second[0]["status"] == "ALREADY_EMITTED"
    ledger_rows = [json.loads(line) for line in ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()]
    assert len(ledger_rows) == 1  # nao duplicou


def test_uses_frozen_model_params_not_arbitrary_values(ambiente):
    # a/b diferentes do default do fixture -> se o job usasse outro valor (ex.:
    # hardcoded ou recalibrado na hora), a probabilidade emitida divergiria da
    # calculada aqui com os MESMOS params congelados que o job deveria ler.
    alt_params = (0.3, 0.5, 1e-4, 0.0)
    _trials_json(ambiente["trials_path"], a=0.3, b=0.5, alpha=1e-4, rho=0.0, max_goals=12)
    expected_p_over = _p_over(alt_params)
    odd = _odd_for_edge(expected_p_over)
    _write_quotes(ambiente["market_obs_path"], [_quote(selection="over", odds=odd)])

    outcomes = _run(ambiente, now=KICKOFF - timedelta(minutes=60))
    assert outcomes[0]["status"] == "EMITTED"
    ledger_rows = [json.loads(line) for line in ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()]
    assert ledger_rows[0]["model_probability"] == pytest.approx(expected_p_over)


def test_no_stable_bookmaker_blocks_emission(ambiente, monkeypatch):
    monkeypatch.setattr(job, "approved_bookmaker", lambda stability_path=None: None)
    odd = _odd_for_edge(_p_over())
    _write_quotes(ambiente["market_obs_path"], [_quote(selection="over", odds=odd)])
    outcomes = _run(ambiente, now=KICKOFF - timedelta(minutes=60))
    assert len(outcomes) == 1
    assert outcomes[0]["status"] == "BLOCKED_NO_STABLE_BOOKMAKER"


def test_wrong_bookmaker_quote_is_not_matched_to_a_different_approved_book(ambiente):
    # cotacao existe, mas de uma casa diferente da aprovada -> emit() nao acha
    # cotacao executavel do book aprovado, mesmo com o jogo na janela certa.
    odd = _odd_for_edge(_p_over())
    _write_quotes(ambiente["market_obs_path"], [_quote(selection="over", odds=odd, bookmaker="outrobook")])
    outcomes = _run(ambiente, now=KICKOFF - timedelta(minutes=60))
    assert len(outcomes) == 1
    assert outcomes[0]["status"] == "NO_EXECUTABLE_QUOTE"


def _attempts_rows(ambiente) -> list[dict]:
    path = ambiente["attempts_path"]
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_audit_trail_records_blocked_evaluations_not_just_emitted(ambiente, monkeypatch):
    monkeypatch.setattr(job, "approved_bookmaker", lambda stability_path=None: None)
    odd = _odd_for_edge(_p_over())
    _write_quotes(ambiente["market_obs_path"], [_quote(selection="over", odds=odd)])
    _run(ambiente, now=KICKOFF - timedelta(minutes=60))
    rows = _attempts_rows(ambiente)
    assert len(rows) == 1
    assert rows[0]["status"] == "BLOCKED_NO_STABLE_BOOKMAKER"
    assert "executed_odds" not in rows[0]


def test_audit_trail_computes_slippage_against_best_available_book(ambiente):
    odd = _odd_for_edge(_p_over())
    # aprovada (williamhill) tem a odd "odd"; outra casa nao aprovada tem uma
    # melhor pra MESMA selecao -> slippage deve capturar essa diferenca.
    better_odd = round(odd + 0.15, 4)
    _write_quotes(
        ambiente["market_obs_path"],
        [
            _quote(selection="over", odds=odd, bookmaker="williamhill"),
            _quote(selection="over", odds=better_odd, bookmaker="pinnacle"),
        ],
    )
    outcomes = _run(ambiente, now=KICKOFF - timedelta(minutes=60))
    assert outcomes[0]["status"] == "EMITTED"
    rows = _attempts_rows(ambiente)
    assert len(rows) == 1
    row = rows[0]
    assert row["executed_odds"] == pytest.approx(odd)
    assert row["best_available_bookmaker"] == "pinnacle"
    assert row["best_available_odds"] == pytest.approx(better_odd)
    assert row["slippage_vs_best"] == pytest.approx(odd - better_odd)
    assert row["slippage_vs_best"] < 0  # aceitamos pior preco que o disponivel no mercado


def test_audit_trail_has_zero_slippage_when_only_the_approved_book_quoted(ambiente):
    # unica cotacao existente = a do proprio book aprovado -> "melhor preco
    # disponivel" e' o preco que ja foi aceito, slippage exatamente zero.
    odd = _odd_for_edge(_p_over())
    _write_quotes(ambiente["market_obs_path"], [_quote(selection="over", odds=odd, bookmaker="williamhill")])
    outcomes = _run(ambiente, now=KICKOFF - timedelta(minutes=60))
    assert outcomes[0]["status"] == "EMITTED"
    row = _attempts_rows(ambiente)[0]
    assert row["executed_odds"] == pytest.approx(odd)
    assert row["best_available_bookmaker"] == "williamhill"
    assert row["slippage_vs_best"] == pytest.approx(0.0)
