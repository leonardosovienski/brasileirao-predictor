"""Frozen synthetic vectors for the Brasileirão research conformance suite.

Deterministic (seeded) SQLite datasets with the production schema (brasileirao_predictor.db),
built to exercise the temporal contract adversarially:

* rounds with SAME-KICKOFF pairs, a 21:30Z/23:00Z overlap (a match still in progress when the
  next one starts) and 00:30Z kickoffs whose UTC date is the next day;
* a postponed match (superseded event without score) replayed weeks later (inconsistent
  rounds) with its kickoff versions;
* one completed match without kickoff (date-only availability);
* the capture-time caches (current_elo, model_parameters, xg_model_parameters) filled with
  values that would change every prediction if read.

Options produce the adversarial variants: insertion-order permutation, FUTURE_CANARY rows after
the cutoff, a naive kickoff, local offsets per venue, a duplicate fixture, a result that could
not exist at the snapshot's as_of, poisoned caches, a changed score after capture.
No real data, no network.
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from brasileirao_predictor import db

CANARY = "FUTURE_CANARY_BR_001"
AS_OF = "2024-01-01T00:00:00Z"
DATA_CUTOFF = "2023-10-01T00:00:00Z"
CANARY_KICKOFF = datetime(2023, 10, 20, 22, 0, tzinfo=UTC)
TEAMS = [f"Clube {i:02d}" for i in range(1, 11)]
STRENGTH = {team: 0.25 - 0.05 * i for i, team in enumerate(TEAMS)}
VENUE_OFFSET = {  # venue timezone per home team (America/*), standard time (no DST after 2019)
    "Clube 01": -3,
    "Clube 02": -3,
    "Clube 03": -4,
    "Clube 04": -4,
    "Clube 05": -5,
    "Clube 06": -3,
    "Clube 07": -3,
    "Clube 08": -3,
    "Clube 09": -4,
    "Clube 10": -3,
}
# Kickoff slots of a round (UTC): same-kickoff pair, overlap 21:30 x 23:00, next-day 00:30Z.
SLOTS = [
    timedelta(hours=19),
    timedelta(hours=19),
    timedelta(hours=21, minutes=30),
    timedelta(hours=23),
    timedelta(hours=24, minutes=30),
]
SEASON_START = {
    2021: datetime(2021, 4, 3, tzinfo=UTC),
    2022: datetime(2022, 4, 2, tzinfo=UTC),
    2023: datetime(2023, 4, 15, tzinfo=UTC),
}
POSTPONED = {"season": 2023, "round": 4, "slot": 2, "days_later": 45}
DATE_ONLY = {"season": 2021, "round": 1, "slot": 0}
MODEL_CONFIG = {
    "schema": "brasileirao-model-config/1",
    "algorithm": "nbdc-normalized-elo-horizon-v2",
    "source": "config.yaml do brasileirao-predictor (elo + model), ensemble_xg desligado",
    "config": {
        "elo": {
            "initial_rating": 1500,
            "home_advantage": 100,
            "window_years": 6,
            "form_half_life_years": 4.0,
            "k_factors": {"Brasileirão Série A": 30, "default": 30, "Friendly": 20},
        },
        "model": {"calibration_window_years": 4, "goal_half_life_days": None, "max_goals": 12},
        "algorithm": "nbdc-normalized-elo-horizon-v2",
    },
}
FEATURES = {"schema": "brasileirao-features/1", "features": ["elo_diff_pre_match", "home_advantage"], "xg": False}
BASELINE_CLIM = {"schema": "brasileirao-baseline/1", "kind": "CLIMATOLOGY_PIT"}
BASELINE_MARKET = {"schema": "brasileirao-baseline/1", "kind": "MARKET_CLOSE_SHIN"}
COST_MODEL = {
    "schema": "brasileirao-cost-model/1",
    "edge_window": [0.02, 0.15],
    "stake": 1,
    "slippage_on_winnings": 0.02,
    "tax_on_annual_positive_net": 0.15,
    "min_bets": 30,
}
ODDS = {
    "schema": "brasileirao-odds/1",
    "source": "sofascore_matches",
    "price": "close",
    "use": "ex post evaluation only",
}


def _poisson(rng: random.Random, lam: float) -> int:
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def _pair_probs(home: str, away: str) -> tuple[float, float, float, float]:
    lh = math.exp(0.25 + STRENGTH[home] - STRENGTH[away])
    la = math.exp(0.05 + STRENGTH[away] - STRENGTH[home])
    ph = pd = pa = over = 0.0
    for i in range(11):
        for j in range(11):
            p = math.exp(-lh) * lh**i / math.factorial(i) * math.exp(-la) * la**j / math.factorial(j)
            if i > j:
                ph += p
            elif i == j:
                pd += p
            else:
                pa += p
            if i + j > 2.5:
                over += p
    s = ph + pd + pa
    return ph / s, pd / s, pa / s, over


def _rounds() -> list[tuple[str, str]]:
    teams = TEAMS[:]
    rounds = []
    for r in range(len(teams) - 1):
        pairs = [(teams[i], teams[-1 - i]) for i in range(len(teams) // 2)]
        rounds.append([(a, b) if r % 2 == 0 else (b, a) for a, b in pairs])
        teams = [teams[0], teams[-1], *teams[1:-1]]
    return rounds + [[(b, a) for a, b in rnd] for rnd in rounds]


def fixtures(seed: int = 20260924) -> list[dict]:
    """All synthetic events (deterministic), before any adversarial option."""
    rng = random.Random(seed)
    events, event_id = [], 5_000_000
    for season, start in SEASON_START.items():
        for r, games in enumerate(_rounds()):
            day = start + timedelta(days=7 * r)
            for slot, (home, away) in enumerate(games):
                event_id += 1
                kickoff = day + SLOTS[slot]
                ph, pd, pa, over = _pair_probs(home, away)
                hs = _poisson(rng, math.exp(0.25 + STRENGTH[home] - STRENGTH[away]))
                as_ = _poisson(rng, math.exp(0.05 + STRENGTH[away] - STRENGTH[home]))
                margin = 1.06
                close = [round(1 / (p * margin), 2) for p in (ph, pd, pa)]
                ou = [round(1 / (over * margin), 2), round(1 / ((1 - over) * margin), 2)]
                jitter = 1 + (rng.random() - 0.5) * 0.08
                event = {
                    "event_id": event_id,
                    "season": season,
                    "round": r + 1,
                    "slot": slot,
                    "home": home,
                    "away": away,
                    "kickoff": kickoff,
                    "hs": hs,
                    "as": as_,
                    "odds_close": close,
                    "odds_ou": ou,
                    "odds_open": [round(o * jitter, 2) for o in close],
                    "superseded_by": None,
                    "versions": [],
                }
                if (season, r + 1, slot) == (POSTPONED["season"], POSTPONED["round"], POSTPONED["slot"]):
                    replay_id = event_id + 900_000
                    replay_kickoff = kickoff + timedelta(days=POSTPONED["days_later"])
                    events.append(event | {"hs": None, "as": None, "superseded_by": replay_id})
                    events.append(
                        event
                        | {
                            "event_id": replay_id,
                            "kickoff": replay_kickoff,
                            "versions": [(kickoff, "RESCHEDULED"), (replay_kickoff, "SCHEDULED")],
                        }
                    )
                    continue
                events.append(event)
    return events


def _kickoff_text(event: dict, *, offsets: bool) -> str | None:
    kickoff = event["kickoff"]
    if event.get("date_only"):
        return None
    if event.get("naive"):
        return kickoff.replace(tzinfo=None).isoformat(timespec="seconds")
    if offsets:
        zone = timezone(timedelta(hours=VENUE_OFFSET.get(event["home"], -3)))
        return kickoff.astimezone(zone).isoformat(timespec="seconds")
    return kickoff.isoformat(timespec="seconds")


def build_dataset(
    path: Path,
    *,
    permutation_seed: int | None = None,
    canary: bool = False,
    naive_event: bool = False,
    offsets: bool = False,
    duplicate_fixture: bool = False,
    future_result: bool = False,
    poison_caches: bool = True,
    extra_events: list[dict] | None = None,
) -> Path:
    """Write one synthetic SQLite dataset with the production schema; returns its path."""
    events = [dict(e) for e in fixtures()]
    for e in events:
        if (e["season"], e["round"], e["slot"]) == (DATE_ONLY["season"], DATE_ONLY["round"], DATE_ONLY["slot"]):
            e["date_only"] = True
    if naive_event:
        target = next(e for e in events if e["season"] == 2023 and e["round"] == 12 and e["slot"] == 1)
        target["naive"] = True
    if canary:
        base = max(e["event_id"] for e in events)
        template = next(e for e in events if e["season"] == 2023 and e["superseded_by"] is None)
        for offset, (home, away, hs, as_, days) in enumerate(
            ((CANARY, TEAMS[0], 17, 0, 0), (TEAMS[1], CANARY, 0, 17, 7)), 1
        ):
            events.append(
                template
                | {
                    "event_id": base + offset,
                    "home": home,
                    "away": away,
                    "hs": hs,
                    "as": as_,
                    "kickoff": CANARY_KICKOFF + timedelta(days=days),
                    "versions": [],
                }
            )
    if duplicate_fixture:
        original = next(e for e in events if e["season"] == 2023 and e["round"] == 12 and e["slot"] == 3)
        # A second Sofascore event for the same fixture (the matches table cannot hold both: PK date/teams).
        events.append(original | {"event_id": original["event_id"] + 800_000, "versions": [], "sofascore_only": True})
    if future_result:
        base = max(e["event_id"] for e in events)
        events.append(
            events[0]
            | {
                "event_id": base + 10,
                "kickoff": datetime(2024, 3, 1, 22, 0, tzinfo=UTC),
                "season": 2024,
                "versions": [],
            }
        )
    for extra in extra_events or []:
        events.append(dict(extra))
    order = list(range(len(events)))
    if permutation_seed is not None:
        random.Random(permutation_seed).shuffle(order)
    path = Path(path)
    if path.exists():
        path.unlink()
    conn = db.connect(str(path))
    try:
        for index in order:
            e = events[index]
            kickoff_text = _kickoff_text(e, offsets=offsets)
            day = e["kickoff"].astimezone(UTC).date().isoformat()
            conn.execute(
                "INSERT INTO sofascore_matches (event_id, competition, season, date, kickoff_at, home_team, away_team, "
                "home_score, away_score, odds_home, odds_draw, odds_away, odds_over, odds_under, odds_home_open, "
                "odds_draw_open, odds_away_open, superseded_by_event_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    e["event_id"],
                    f"Brasileirão Série A {e['season']}",
                    str(e["season"]),
                    day,
                    kickoff_text,
                    e["home"],
                    e["away"],
                    e["hs"],
                    e["as"],
                    *e["odds_close"],
                    *e["odds_ou"],
                    *e["odds_open"],
                    e["superseded_by"],
                ),
            )
            for version, (when, status) in enumerate(e["versions"], start=1):
                conn.execute(
                    "INSERT INTO match_kickoff_versions VALUES (?,?,?,?,?,?)",
                    (
                        e["event_id"],
                        version,
                        when.isoformat(timespec="seconds"),
                        status,
                        version + 1 if status == "RESCHEDULED" else None,
                        "2023-06-01T00:00:00+00:00",
                    ),
                )
            if e["hs"] is not None and e["superseded_by"] is None and not e.get("sofascore_only"):
                conn.execute(
                    "INSERT INTO matches (event_id, date, home_team, away_team, home_score, away_score, tournament, "
                    "city, country, neutral) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        e["event_id"],
                        day,
                        e["home"],
                        e["away"],
                        e["hs"],
                        e["as"],
                        "Brasileirão Série A",
                        None,
                        "Brazil",
                        0,
                    ),
                )
        if poison_caches:
            for team in [*TEAMS, CANARY]:
                conn.execute(
                    "INSERT OR REPLACE INTO current_elo VALUES (?, ?)", (team, 9999.0 if team == TEAMS[-1] else 1.0)
                )
            conn.execute(
                "INSERT OR REPLACE INTO model_parameters VALUES (1, 5.0, 9.0, 2.0, 0.3, 999, 'poisoned', ?)",
                ("2023-12-31T00:00:00Z",),
            )
            conn.execute(
                "INSERT OR REPLACE INTO xg_model_parameters VALUES (1, ?, 999, 'poisoned', '2023-12-31T00:00:00Z')",
                (json.dumps({"canary": CANARY}),),
            )
        conn.commit()
        conn.execute("PRAGMA journal_mode=DELETE")
    finally:
        conn.close()
    return path


def mutate_source(path: Path) -> None:
    """Write into the SOURCE database after capture (scores, new rows, caches)."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("UPDATE matches SET home_score = home_score + 3 WHERE date < '2023-09-01'")
        conn.execute("UPDATE sofascore_matches SET odds_home = 1.01 WHERE season = '2023'")
        conn.execute("DELETE FROM matches WHERE date >= '2022-01-01' AND date < '2022-06-01'")
        conn.commit()
    finally:
        conn.close()


def policy(registry: list[dict], **limits_override) -> dict:
    limits = {
        "max_pending_requests": 50,
        "max_request_bytes": 65536,
        "max_parameter_bytes": 32768,
        "max_concurrency": 1,
        "cpu_seconds": 1800,
        "memory_mb": 2048,
        "disk_mb": 1024,
        "timeout_seconds": 1800,
        "max_retries": 2,
        "max_priority": "NORMAL",
    } | limits_override
    return {
        "schema_version": "BrasileiraoResearchAdmissionPolicyV1",
        "policy_id": "brasileirao-research-qualification",
        "policy_version": 1,
        "owner": "BRASILEIRAO_OPERATOR",
        "requester_trust": "LOCAL_FILE_ONLY",
        "handlers": {"WALKFORWARD_FORECAST_EVALUATION": "brasileirao.handlers.walkforward_forecast_evaluation.v1"},
        "hypotheses": {
            "brasileirao:HQ-SERVING-BASELINE": {
                "hypothesis_family": "brasileirao:serving-baseline",
                "purpose": "walk-forward do modelo de serving congelado contra baseline, sem retunar",
            }
        },
        "protected_hypotheses": [
            "brasileirao:H8",
            "brasileirao:H9",
            "brasileirao:H14",
            "brasileirao:H15",
            "brasileirao:A1",
        ],
        "season_policy": {
            "2021": "DEVELOPMENT",
            "2022": "DEVELOPMENT",
            "2023": "DEVELOPMENT",
            "2024": "VALIDATION",
            "2025": "HOLDOUT_SEALED",
            "2026": "EXPLORATORY",
        },
        "allowed_competitions": ["Brasileirão Série A"],
        "registry": registry,
        "limits": limits,
    }


def request(
    request_id: str,
    *,
    target: str = "1X2",
    season: int = 2023,
    kickoff_from: str = "2023-06-01T00:00:00Z",
    kickoff_to: str = DATA_CUTOFF,
    data_cutoff: str = DATA_CUTOFF,
    dataset: str = "synthetic",
    baseline: str = "climatology",
    odds: bool = True,
    fixtures_list: list[dict] | None = None,
    hypothesis: str = "brasileirao:HQ-SERVING-BASELINE",
    lead: int = 60,
    client_ref: object | None = None,
) -> dict:
    refs = {
        "dataset": {"name": dataset, "version": "1"},
        "model": {"name": "serving-baseline", "version": "1"},
        "features": {"name": "elo-home-advantage", "version": "1"},
        "baseline": {"name": baseline, "version": "1"},
        "cost_model": {"name": "close-slippage-tax", "version": "1"},
    }
    if odds:
        refs["odds"] = {"name": "sofascore-close", "version": "1"}
    events: dict = {"kickoff_from": kickoff_from, "kickoff_to": kickoff_to}
    if fixtures_list is not None:
        events["fixtures"] = fixtures_list
    out = {
        "schema_version": "brasileirao-research-request/1",
        "request_id": request_id,
        "request_type": "WALKFORWARD_FORECAST_EVALUATION",
        "research_id": "brasileirao:R-CONFORMANCE",
        "hypothesis_id": hypothesis,
        "competition": "Brasileirão Série A",
        "season": season,
        "target": target,
        "events": events,
        "data_cutoff": data_cutoff,
        "decision_lead_minutes": lead,
        "references": refs,
        "priority_hint": "NORMAL",
    }
    if client_ref is not None:
        out["client_ref"] = client_ref
    return out


__all__ = [
    "AS_OF",
    "BASELINE_CLIM",
    "BASELINE_MARKET",
    "CANARY",
    "COST_MODEL",
    "DATA_CUTOFF",
    "FEATURES",
    "MODEL_CONFIG",
    "ODDS",
    "build_dataset",
    "fixtures",
    "mutate_source",
    "policy",
    "request",
]
