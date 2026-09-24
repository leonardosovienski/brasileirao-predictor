"""Temporal suite of the Brasileirão research circuit (prompt §10), through the entrypoint.

Rule: for every information i used by prediction t, available_at(i) < cutoff(t).
Gates: TEMPORAL_INTEGRITY, FUTURE_CANARY, BR_KICKOFF_ORDERING, BR_TIMEZONE_INTEGRITY,
BR_METAMORPHIC, BR_SAME_KICKOFF_ISOLATION, BR_CACHE_STATE, BR_FUTURE_INJECTION.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_predictor.research_runtime import worker

from . import fixtures
from .harness import Lab, comparable, standard_lab

PERMUTATION_SEEDS = (11, 23, 37, 41, 53)


def _result(lab: Lab, request: dict, **kwargs) -> dict:
    code, outcome = lab.submit(request, **kwargs)
    assert code == 0 and outcome["status"] in {"RESULT", "DUPLICATE"}, outcome
    code, shown = lab.show(request["request_id"], state=kwargs.get("state"))
    assert code == 0
    return shown["result"]


@pytest.fixture(scope="module")
def variants():
    lab = standard_lab(
        {
            "synthetic": {},
            "canary": {"canary": True},
            "offsets": {"offsets": True},
            "clean-caches": {"poison_caches": False},
            **{f"perm-{seed}": {"permutation_seed": seed} for seed in PERMUTATION_SEEDS},
        }
    )
    yield lab
    lab.cleanup()


# ------------------------------------------------------------------ FUTURE_CANARY


def test_future_canary_never_reaches_any_artifact(variants: Lab) -> None:
    base = _result(variants, fixtures.request("brasileirao:REQ-CANARY-BASE", dataset="synthetic"))
    with_canary = _result(variants, fixtures.request("brasileirao:REQ-CANARY-ON", dataset="canary"))
    assert comparable(with_canary) == comparable(base), "rows after the cutoff changed a prediction"
    assert (
        with_canary["core_facts"]["temporal_validation"]["excluded_after_data_cutoff"]
        > base["core_facts"]["temporal_validation"]["excluded_after_data_cutoff"]
    )
    # The token appears nowhere the circuit wrote (effects, trials, results, outcomes, jobs, Ops events).
    for path in variants.state.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".sqlite"}:
            assert fixtures.CANARY.encode() not in path.read_bytes(), path


# ------------------------------------------------------------------ TEMPORAL_INTEGRITY


def test_every_prediction_uses_only_information_available_before_its_cutoff(variants: Lab) -> None:
    result = _result(variants, fixtures.request("brasileirao:REQ-PIT-001"))
    audit = result["core_facts"]["temporal_validation"]
    assert audit["engine"] == "predictor_core.measurement.replay"
    assert audit["max_used_minus_cutoff_seconds"] < 0
    events = fixtures.fixtures()
    for p in result["domain_facts"]["predictions"]:
        cutoff = datetime.fromisoformat(p["cutoff"].replace("Z", "+00:00"))
        kickoff = datetime.fromisoformat(p["kickoff"].replace("Z", "+00:00"))
        assert cutoff == kickoff - timedelta(minutes=60)
        available = [
            e
            for e in events
            if e["hs"] is not None
            and e["superseded_by"] is None
            and e["kickoff"] + timedelta(minutes=180) < cutoff
            and not (e["season"], e["round"], e["slot"]) == (2021, 1, 0)
        ]
        date_only = [e for e in events if (e["season"], e["round"], e["slot"]) == (2021, 1, 0)]
        expected = len(available) + sum(
            1
            for e in date_only
            if datetime.combine(e["kickoff"].date() + timedelta(days=1), datetime.min.time(), UTC) + timedelta(hours=3)
            < cutoff
        )
        assert p["n_information"] == expected, p["event_id"]


def test_handler_reads_only_the_captured_snapshot_not_the_live_database() -> None:
    lab = standard_lab()
    try:
        before = _result(lab, fixtures.request("brasileirao:REQ-SNAP-001"))
        fixtures.mutate_source(lab.root / "src" / "synthetic.sqlite3")  # write to the SOURCE after capture
        after = _result(lab, fixtures.request("brasileirao:REQ-SNAP-002"))
        assert comparable(after) == comparable(before)
        # The same question on a NEW capture of the mutated source must differ (the test can see a change).
        lab.put_dataset("recaptured", lab.root / "src" / "synthetic.sqlite3")
        lab.write_policy()
        changed = _result(lab, fixtures.request("brasileirao:REQ-SNAP-003", dataset="recaptured"))
        assert comparable(changed) != comparable(before)
    finally:
        lab.cleanup()


# ------------------------------------------------------------------ BR_METAMORPHIC / KICKOFF ORDERING


def test_metamorphic_row_order_permutations_do_not_change_results(variants: Lab) -> None:
    base = comparable(_result(variants, fixtures.request("brasileirao:REQ-META-BASE")))
    for seed in PERMUTATION_SEEDS:
        permuted = _result(variants, fixtures.request(f"brasileirao:REQ-META-{seed}", dataset=f"perm-{seed}"))
        assert comparable(permuted) == base, f"permutation seed {seed} changed the result"


def test_postponed_and_rescheduled_match_is_ordered_by_its_real_kickoff(variants: Lab) -> None:
    events = fixtures.fixtures()
    original = next(e for e in events if e["superseded_by"] is not None)
    replay_event = next(e for e in events if e["event_id"] == original["superseded_by"])
    result = _result(
        variants,
        fixtures.request(
            "brasileirao:REQ-RESCHEDULE-001", kickoff_from="2023-04-01T00:00:00Z", kickoff_to=fixtures.DATA_CUTOFF
        ),
    )
    predicted = {p["event_id"]: p for p in result["domain_facts"]["predictions"]}
    assert original["event_id"] not in predicted
    assert predicted[replay_event["event_id"]]["kickoff"] == replay_event["kickoff"].strftime("%Y-%m-%dT%H:%M:%SZ")
    assert result["domain_facts"]["data_quality"]["excluded_superseded"] == 1
    # Listing the superseded event, or the replay with its OLD kickoff, fails closed.
    stale = fixtures.request(
        "brasileirao:REQ-RESCHEDULE-002",
        kickoff_from="2023-04-01T00:00:00Z",
        fixtures_list=[
            {"event_id": original["event_id"], "kickoff_at": original["kickoff"].strftime("%Y-%m-%dT%H:%M:%SZ")}
        ],
    )
    code, outcome = variants.submit(stale)
    assert code == 2 and outcome["status"] == "REJECTED" and "EVENT_SUPERSEDED" in outcome["reason"]
    old_kickoff = fixtures.request(
        "brasileirao:REQ-RESCHEDULE-003",
        kickoff_from="2023-04-01T00:00:00Z",
        fixtures_list=[
            {"event_id": replay_event["event_id"], "kickoff_at": original["kickoff"].strftime("%Y-%m-%dT%H:%M:%SZ")}
        ],
    )
    code, outcome = variants.submit(old_kickoff)
    assert code == 2 and "KICKOFF_MISMATCH" in outcome["reason"]


def test_duplicate_fixture_fails_closed() -> None:
    lab = standard_lab({"dup": {"duplicate_fixture": True}})
    try:
        code, outcome = lab.submit(fixtures.request("brasileirao:REQ-DUP-001", dataset="dup"))
        assert code == 2 and outcome["status"] == "REJECTED" and "DUPLICATE_FIXTURE" in outcome["reason"]
    finally:
        lab.cleanup()


# ------------------------------------------------------------------ BR_SAME_KICKOFF_ISOLATION


def _score_change_keeps_prediction(
    changed: tuple[int, int, int], target: tuple[int, int, int], later: tuple[int, int, int]
) -> None:
    """Change the score of game `changed` in a new capture; `target`'s prediction must be byte-identical,
    and a `later` game must see the change (the test can detect a leak)."""
    import sqlite3

    pick = {(e["season"], e["round"], e["slot"]): e for e in fixtures.fixtures()}
    a, b, c = pick[changed], pick[target], pick[later]
    lab = standard_lab({"base": {}, "changed": {}})
    try:
        source = lab.root / "src" / "changed.sqlite3"
        conn = sqlite3.connect(source)
        for table in ("matches", "sofascore_matches"):
            conn.execute(f"UPDATE {table} SET home_score=9, away_score=0 WHERE event_id=?", (a["event_id"],))
        conn.commit()
        conn.close()
        lab.put_dataset("changed-v2", source)
        lab.write_policy()

        def one(event: dict, dataset: str, rid: str) -> dict:
            listed = [{"event_id": event["event_id"], "kickoff_at": event["kickoff"].strftime("%Y-%m-%dT%H:%M:%SZ")}]
            request = fixtures.request(
                rid, dataset=dataset, fixtures_list=listed, odds=False, kickoff_from="2023-06-01T00:00:00Z"
            )
            return _result(lab, request)["domain_facts"]["predictions"][0]

        tag = f"{changed[1]}{changed[2]}{target[2]}"
        assert one(b, "base", f"brasileirao:REQ-ISO-{tag}-B1") == one(b, "changed-v2", f"brasileirao:REQ-ISO-{tag}-B2")
        l1, l2 = one(c, "base", f"brasileirao:REQ-ISO-{tag}-L1"), one(c, "changed-v2", f"brasileirao:REQ-ISO-{tag}-L2")
        assert l1["information_fingerprint"] != l2["information_fingerprint"]
    finally:
        lab.cleanup()


def test_result_of_game_a_does_not_affect_game_b_with_the_same_kickoff() -> None:
    pick = {(e["season"], e["round"], e["slot"]): e for e in fixtures.fixtures()}
    assert pick[(2023, 12, 0)]["kickoff"] == pick[(2023, 12, 1)]["kickoff"]
    _score_change_keeps_prediction(changed=(2023, 12, 0), target=(2023, 12, 1), later=(2023, 13, 0))


def test_match_still_in_progress_is_not_information_for_the_next_kickoff() -> None:
    """21:30Z and 23:00Z games of one round: at the 22:00Z cutoff the 21:30Z game is being played."""
    pick = {(e["season"], e["round"], e["slot"]): e for e in fixtures.fixtures()}
    live, nxt = pick[(2023, 12, 2)], pick[(2023, 12, 3)]
    assert live["kickoff"] + timedelta(minutes=180) >= nxt["kickoff"] - timedelta(minutes=60)
    _score_change_keeps_prediction(changed=(2023, 12, 2), target=(2023, 12, 3), later=(2023, 13, 0))


# ------------------------------------------------------------------ BR_TIMEZONE_INTEGRITY


def test_venue_offsets_normalize_to_the_same_instants(variants: Lab) -> None:
    utc_result = comparable(_result(variants, fixtures.request("brasileirao:REQ-TZ-UTC")))
    local_result = comparable(_result(variants, fixtures.request("brasileirao:REQ-TZ-LOCAL", dataset="offsets")))
    assert local_result == utc_result


def test_naive_kickoff_in_the_dataset_fails_closed() -> None:
    lab = standard_lab({"naive": {"naive_event": True}})
    try:
        code, outcome = lab.submit(fixtures.request("brasileirao:REQ-TZ-NAIVE", dataset="naive"))
        assert code == 4 and outcome["status"] == "TEMPORAL_INTEGRITY_VIOLATION", outcome
        assert "without timezone" in outcome["reason"]
    finally:
        lab.cleanup()


@pytest.mark.parametrize(
    ("text", "expected_utc"),
    [
        ("2023-06-10T19:00:00-03:00", "2023-06-10T22:00:00Z"),  # America/Sao_Paulo
        ("2023-06-10T18:00:00-04:00", "2023-06-10T22:00:00Z"),  # America/Manaus
        ("2023-06-10T18:00:00-04:00", "2023-06-10T22:00:00Z"),  # America/Cuiaba
        ("2023-06-10T17:00:00-05:00", "2023-06-10T22:00:00Z"),  # America/Rio_Branco
        ("2018-02-17T23:30:00-02:00", "2018-02-18T01:30:00Z"),  # São Paulo summer time (1st 23:30)
        ("2018-02-17T23:30:00-03:00", "2018-02-18T02:30:00Z"),  # the repeated hour (2nd 23:30)
        ("2018-11-04T01:30:00-02:00", "2018-11-04T03:30:00Z"),  # after the skipped 00:00-00:59
        ("2016-10-16T01:30:00-03:00", "2016-10-16T04:30:00Z"),  # America/Cuiaba DST start 2016
    ],
)
def test_explicit_offsets_are_normalized_never_guessed(text: str, expected_utc: str) -> None:
    assert worker.parse_instant(text, "kickoff").strftime("%Y-%m-%dT%H:%M:%SZ") == expected_utc


@pytest.mark.parametrize(
    "text", ["2018-02-17T23:30:00", "2018-11-04T00:30:00", "2024-05-01T19:00:00", "2024-05-01", ""]
)
def test_ambiguous_nonexistent_or_naive_local_times_are_rejected(text: str) -> None:
    with pytest.raises(worker.TemporalViolation):
        worker.parse_instant(text, "kickoff")


# ------------------------------------------------------------------ BR_CACHE_STATE


def test_capture_time_caches_are_never_read(variants: Lab) -> None:
    poisoned = comparable(_result(variants, fixtures.request("brasileirao:REQ-CACHE-POISON")))
    clean = comparable(_result(variants, fixtures.request("brasileirao:REQ-CACHE-CLEAN", dataset="clean-caches")))
    assert poisoned == clean


def test_historical_prediction_is_the_same_after_running_a_future_date() -> None:
    """Across processes sharing one state root, and in one process sharing the refit memo."""
    fresh = standard_lab()
    shared = standard_lab()
    try:
        historical = fixtures.request(
            "brasileirao:REQ-HIST", kickoff_from="2023-06-01T00:00:00Z", kickoff_to="2023-07-15T00:00:00Z"
        )
        future = fixtures.request(
            "brasileirao:REQ-FUT", kickoff_from="2023-07-15T00:00:00Z", kickoff_to=fixtures.DATA_CUTOFF
        )
        in_fresh = comparable(_result(fresh, historical))
        _result(shared, future)
        in_shared = comparable(_result(shared, historical))
        assert in_shared == in_fresh
    finally:
        fresh.cleanup()
        shared.cleanup()


def test_same_process_memo_does_not_leak_a_future_refit() -> None:
    """In-process: the refit memo keyed by the exact information cannot serve a later fit early."""
    from datetime import UTC as _UTC

    cfg = fixtures.MODEL_CONFIG["config"]
    events = [e for e in fixtures.fixtures() if e["hs"] is not None and e["superseded_by"] is None]
    info = [
        {
            "event_id": e["event_id"],
            "date": e["kickoff"].date().isoformat(),
            "home": e["home"],
            "away": e["away"],
            "hs": e["hs"],
            "as": e["as"],
            "tournament": "Brasileirão Série A",
            "neutral": 0,
            "kickoff": e["kickoff"],
            "available_at": e["kickoff"] + timedelta(minutes=180),
        }
        for e in events
    ]
    info.sort(key=lambda r: (r["available_at"], r["event_id"]))

    def targets(start, end):
        out = []
        for e in events:
            if start <= e["kickoff"] < end:
                out.append(
                    {
                        "event_id": e["event_id"],
                        "home": e["home"],
                        "away": e["away"],
                        "kickoff": e["kickoff"],
                        "cutoff": e["kickoff"] - timedelta(minutes=60),
                        "neutral": 0,
                        "label": None,
                        "odds": {},
                    }
                )
        return sorted(out, key=lambda t: (t["cutoff"], t["kickoff"], t["event_id"]))

    hist = targets(datetime(2023, 6, 1, tzinfo=_UTC), datetime(2023, 7, 15, tzinfo=_UTC))
    fut = targets(datetime(2023, 7, 15, tzinfo=_UTC), datetime(2023, 10, 1, tzinfo=_UTC))
    fresh, _ = worker.walkforward(info, hist, cfg, worker.GoalModelCache())
    shared_cache = worker.GoalModelCache()
    worker.walkforward(info, fut, cfg, shared_cache)
    again, _ = worker.walkforward(info, hist, cfg, shared_cache)
    assert json.dumps(again, sort_keys=True) == json.dumps(fresh, sort_keys=True)


# ------------------------------------------------------------------ BR_FUTURE_INJECTION


def test_result_that_could_not_exist_at_capture_fails_closed() -> None:
    lab = standard_lab({"future": {"future_result": True}})
    try:
        code, outcome = lab.submit(fixtures.request("brasileirao:REQ-INJECT-001", dataset="future"))
        assert code == 4 and outcome["status"] == "TEMPORAL_INTEGRITY_VIOLATION", outcome
        code, shown = lab.show("brasileirao:REQ-INJECT-001")
        assert code == 3 and shown["status"] == "NOT_FOUND"
    finally:
        lab.cleanup()


def test_data_cutoff_after_the_snapshot_as_of_is_refused(variants: Lab) -> None:
    request = fixtures.request(
        "brasileirao:REQ-INJECT-002", kickoff_to="2023-12-31T00:00:00Z", data_cutoff="2024-02-01T00:00:00Z"
    )
    code, outcome = variants.submit(request)
    assert code == 2 and "DATA_CUTOFF_AFTER_DATASET_AS_OF" in outcome["reason"]
