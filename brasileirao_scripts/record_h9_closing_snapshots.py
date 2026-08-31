"""record_h9_closing_snapshots — coleta MAIS DENSA de cotações perto do apito.

Por que existe: `collect_market_research.py` roda a cada 6h — bom pra pesquisa
geral, mas "fechamento" medido contra uma amostra de até 6h de idade não é
fechamento (é a mesma abertura-fantasma que já invalidou a H1 original: medir
CLV contra um preço velho fabrica um número que não é o que a trial declara).
`h9_shadow.settle()` precisa da ÚLTIMA cotação válida antes do apito, da MESMA
casa que decidiu o pick — só existe se alguém amostrar perto o bastante.

Escreve no MESMO data/research/market_observations.jsonl que
`scripts/emit_h9_shadow.py` já lê — não é um arquivo novo, é a mesma fonte
amostrada com mais frequência quando um apito está próximo. O dedupe é por
(bookmaker, mercado, seleção, odds_captured_at) — rodar sem a odd ter mudado
não duplica nada (ver `persist_snapshots`).

Só bate na API quando existe pelo menos um jogo dentro da janela — fora dela
sai em silêncio, sem gastar cota. NUNCA decide, nunca emite pick, nunca lê
modelo — só amostra.

Uso (Task Scheduler, cadência sugerida: a cada 15 minutos):
    python brasileirao_scripts/record_h9_closing_snapshots.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.data.contracts import DataUnavailableError  # noqa: E402

from brasileirao_predictor import db  # noqa: E402
from brasileirao_predictor.data.market_anchor import persist_market_observations  # noqa: E402
from brasileirao_predictor.data.the_odds_api_provider import TheOddsApiProvider  # noqa: E402
from brasileirao_predictor.ingest import load_config  # noqa: E402

MARKET_OBS_PATH = ROOT / "data" / "research" / "market_observations.jsonl"
WINDOW_BEFORE_KICKOFF = timedelta(hours=3)


def _has_upcoming_kickoff(conn, now: datetime, window: timedelta) -> bool:
    rows = conn.execute(
        "SELECT kickoff_at FROM sofascore_matches WHERE home_score IS NULL AND kickoff_at IS NOT NULL"
    ).fetchall()
    for (kickoff_at,) in rows:
        try:
            kickoff = datetime.fromisoformat(str(kickoff_at).replace("Z", "+00:00"))
        except ValueError:
            continue
        if kickoff.tzinfo is not None and now <= kickoff <= now + window:
            return True
    return False


def run(
    *,
    now: datetime | None = None,
    db_path: Path | None = None,
    market_obs_path: Path = MARKET_OBS_PATH,
    window: timedelta = WINDOW_BEFORE_KICKOFF,
) -> dict:
    now = now or datetime.now(UTC)
    cfg = load_config()
    conn = db.connect(str(db_path or (ROOT / cfg["database"])), read_only=True)
    try:
        imminent = _has_upcoming_kickoff(conn, now, window)
    finally:
        conn.close()
    if not imminent:
        return {"status": "NO_KICKOFF_WINDOW", "rows_written": 0}
    try:
        rows = TheOddsApiProvider().fetch_markets(markets=("totals",), retrieved_at=now)
    except DataUnavailableError as exc:
        return {"status": "SOURCE_UNAVAILABLE", "reason": str(exc), "rows_written": 0}
    written = persist_market_observations(market_obs_path, rows)
    return {"status": "OK", "rows_written": written}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
