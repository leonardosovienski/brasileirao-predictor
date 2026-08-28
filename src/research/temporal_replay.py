"""Build auditable manifests for new temporal replay experiments."""

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from src.temporal_policy import FallbackPolicy, TemporalPolicy, assert_unique_teams


def build_temporal_manifest(
    rows: Iterable[dict[str, Any]], *, fallback: FallbackPolicy = "group_by_date"
) -> dict[str, Any]:
    materialized = list(rows)
    policy = TemporalPolicy(fallback=fallback)
    groups = policy.group(materialized)
    for group in groups:
        assert_unique_teams(group)
    source_payload = json.dumps(materialized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema_version": "temporal-replay-manifest/v1",
        "temporal_policy": {"version": policy.version, "fallback": fallback, "fingerprint": policy.fingerprint},
        "source_sha256": hashlib.sha256(source_payload).hexdigest(),
        "row_count": len(materialized),
        "group_count": len(groups),
        "groups": [
            {
                "key": group.key,
                "precision": group.precision,
                "row_count": len(group.rows),
            }
            for group in groups
        ],
    }
