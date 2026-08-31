"""PoC read-only de coocorrência Pinnacle x casas BR na OddsPapi.

Faz exatamente duas chamadas: fixtures da Série A e odds do próximo fixture.
A chave fica somente no ambiente e nunca é impressa ou persistida.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests

BASE_URL = "https://api.oddspapi.io/v4"
BRASILEIRAO_SERIE_A_ID = 325
TIMEOUT_SECONDS = 30
TARGET_BR_BOOKMAKERS = {
    "betano.bet.br": ("betano",),
    "estrelabet": ("estrelabet", "estrela"),
    "sportingbet.bet.br": ("sportingbet",),
    "superbet.bet.br": ("superbet",),
    "kto": ("kto",),
    "pixbet": ("pixbet",),
}


def get_json(path: str, api_key: str, **params: object) -> Any:
    """Executa GET sem incluir a chave em mensagens de erro."""
    response = requests.get(
        f"{BASE_URL}/{path}",
        params={**params, "apiKey": api_key},
        timeout=TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        detail = response.text[:300].replace(api_key, "[REDACTED]")
        raise RuntimeError(f"OddsPapi respondeu HTTP {response.status_code}: {detail}")
    try:
        return response.json()
    except requests.JSONDecodeError as exc:
        raise RuntimeError("OddsPapi retornou resposta não-JSON") from exc


def bookmaker_match(keys: list[str], aliases: tuple[str, ...]) -> str | None:
    for key in keys:
        normalized = key.casefold().replace("-", "").replace("_", "").replace(".", "")
        if any(alias.replace(".", "") in normalized for alias in aliases):
            return key
    return None


def summarize_1x2(bookmaker: dict[str, Any]) -> dict[str, float] | None:
    """Resume o mercado canônico v4 101 (1X2)."""
    market = bookmaker.get("markets", {}).get("101")
    if not isinstance(market, dict):
        return None
    prices: dict[str, float] = {}
    outcome_names = {"101": "home", "102": "draw", "103": "away"}
    for outcome_id, outcome in market.get("outcomes", {}).items():
        for player in outcome.get("players", {}).values():
            price = player.get("price")
            if outcome_id in outcome_names and isinstance(price, int | float):
                prices[outcome_names[outcome_id]] = float(price)
    return prices or None


def main() -> int:
    api_key = os.environ.get("ODDSPAPI_KEY", "").strip()
    if not api_key:
        print("ERRO: defina ODDSPAPI_KEY no ambiente.", file=sys.stderr)
        return 2

    try:
        fixtures = get_json(
            "fixtures",
            api_key,
            tournamentId=BRASILEIRAO_SERIE_A_ID,
            statusId=0,
            hasOdds="true",
        )
        if not isinstance(fixtures, list):
            raise RuntimeError("payload de fixtures não é uma lista")
        eligible = [item for item in fixtures if isinstance(item, dict) and item.get("fixtureId")]
        if not eligible:
            raise RuntimeError("nenhum fixture futuro com odds foi encontrado")
        fixture = min(eligible, key=lambda item: str(item.get("startTime", "9999")))
        odds = get_json("odds", api_key, fixtureId=fixture["fixtureId"], oddsFormat="decimal", verbosity=3)
        if not isinstance(odds, dict):
            raise RuntimeError("payload de odds não é um objeto")
    except (requests.RequestException, RuntimeError) as exc:
        print(f"ERRO: {str(exc).replace(api_key, '[REDACTED]')}", file=sys.stderr)
        return 1

    bookmaker_odds = odds.get("bookmakerOdds", {})
    if not isinstance(bookmaker_odds, dict):
        bookmaker_odds = {}
    keys = sorted(str(key) for key in bookmaker_odds)
    matched_br = {
        label: match
        for label, aliases in TARGET_BR_BOOKMAKERS.items()
        if (match := label if label in keys else bookmaker_match(keys, aliases)) is not None
    }
    pinnacle_key = bookmaker_match(keys, ("pinnacle",))
    selected_keys = ([pinnacle_key] if pinnacle_key else []) + list(matched_br.values())
    if pinnacle_key and len(matched_br) >= 4:
        gate = "PASS"
    elif pinnacle_key and matched_br:
        gate = "PASS_PARTIAL"
    else:
        gate = "FAIL"
    result = {
        "source": "oddspapi",
        "requests_used_by_run": 2,
        "fixture": {
            "fixtureId": fixture.get("fixtureId"),
            "startTime": fixture.get("startTime"),
            "home": fixture.get("participant1Name"),
            "away": fixture.get("participant2Name"),
            "statusName": fixture.get("statusName"),
        },
        "bookmakers_total": len(keys),
        "bookmaker_keys": keys,
        "pinnacle": pinnacle_key,
        "target_br_matches": matched_br,
        "target_br_count": len(matched_br),
        "one_x_two": {
            key: summary for key in selected_keys if (summary := summarize_1x2(bookmaker_odds[key])) is not None
        },
        "gate": gate,
        "read_only": True,
        "api_key_logged": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
