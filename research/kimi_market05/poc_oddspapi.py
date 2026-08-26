"""poc_oddspapi.py — PoC Gate A1 (MARKET-05): valida fonte de odds em <5 min.

Uso:
    export ODDSPAPI_KEY="sua_chave"
    python poc_oddspapi.py

CRITÉRIO DE PASS (declarado ex ante):
  - Pinnacle presente nas respostas
  - >= 4 casas BR presentes no MESMO evento do Brasileirão
  - >= 1 fixture BR com odds nos próximos 7 dias
Se PASS: prosseguir para implementação do coletor (spec MARKET_05_A1).
Se FAIL: documentar e reavaliar fonte.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

API_KEY = os.environ.get("ODDSPAPI_KEY", "")
BASE = "https://api.oddspapi.io/v4"

REFERENCE = "pinnacle"
BR_BOOKS = ["betano.bet.br", "estrelabet", "sportingbet.bet.br",
            "superbet.bet.br", "kto", "pixbet", "blaze.bet.br", "brazino777.bet.br"]


def get(path, **params):
    params["apiKey"] = API_KEY
    r = requests.get(f"{BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    if not API_KEY:
        sys.exit("ERRO: defina ODDSPAPI_KEY no ambiente.")

    print("=" * 60)
    print("PoC MARKET-05 / Gate A1 — fonte de odds")
    print("=" * 60)

    # 1. Catálogo de casas: Pinnacle + BR presentes?
    books = get("bookmakers")
    slugs = {b["slug"] for b in books}
    print(f"\n[1] Catálogo total: {len(slugs)} casas")
    print(f"    Pinnacle: {'OK' if REFERENCE in slugs else 'FALTA'}")
    br_ok = [s for s in BR_BOOKS if s in slugs]
    print(f"    Casas BR encontradas ({len(br_ok)}/8): {br_ok}")

    # 2. Fixtures BR com odds nos próximos 7 dias
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plus7 = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
    fixtures = get("fixtures", sportId=10, **{"from": today, "to": plus7})
    br_fixtures = [f for f in fixtures
                   if "brazil" in str(f.get("categorySlug", "")).lower()
                   and f.get("hasOdds")]
    print(f"\n[2] Fixtures BR com odds (7 dias): {len(br_fixtures)}")
    for f in br_fixtures[:5]:
        print(f"    {f.get('participant1Name')} x {f.get('participant2Name')}")

    if not br_fixtures:
        print("\nVEREDITO: FAIL — sem fixtures BR com odds na janela.")
        sys.exit(1)

    # 3. Um evento: Pinnacle + quantas casas BR no MESMO jogo?
    fid = br_fixtures[0]["fixtureId"]
    data = get("odds", fixtureId=fid)
    bk = data.get("bookmakerOdds", {})
    present_br = [s for s in BR_BOOKS if s in bk]
    has_pin = REFERENCE in bk
    print(f"\n[3] Evento: {br_fixtures[0].get('participant1Name')} x "
          f"{br_fixtures[0].get('participant2Name')}")
    print(f"    Pinnacle presente: {has_pin}")
    print(f"    Casas BR no mesmo evento ({len(present_br)}): {present_br}")

    # Amostra 1X2 (market 101: home=101, draw=102, away=103)
    for slug in ([REFERENCE] if has_pin else []) + present_br[:3]:
        m = bk[slug].get("markets", {}).get("101", {}).get("outcomes", {})
        def price(o): return m.get(o, {}).get("players", {}).get("0", {}).get("price", "-")
        print(f"    {slug:<22} H:{price('101')}  D:{price('102')}  A:{price('103')}")

    # 4. Veredito
    passed = has_pin and len(present_br) >= 4 and len(br_fixtures) >= 1
    print("\n" + "=" * 60)
    print(f"VEREDITO PoC: {'PASS' if passed else 'FAIL'}")
    print("=" * 60)
    if passed:
        print("Próximo passo: Codex implementa o coletor conforme")
        print("docs/experiments/MARKET_05_A1_COLLECTOR_SPEC.md com")
        print("source_id='oddspapi_v4'. Iniciar shadow mode HOJE para o")
        print("relógio de 7 dias do Gate A1 começar a contar.")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
