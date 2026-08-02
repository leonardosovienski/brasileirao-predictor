"""Testes do domínio Brasileirão (PASSO 6.2 do bootstrap).

Cobrem o que mudou na adaptação Copa → clubes: config de identidade,
k_factor da liga, modelo com dois clubes, settle com resultado REAL da
Série A 2024 (Bahia 0x2 Flamengo, coletado do Sofascore em 2026-07-10),
espelho sofascore→matches e o sport key do odds_shop.
Tudo em :memory:/tmp_path — sem disco compartilhado, sem rede.
"""

import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import db, model, predict, ratings  # noqa: E402
from src.settle import record_result  # noqa: E402

_CFG_ELO = {
    "initial_rating": 1500,
    "home_advantage": 100,
    "k_factors": {"Brasileirão Série A": 30, "default": 30, "Friendly": 20},
}


def test_config_identidade_do_dominio():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert "Brasileirão" in cfg["league"]
    assert cfg["tournament_name"] == "Brasileirão Série A"
    comps = cfg["sofascore"]["competitions"]
    assert comps and all(c["ut_id"] == 325 for c in comps)
    assert {str(c["season"]) for c in comps} >= {"2024", "2025"}


def test_k_factor_brasileirao():
    assert ratings.k_factor("Brasileirão Série A", _CFG_ELO["k_factors"]) == 30
    # clube desconhecido do dict cai no default, não em chave da Copa
    assert ratings.k_factor("Copa do Brasil", _CFG_ELO["k_factors"]) == 30


def test_modelo_com_dois_clubes():
    """Elo + MLE + previsão com nomes de CLUBE — o motor não pode depender de
    nada específico de seleções. Round-robin sintético determinístico."""
    clubes = ["Flamengo", "Palmeiras", "São Paulo", "Grêmio"]
    ms = []
    day = 0
    for rodada in range(30):
        for i, h in enumerate(clubes):
            for j, a in enumerate(clubes):
                if i >= j:
                    continue
                day += 1
                # placar determinístico: força decresce com o índice
                hs = max(0, 2 - i + (rodada + i + j) % 2)
                as_ = max(0, 1 - j + (rodada + i) % 2)
                ms.append(
                    (
                        f"2024-{1 + day // 28:02d}-{1 + day % 28:02d}",
                        h,
                        a,
                        hs,
                        as_,
                        "Brasileirão Série A",
                        0,
                    )
                )
    ms.sort(key=lambda m: m[0])
    elo, history = ratings.compute_ratings(ms, _CFG_ELO)
    assert set(clubes) <= set(elo)
    params = model.fit_goal_model(history)
    r = model.predict_match(elo["Flamengo"], elo["Palmeiras"], params, home_adv=100, max_goals=10)
    total = r["p_win"] + r["p_draw"] + r["p_loss"]
    assert 0.99 <= total <= 1.01
    assert r["lambda_a"] > 0 and r["lambda_b"] > 0
    assert 0.0 < r["over"][2.5] < 1.0


def test_settle_resultado_real_brasileirao(tmp_path):
    """Bahia 0x2 Flamengo (Série A 2024, sofascore) — o ciclo palpite→resultado
    tem que fechar com nomes de clube (sem alias de seleção no meio)."""
    pred = {
        "home": "Bahia",
        "away": "Flamengo",
        "p_home": 0.30,
        "p_draw": 0.28,
        "p_away": 0.42,
        "lambda_home": 1.1,
        "lambda_away": 1.5,
        "over": {"1.5": 0.70, "2.5": 0.45, "3.5": 0.22},
        "btts_yes": 0.52,
        "btts_no": 0.48,
        "top_scores": [[[0, 2], 0.08]],
        "logged_at": "2024-06-20T00:00:00+00:00",
    }
    pred_p = tmp_path / "predictions.jsonl"
    pred_p.write_text(json.dumps(pred) + "\n", encoding="utf-8")
    rec = record_result("Bahia", "Flamengo", 0, 2, path=tmp_path / "results.jsonl", pred_path=pred_p)
    assert rec["prediction"] is not None
    assert rec["grades"]["winner"]["pick"] == "Flamengo"
    assert rec["grades"]["winner"]["correct"] is True
    assert rec["grades"]["over_under_2.5"]["actual"] == "Under"
    assert rec["grades"]["exact_score"]["correct"] is True


def test_espelho_sofascore_para_matches():
    """scripts/sync_matches_from_sofascore: upsert idempotente, tournament do
    config, neutral=0 (liga tem mando sempre)."""
    spec = importlib.util.spec_from_file_location("sync_matches", ROOT / "scripts" / "sync_matches_from_sofascore.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    conn = db.connect(":memory:")
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, "
        "home_team, away_team, home_score, away_score) VALUES "
        "(1, 'Brasileirão Série A 2024', '2024', '2024-04-13', "
        "'Criciúma', 'Corinthians', 2, 4)"
    )
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, "
        "home_team, away_team) VALUES "
        "(2, 'Brasileirão Série A 2026', '2026', '2026-07-20', "
        "'Flamengo', 'Palmeiras')"
    )  # fixture futuro, sem placar
    conn.commit()

    played, fixtures = mod.sync(conn, "Brasileirão Série A")
    assert (played, fixtures) == (1, 1)
    row = conn.execute("SELECT tournament, neutral, home_score FROM matches WHERE home_team='Criciúma'").fetchone()
    assert row == ("Brasileirão Série A", 0, 2)
    # idempotente: rodar de novo não duplica
    played2, fixtures2 = mod.sync(conn, "Brasileirão Série A")
    assert (played2, fixtures2) == (1, 1)


def test_odds_shop_sport_key_do_config():
    spec = importlib.util.spec_from_file_location("odds_shop_dom", ROOT / "scripts" / "odds_shop.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.SPORT == "soccer_brazil_campeonato"


def test_proximos_fixtures_excluem_eventos_passados_sem_placar():
    """Um fixture antigo sem score precisa continuar conciliável, mas nunca
    pode aparecer como o próximo jogo no serving."""
    conn = db.connect(":memory:")
    conn.executemany(
        "INSERT INTO matches (date, home_team, away_team, tournament, neutral) VALUES (?, ?, ?, ?, 0)",
        [
            ("2024-04-17", "Stale FC", "Old FC", "Brasileirão Série A"),
            ("2026-07-16", "Hoje FC", "Visitante FC", "Brasileirão Série A"),
            ("2026-07-17", "Amanhã FC", "Outro FC", "Brasileirão Série A"),
        ],
    )
    rows = predict.upcoming_fixtures(conn, 10, as_of="2026-07-16")
    assert [(row[0], row[1]) for row in rows] == [
        ("2026-07-16", "Hoje FC"),
        ("2026-07-17", "Amanhã FC"),
    ]


def test_ht_fraction_forward_only():
    """H2: a fração de gols do 1T só pode ver jogos ANTERIORES ao corte."""
    spec = importlib.util.spec_from_file_location("wf", ROOT / "scripts" / "backtest_walkforward.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # 60 jogos antes do corte (1 gol no 1T de 2 no total → frac 0.5),
    # 40 depois com fração diferente que NÃO pode contaminar
    rows = [("2024-01-01", 1, 1, 1, 0)] * 60 + [("2025-01-01", 3, 3, 0, 0)] * 40
    frac, n = mod._ht_fraction(rows, "2024-12-31")
    assert n == 60 and abs(frac - 0.5) < 1e-9
    # menos de 50 jogos → None (mesmo piso do serving)
    frac2, n2 = mod._ht_fraction(rows[:30], "2024-12-31")
    assert frac2 is None and n2 == 30
