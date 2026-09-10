"""Bounded unauthenticated primary-source requests; no odds or account API."""
import hashlib
import json
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'oddspapi_current_contract': 'https://oddspapi.io/us/docs/get-odds',
    'oddspapi_historical_contract': 'https://oddspapi.io/us/docs/get-historical-odds',
    'oddspapi_markets_contract': 'https://oddspapi.io/us/docs/get-markets',
    'football_data_notes': 'https://www.football-data.co.uk/notes.txt',
    'football_data_availability': 'https://www.football-data.co.uk/data.php',
    'the_odds_api_history_contract': 'https://the-odds-api.com/liveapi/guides/v4/#historical-odds',
    'github_current_ci': 'https://api.github.com/repos/leonardosovienski/brasileirao-predictor/actions/runs?head_sha=ac22c56c3318623e07a722f34d44dc6cd877ea37&per_page=3',
    'dotnet_10_release_metadata': 'https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json',
}

def main():
    out = ROOT / 'public-sources'
    out.mkdir(exist_ok=False)
    receipts = []
    for label, url in SOURCES.items():
        r = {'source':label,'url':url,'requested_at':datetime.now(UTC).isoformat(), 'authenticated':False}
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'brasileirao-independent-integral-review/1'})
            with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as response:
                raw = response.read(5_000_001)
                r.update(http_status=response.status, received_at=datetime.now(UTC).isoformat(), final_url=response.url,
                         content_type=response.headers.get('Content-Type'), date_header=response.headers.get('Date'))
            if len(raw)>5_000_000:
                raise ValueError('oversize_public_document')
            name=label+'.raw'
            (out/name).write_bytes(raw)
            r.update(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),status='SAVED')
        except urllib.error.HTTPError as exc:
            r.update(status='HTTP_FAILURE',http_status=exc.code)
        except Exception as exc:
            r.update(status='FAILURE',error_type=type(exc).__name__)
        receipts.append(r)
        (out/'receipts.json').write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:r[k] for k in ('source','status','http_status') if k in r}),flush=True)

if __name__ == '__main__':
    main()
