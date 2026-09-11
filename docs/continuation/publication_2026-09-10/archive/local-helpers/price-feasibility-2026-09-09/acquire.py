"""Explicit allowlist acquisition; never extracts private or protected files."""
import hashlib
import json
import urllib.request
import urllib.error
import zipfile
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
PACKAGE = Path('C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS')
ENTRY = 'projetos/brasileirao-predictor-sessoes/2026-09-07/price_strength_evaluation_2026-09-07/inputs/history.json'
EXPECTED = '14153f7cbb348e9eef22a8e1c438757b1ef482951e2576d4a8381d7928e8e142'


def local():
    with zipfile.ZipFile(PACKAGE / 'brasileirao-predictor-dados.zip') as archive:
        blob = archive.read(ENTRY)
    digest = hashlib.sha256(blob).hexdigest()
    if digest != EXPECTED:
        raise ValueError('local_input_hash_mismatch')
    with (ROOT / 'history.json').open('xb') as output:
        output.write(blob)
    payload = json.loads(blob)
    print(json.dumps({'local_sha256': digest, 'type': type(payload).__name__,
                     'keys': list(payload)[:12] if isinstance(payload, dict) else None,
                     'row_keys': list(payload[0]) if isinstance(payload, list) and payload else None}))


def public(url, filename):
    receipt = {'url': url, 'started_at': datetime.now(timezone.utc).isoformat(),
               'authenticated': False, 'paid_api_calls': 0}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'brasileirao-research/1.0'})
        with urllib.request.urlopen(request, timeout=25) as response:
            blob = response.read(4_000_001)
            if len(blob) > 4_000_000:
                raise ValueError('response_size_limit')
            receipt.update(status=response.status, bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(),
                           content_type=response.headers.get('Content-Type'),
                           last_modified=response.headers.get('Last-Modified'))
        with (ROOT / filename).open('xb') as output:
            output.write(blob)
    except urllib.error.HTTPError as exc:
        receipt.update(error='HTTPError', status=exc.code)
    except Exception as exc:
        receipt.update(error=type(exc).__name__)
    receipt['received_at'] = datetime.now(timezone.utc).isoformat()
    with (ROOT / (filename + '.receipt.json')).open('x', encoding='utf-8') as output:
        json.dump(receipt, output, indent=2)
    print(json.dumps(receipt))


if __name__ == '__main__':
    local()
    public('https://www.football-data.co.uk/brazil.php', 'football-data-brazil.html')
    public('https://www.football-data.co.uk/notes.txt', 'football-data-notes.txt')
