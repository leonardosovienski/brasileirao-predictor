"""Two remaining document lookups; no authenticated API or price data."""
import hashlib
import json
import os
import urllib.request
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

out = Path(__file__).with_name('sources-followup')
out.mkdir(exist_ok=False)
for key in list(os.environ):
    if key.upper() not in {'SYSTEMROOT', 'WINDIR', 'PATH', 'COMSPEC', 'PATHEXT'}:
        del os.environ[key]
urls = {
    'sportmonks_timezone': 'https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/introduction/set-your-time-zone.md',
    'api_football_guide': 'https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide',
}
receipts = []
for name, url in urls.items():
    row = dict(id=name, url=url, requested_at=datetime.now(UTC).isoformat(), authenticated=False)
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Brasileirao-source-contract-audit/1.0'})
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError('document_size_budget_exceeded')
            row.update(status=response.status, final_url=response.url, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            with (out / (name + '.raw')).open('xb') as dest:
                dest.write(raw)
    except urllib.error.HTTPError as exc:
        row.update(error_type='HTTPError', status=exc.code)
    except Exception as exc:
        row.update(error_type=type(exc).__name__)
    row['received_at'] = datetime.now(UTC).isoformat()
    receipts.append(row)
    (out / 'receipts.json').write_text(json.dumps(receipts, indent=2), encoding='utf-8')
    print(json.dumps(row), flush=True)
