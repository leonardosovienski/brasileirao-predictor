"""Pure Redis invocation validation shared by daemon and verification tools.

Importing this module starts no numeric runtime, logging, connection or worker.
"""

import json
import math

from brasileirao_predictor import kernel_redis_v2 as protocol


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field in invocation")
        result[key] = value
    return result


_INVOKE_ID_FIELDS = ("job_id", "run_id", "match_id", "idempotency_key")
_INVOKE_NUMBER_FIELDS = ("elo_a", "elo_b", "dvorp_a", "dvorp_b")
_INVOKE_FIELDS = frozenset(
    (*_INVOKE_ID_FIELDS, *_INVOKE_NUMBER_FIELDS, "protocol_version", "timestamp_t3", "state_version")
)


def parse_invoke(payload_bytes: bytes) -> dict:
    """Valida redis-protocol-v2 sem I/O nem coerção de tipos JSON."""
    msg = json.loads(payload_bytes, object_pairs_hook=_unique_object)
    if not isinstance(msg, dict) or msg.keys() != _INVOKE_FIELDS:
        raise ValueError("campos fora do contrato")
    if msg["protocol_version"] != protocol.PROTOCOL_VERSION:
        raise ValueError("protocol_version incompatível")
    for field in _INVOKE_ID_FIELDS:
        if not isinstance(msg[field], str) or not msg[field]:
            raise ValueError("identifiers obrigatórios inválidos")
    for field in _INVOKE_NUMBER_FIELDS:
        value = msg[field]
        if type(value) not in (int, float):
            raise ValueError("entrada numérica inválida")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("entrada numérica não finita")
        msg[field] = value
    timestamp = msg["timestamp_t3"]
    # JSON Schema integer também admite representações como 1.0, mas não bool.
    if not (type(timestamp) is int or (type(timestamp) is float and timestamp.is_integer())) or timestamp < 0:
        raise ValueError("timestamp_t3 inválido")
    version = msg["state_version"]
    if (
        not isinstance(version, str)
        or not version.isascii()
        or not version.isdecimal()
        or version.startswith("0")
        or len(version) > 19
        or int(version) > 9223372036854775807
    ):
        raise ValueError("state_version inválida")
    return msg
