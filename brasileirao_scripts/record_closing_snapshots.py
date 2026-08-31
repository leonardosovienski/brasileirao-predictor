"""Registra cotações do bookmaker perto do apito — SEM emitir pick.

Por que existe: a captura de picks roda 13:00 e 02:00 UTC, mas os apitos do
Brasileirão são 19:00/21:30/22:30 UTC. O último snapshot antes do jogo ficava
6h a 9h30 velho, e "fechamento" com essa defasagem não é fechamento: a maior
parte do movimento de linha acontece nas horas finais. O gate de CLV
(`h7-clv-prospectivo-pinnacle-2026`) mede contra o fechamento — medir contra
linha de meio da tarde produziria um número que não é o que a trial declara.

Separação deliberada: o INSTANTE DA DECISÃO (quando o pick é emitido) é parte
do contrato da trial e continua fixo em 13:00/02:00. O FECHAMENTO precisa de
amostragem densa perto do apito. Este script faz só a segunda coisa — ele nunca
grava pick, nunca lê modelo, nunca decide nada.

Uso:
    python brasileirao_scripts/record_closing_snapshots.py
    python brasileirao_scripts/record_closing_snapshots.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.data.contracts import DataUnavailableError  # noqa: E402

from brasileirao_predictor import db  # noqa: E402
from brasileirao_predictor.data.bookmaker_odds import (  # noqa: E402
    MAPPING_VERSION,
    SNAPSHOTS,
    match_fixture,
    persist_snapshots,
)
from brasileirao_predictor.data.the_odds_api_provider import TheOddsApiProvider  # noqa: E402
from brasileirao_predictor.ingest import load_config  # noqa: E402

# Só faz sentido gastar chamada de API perto de um apito. Fora dessa janela o
# script sai em silêncio, sem consumir cota.
JANELA_ANTES = timedelta(hours=4)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="não grava")
    ap.add_argument("--force", action="store_true", help="ignora a janela de 4h antes do apito")
    args = ap.parse_args(argv)

    bookmaker = os.environ.get("BRASILEIRAO_BOOKMAKER")
    if not bookmaker:
        print(json.dumps({"status": "SKIPPED", "reason": "BRASILEIRAO_BOOKMAKER ausente"}))
        return 0

    cfg = load_config()
    conn = db.connect(str(ROOT / cfg["database"]), read_only=True)
    agora = datetime.now(UTC)
    fixtures = [
        {"event_id": r[0], "home_team": r[1], "away_team": r[2], "kickoff_at": r[3]}
        for r in conn.execute(
            "SELECT event_id, home_team, away_team, kickoff_at FROM sofascore_matches "
            "WHERE home_score IS NULL AND kickoff_at IS NOT NULL"
        )
    ]
    proximos = [f for f in fixtures if agora <= datetime.fromisoformat(f["kickoff_at"]) <= agora + JANELA_ANTES]
    if not proximos and not args.force:
        print(json.dumps({"status": "NO_KICKOFF_WINDOW", "proximos_4h": 0, "fixtures_futuros": len(fixtures)}))
        return 0

    try:
        api_rows = TheOddsApiProvider().fetch_ou25()
    except DataUnavailableError as exc:
        print(json.dumps({"status": "SOURCE_UNAVAILABLE", "reason": str(exc)}))
        return 1

    novos, sem_fixture = [], 0
    for row in api_rows:
        if row["bookmaker"] != bookmaker:
            continue
        fixture, status = match_fixture(row, fixtures)
        if fixture is None:
            sem_fixture += 1
            continue
        novos.append(
            {
                "event_id": fixture["event_id"],
                "market": "ou2.5",
                "selection": row["selection"],
                "odd": row["decimal_odds"],
                "odds_captured_at": row["odds_captured_at"],
                "bookmaker": bookmaker,
                "source": row["source"],
                "source_event_id": row["source_event_id"],
                "canonical_match_id": row["canonical_match_id"],
                "kickoff_at": fixture["kickoff_at"],
                "retrieved_at": row["retrieved_at"],
                "raw_payload_hash": row["raw_payload_hash"],
                "adapter_version": row["adapter_version"],
                "identity_status": status,
                "mapping_version": MAPPING_VERSION,
                "capture_kind": "closing_snapshot",
            }
        )

    gravados = 0 if args.dry_run else persist_snapshots(ROOT / "data" / SNAPSHOTS, novos)
    print(
        json.dumps(
            {
                "status": "OK",
                "bookmaker": bookmaker,
                "kickoffs_na_janela": len(proximos),
                "cotacoes_do_book": len(novos),
                "snapshots_novos": gravados,
                "sem_fixture": sem_fixture,
                "dry_run": args.dry_run,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
