"""Regressão W5 (auditoria 2026-07-09): o consenso do odds_shop incluía casas
com last_update congelado — o melhor preço via max() podia ser um feed morto
que o operador não consegue executar. O filtro de frescor (max_stale_s)
descarta essas casas; None desliga (modo --from-file, onde o snapshot inteiro
é velho por definição).
"""

from datetime import UTC, datetime, timedelta

from brasileirao_scripts import odds_shop


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _event(now):
    fresh = _iso(now - timedelta(minutes=2))
    stale = _iso(now - timedelta(hours=3))

    def mk(over, under):
        return [
            {
                "key": "totals",
                "outcomes": [
                    {"name": "Over", "price": over, "point": 2.5},
                    {"name": "Under", "price": under, "point": 2.5},
                ],
            }
        ]

    return {
        "bookmakers": [
            {"key": "viva", "title": "CasaViva", "last_update": fresh, "markets": mk(1.90, 1.90)},
            # feed morto com o "melhor" preço do under — a isca do W5
            {"key": "morta", "title": "CasaMorta", "last_update": stale, "markets": mk(1.80, 2.50)},
            {"key": "semdata", "title": "CasaSemData", "markets": mk(1.95, 1.85)},
        ]
    }


def test_filtro_descarta_feed_morto():
    now = datetime.now(UTC)
    c = odds_shop.consensus(_event(now), "totals", point=2.5, max_stale_s=15 * 60)
    # melhor under vem da casa viva (1.90), não da morta (2.50)
    assert c["Under"]["best"][0] == 1.90
    assert c["Under"]["best"][1] == "CasaViva"
    # Horário desconhecido não confirma frescor; somente a casa viva entra.
    assert c["Under"]["n_books"] == 1


def test_none_desliga_o_filtro():
    now = datetime.now(UTC)
    c = odds_shop.consensus(_event(now), "totals", point=2.5, max_stale_s=None)
    assert c["Under"]["best"] == (2.50, "CasaMorta")
    assert c["Under"]["n_books"] == 3


def test_last_update_ilegivel_nao_trava():
    ev = _event(datetime.now(UTC))
    ev["bookmakers"][0]["last_update"] = "ontem de manhã"
    c = odds_shop.consensus(ev, "totals", point=2.5, max_stale_s=15 * 60)
    assert c == {}  # ilegível, ausente e antigo não confirmam preço atual
