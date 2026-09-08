"""Append a lineup to the recoverable Worker inbox, without trimming pending work."""

import json

INBOX_KEY = "lineup:v2:inbox"
MAX_PENDING = 10000
_APPEND = """
local kind = redis.call('TYPE', KEYS[1]).ok
if kind ~= 'none' and kind ~= 'stream' then return redis.error_reply('invalid inbox type') end
if redis.call('XLEN', KEYS[1]) >= tonumber(ARGV[1]) then
    return redis.error_reply('lineup inbox full; retry after processing')
end
return redis.call('XADD', KEYS[1], '*', 'payload', ARGV[2])
"""


def enqueue_lineup(client, event: dict) -> str:
    """An accepted Redis stream ID confirms storage, not processing or financial use.

    Retry the same event unchanged after an uncertain reply. Worker registration
    is idempotent. No MAXLEN trimming is allowed on the input stream: producers
    receive a visible capacity error instead of deleting unprocessed events.
    """
    encoded = json.dumps(event, allow_nan=False, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 65536:
        raise ValueError("lineup payload exceeds the inbox size limit")
    result = client.eval(_APPEND, 1, INBOX_KEY, MAX_PENDING, encoded)
    return result.decode("ascii") if isinstance(result, bytes) else str(result)
