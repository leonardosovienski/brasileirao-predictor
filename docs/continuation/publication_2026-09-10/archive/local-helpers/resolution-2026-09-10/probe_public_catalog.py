"""Bounded public catalog acquisition; no event, outcome, order or user endpoint."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import requests

root = Path('C:/BRASILEIRAO/work/resolution-2026-09-10/public-catalog')
root.mkdir(exist_ok=False)
plan = dict(purpose='CPL-P26: test a different legitimate public source for nominal football market metadata',
    performance_evaluation=False, credentials=False, accounts=False, orders=False,
    endpoint='https://gamma-api.polymarket.com/sports', public_get_budget=1, byte_budget=2*1024*1024,
    timeout_seconds=30, retries=0, redirects=False, protected_api_quota_consumption=0,
    rate_limit_reference='https://docs.polymarket.com/api-reference/rate-limits',
    documented_gamma_general_limit='4000 requests/10 seconds',
    public_access_reference='https://docs.polymarket.com/market-data/overview',
    access_scope='public market-data REST: no API key, wallet or authentication; no paid service contracted',
    geography_reference='https://docs.polymarket.com/api-reference/geoblock',
    legal_or_personal_trading_eligibility='not assessed; no trade or authentication',
    stop='one catalog GET; no event/outcome response fetched, no historical performance, no automatic collector')
(root/'plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
receipt = dict(plan=plan, started_at=datetime.now(UTC).isoformat())
session = requests.Session()
session.trust_env = False
try:
    with session.get(plan['endpoint'], timeout=(10,30), stream=True, allow_redirects=False) as response:
        receipt['status_code'] = response.status_code
        total=0
        with (root/'response.raw').open('xb') as handle:
            for block in response.iter_content(8192):
                total+=len(block)
                if total>plan['byte_budget']:
                    raise ValueError('byte_budget_exceeded')
                handle.write(block)
        payload=(root/'response.raw').read_bytes()
        receipt.update(bytes=total, sha256=hashlib.sha256(payload).hexdigest())
        response.raise_for_status()
        data=json.loads(payload)
        if not isinstance(data,list):
            raise ValueError('catalog_schema_not_a_list')
        receipt.update(entries=len(data), sports=[{key:row.get(key) for key in ('sport','series','tags')} for row in data])
except (requests.RequestException, ValueError) as exc:
    receipt.update(failure_type=type(exc).__name__, failure_scope='one public catalog request; not evidence of no economic opportunity')
finally:
    receipt['finished_at']=datetime.now(UTC).isoformat()
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt))
