"""Fixed public documentation acquisition; no credentials or price quota."""
import hashlib
import json
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'sources'
URLS = {
    'the_odds_api_v4': 'https://the-odds-api.com/liveapi/guides/v4/',
    'sportmonks_pagination': 'https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/introduction/pagination.md',
    'sportmonks_request': 'https://docs.sportmonks.com/v3/welcome/making-your-first-request.md',
    'sportmonks_timezones': 'https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/introduction/timezones.md',
    'api_football_v3': 'https://www.api-football.com/documentation-v3',
}
for key in list(os.environ):
    if key.upper() not in {'SYSTEMROOT', 'WINDIR', 'PATH', 'COMSPEC', 'PATHEXT'}:
        del os.environ[key]
ROOT.mkdir(exist_ok=False)
receipts = []
for name, url in URLS.items():
    receipt = {'id': name, 'url': url, 'requested_at': datetime.now(UTC).isoformat(), 'authenticated': False}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Brasileirao-source-contract-audit/1.0'})
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError('document_size_budget_exceeded')
            receipt.update(status=response.status, final_url=response.url, received_at=datetime.now(UTC).isoformat(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            (ROOT / (name + '.raw')).write_bytes(raw)
    except Exception as exc:
        receipt.update(error_type=type(exc).__name__, received_at=datetime.now(UTC).isoformat())
    receipts.append(receipt)
    (ROOT / 'receipts.json').write_text(json.dumps(receipts, indent=2), encoding='utf-8')
    print(json.dumps(receipt), flush=True)
