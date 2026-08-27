"""Replay diagnóstico da rodada de 22--24/08/2026, sem escrever no banco.

As odds são snapshots PIT do SofaScore (agregado sem bookmaker), portanto este
replay testa o encadeamento modelo -> sinal -> liquidação, não o A1
Pinnacle-versus-soft e não prova executabilidade ou edge econômico.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from src import model
from src.ingest import load_config
from src.sofascore import Sofascore

ROOT = Path(__file__).resolve().parent.parent
EVENT_IDS = (15235430, 15235438, 15235446, 15235454, 15235444, 15235436, 15235451, 15235435, 15235437, 15235432)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_results(client: Sofascore) -> dict[int, tuple[int, int]]:
    results = {}
    for event_id in EVENT_IDS:
        payload = client._get(f"event/{event_id}", cache=False) or {}
        event = payload.get("event", {})
        if (event.get("status") or {}).get("type") != "finished":
            raise RuntimeError(f"evento {event_id} não encerrado")
        results[event_id] = (int(event["homeScore"]["current"]), int(event["awayScore"]["current"]))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "replay_round_2026_08_22.json")
    args = parser.parse_args()
    database = ROOT / "data" / "matches.db"
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    elo = dict(connection.execute("SELECT team,elo FROM current_elo"))
    parameter_row = connection.execute(
        "SELECT param_a,param_b,param_alpha,param_rho,n_matches,config_hash,computed_at "
        "FROM model_parameters WHERE id=1"
    ).fetchone()
    if parameter_row is None:
        raise RuntimeError("model_parameters ausente")
    parameters = tuple(parameter_row[key] for key in ("param_a", "param_b", "param_alpha", "param_rho"))
    config = load_config()
    results = fetch_results(Sofascore(rate_limit=0, cache_dir=None))
    games, bets = [], []
    for event_id in EVENT_IDS:
        fixture = connection.execute(
            "SELECT home_team,away_team,kickoff_at FROM sofascore_matches WHERE event_id=?", (event_id,)
        ).fetchone()
        if fixture is None:
            raise RuntimeError(f"fixture {event_id} ausente")
        home, away, kickoff = fixture
        prediction = model.predict_match(
            elo[home],
            elo[away],
            parameters,
            float(config["elo"]["home_advantage"]),
            max_goals=int(config["model"]["max_goals"]),
        )
        captured_at = connection.execute(
            "SELECT max(captured_at) FROM odds_snapshots WHERE event_id=? AND captured_at < replace(?, '+00:00', 'Z')",
            (event_id, kickoff),
        ).fetchone()[0]
        odds = dict(
            connection.execute(
                "SELECT selection,odd FROM odds_snapshots WHERE event_id=? AND captured_at=? AND market='ou2.5'",
                (event_id, captured_at),
            )
        )
        home_score, away_score = results[event_id]
        actual_over = home_score + away_score > 2.5
        p_over = float(prediction["over"][2.5])
        signals = []
        for selection, probability in (("over", p_over), ("under", 1 - p_over)):
            if selection not in odds:
                continue
            gross_ev = probability * float(odds[selection]) - 1
            if gross_ev < 0.05:
                continue
            won = (selection == "over") == actual_over
            pnl = float(odds[selection]) - 1 if won else -1.0
            signal = {
                "selection": selection,
                "odd": odds[selection],
                "gross_ev": gross_ev,
                "won": won,
                "pnl_units": pnl,
                "indication_score": 0,
                "indication_reason": "unknown_bookmaker_and_not_proven_executable",
            }
            signals.append(signal)
            bets.append(signal)
        games.append(
            {
                "event_id": event_id,
                "home": home,
                "away": away,
                "kickoff_at": kickoff,
                "score": [home_score, away_score],
                "captured_at": captured_at,
                "hours_before_kickoff": (
                    datetime.fromisoformat(kickoff).astimezone(UTC)
                    - datetime.fromisoformat(captured_at.replace("Z", "+00:00")).astimezone(UTC)
                ).total_seconds()
                / 3600,
                "probabilities_1x2": [prediction["p_win"], prediction["p_draw"], prediction["p_loss"]],
                "p_over_2_5": p_over,
                "signals": signals,
            }
        )
    pnl = sum(float(bet["pnl_units"]) for bet in bets)
    report = {
        "schema_version": "retrospective-round-replay/1",
        "status": "DIAGNOSTIC_CONTAMINATED_NOT_CONFIRMATORY",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "decision_rule": "gross EV >= 5%; threshold previously inspected",
        "odds_provenance": "sofascore aggregate; bookmaker unknown; not executable A1 price",
        "model_state": dict(parameter_row),
        "summary": {
            "games": len(games),
            "signals": len(bets),
            "pnl_units": pnl,
            "roi": pnl / len(bets) if bets else None,
        },
        "games": games,
        "manifest": {
            "database_sha256": sha256(database),
            "config_sha256": sha256(ROOT / "config.yaml"),
            "script_sha256": sha256(Path(__file__)),
            "event_ids": list(EVENT_IDS),
        },
        "limitations": [
            "model cache is consistent with a pre-round state because local results are absent, "
            "but no historical cache attestation exists",
            "SofaScore odds do not identify bookmaker and cannot establish Pinnacle-versus-soft edge",
            "the 5% threshold and outcomes are already observed; ROI has zero confirmatory weight",
            "n=3 signals is far below useful statistical power",
        ],
        "capital_enabled": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output), **report["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
