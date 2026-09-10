"""Bounded public contract retrieval; no authentication or API quota."""
import hashlib
import json
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'oddspapi_limit_semantics': 'https://oddspapi.io/blog/betting-limits-api-stake-sizing/',
    'bet365_br_stake_limits': 'https://help.bet365.bet.br/s/pt-br/sports/min-max-stake',
    'oddspapi_current_odds_contract': 'https://oddspapi.io/us/docs/get-odds',
    'receita_current_service': 'https://www.gov.br/pt-br/servicos/apurar-imposto-sobre-premios-de-apostas-na-loteria-de-quota-fixa-e-em-fantasy-sport',
    'receita_2026_tables': 'https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/2026',
}


def main():
    out = ROOT/'public_sources'
    out.mkdir(exist_ok=False)
    rows = []
    for name, url in SOURCES.items():
        row = {'source': name, 'url': url, 'requested_at': datetime.now(UTC).isoformat()}
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'brasileirao-contract-audit/1'})
            with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as response:
                raw = response.read(10_000_001)
                row.update(http_status=response.status, received_at=datetime.now(UTC).isoformat(),
                           final_url=response.url, date_header=response.headers.get('Date'))
            if len(raw) > 10_000_000:
                raise ValueError('oversize')
            (out/(name+'.html')).write_bytes(raw)
            row.update(status='SAVED', file=name+'.html', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        except urllib.error.HTTPError as exc:
            row.update(status='HTTP_FAILURE', http_status=exc.code)
        except Exception as exc:
            row.update(status='FAILURE', error_type=type(exc).__name__)
        rows.append(row)
        (out/'manifest.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k in ('source','http_status','status')} for r in rows]))


if __name__ == '__main__':
    main()
