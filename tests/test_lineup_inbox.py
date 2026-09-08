import json

import pytest

from brasileirao_scripts.lineup_inbox import INBOX_KEY, enqueue_lineup


def test_enqueue_preserves_event_for_idempotent_retry_and_does_not_trim():
    class Client:
        def eval(self, script, count, key, capacity, raw):
            assert (count, key, capacity) == (1, INBOX_KEY, 10000)
            assert "MAXLEN" not in script and "XTRIM" not in script
            assert json.loads(raw) == event
            return b"100-1"

    event = {"MatchId": "synthetic", "CapturedAt": "2026-09-08T00:00:00+00:00"}
    assert enqueue_lineup(Client(), event) == "100-1"


@pytest.mark.parametrize("event", [{"oversized": "x" * 65537}, {"nonfinite": float("nan")}])
def test_invalid_serialization_is_not_sent_to_redis(event):
    with pytest.raises(ValueError):
        enqueue_lineup(None, event)
