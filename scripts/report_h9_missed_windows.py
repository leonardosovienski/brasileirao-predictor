"""report_h9_missed_windows — alerta OPS-P0: jogos cuja janela de decisão da
H9 (h9-ou25-prospective-replication) já ABRIU (kickoff - 90min - 15min de
folga) mas que não têm NENHUMA linha em data/research/h9_emission_attempts.jsonl
— sinal de que o poller de 15min (scripts/emit_h9_shadow.py) não rodou, ou
rodou e não conseguiu casar o fixture, durante toda a janela daquele jogo.

Diferente de scripts/report_h9_execution_quality.py (que mede POR QUE um jogo
avaliado não emitiu — bookmaker instável, sem cotação elegível), este script
mede jogos que o funil nunca chegou a AVALIAR — o problema é anterior: o job
agendado parou, ou o fixture nunca apareceu em `sofascore_matches` a tempo.

Duas categorias:
    - MISSED (severo): janela já FECHOU (jogo já teve apito, ou kickoff no
      passado) e zero tentativas registradas — a coorte prospectiva perdeu
      esse jogo, não há como recuperar o dado.
    - AT_RISK (aviso): janela está ABERTA agora e zero tentativas registradas
      ainda — pode ser só o primeiro tick (ok) ou o poller pode estar parado
      (investigar se a janela já está aberta há mais de ~20min sem nenhuma
      linha).

Não escreve nada, não decide nada, não abre matches.db em modo de escrita.

Uso (Task Scheduler, cadência sugerida: diária):
    python scripts/report_h9_missed_windows.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import db  # noqa: E402
from src.ingest import load_config  # noqa: E402
from src.research.h9_shadow import HORIZON  # noqa: E402

ATTEMPTS_PATH = ROOT / "data" / "research" / "h9_emission_attempts.jsonl"
WINDOW_SLACK = timedelta(minutes=15)
AT_RISK_GRACE = timedelta(minutes=20)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _finished_fixtures(conn, since: datetime) -> list[dict[str, Any]]:
    """Todos os jogos com kickoff conhecido, encerrados ou não — a janela
    importa só pelo horário de apito, independente de o placar já ter sido
    coletado."""
    rows = conn.execute(
        "SELECT event_id, home_team, away_team, kickoff_at FROM sofascore_matches "
        "WHERE kickoff_at IS NOT NULL AND kickoff_at >= ?",
        (since.isoformat(),),
    ).fetchall()
    return [
        {"event_id": eid, "home_team": home, "away_team": away, "kickoff_at": kickoff_at}
        for eid, home, away, kickoff_at in rows
    ]


def _window_bounds(kickoff_at: str) -> tuple[datetime, datetime] | None:
    try:
        kickoff = datetime.fromisoformat(str(kickoff_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if kickoff.tzinfo is None:
        return None
    return kickoff - HORIZON - WINDOW_SLACK, kickoff


def report(
    *,
    now: datetime | None = None,
    attempts_path: Path = ATTEMPTS_PATH,
    db_path: Path | None = None,
    lookback_days: int = 30,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    cfg = load_config()

    conn = db.connect(str(db_path or (ROOT / cfg["database"])), read_only=True)
    try:
        fixtures = _finished_fixtures(conn, now - timedelta(days=lookback_days))
    finally:
        conn.close()

    attempted_event_ids = {row.get("sofascore_event_id") for row in _load_jsonl(attempts_path)}

    missed: list[dict[str, Any]] = []
    at_risk: list[dict[str, Any]] = []
    for fx in fixtures:
        bounds = _window_bounds(fx["kickoff_at"])
        if bounds is None:
            continue
        window_open, window_close = bounds
        if now < window_open or fx["event_id"] in attempted_event_ids:
            continue
        entry = {
            "sofascore_event_id": fx["event_id"],
            "home": fx["home_team"],
            "away": fx["away_team"],
            "kickoff_at": fx["kickoff_at"],
            "window_open_at": window_open.isoformat(timespec="seconds"),
        }
        if now >= window_close:
            missed.append(entry)
        elif now - window_open >= AT_RISK_GRACE:
            at_risk.append(entry)

    return {
        "schema_version": "h9-missed-windows/v1",
        "checked_at": now.isoformat(timespec="seconds"),
        "missed_count": len(missed),
        "at_risk_count": len(at_risk),
        "missed": missed,
        "at_risk": at_risk,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lookback-days", type=int, default=30, help="janela de fixtures a checar (default: 30)")
    args = parser.parse_args()

    result = report(lookback_days=args.lookback_days)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["missed_count"]:
        print(
            f"H9_MISSED_WINDOW_ALERT missed={result['missed_count']} at_risk={result['at_risk_count']}",
            file=sys.stderr,
        )
        return 1
    if result["at_risk_count"]:
        print(f"H9_AT_RISK_WARNING at_risk={result['at_risk_count']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
