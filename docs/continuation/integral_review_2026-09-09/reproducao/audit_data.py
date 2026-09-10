"""Explicit allowlisted historical/pilot audit; no 2026 outcome fields consumed."""
import csv
import hashlib
import io
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=Path('C:/BRASILEIRAO/brasileirao-predictor')
DC=Path('C:/BRASILEIRAO/work/data-completion-2026-09-09')

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    out=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'data-audit')
    if not out.resolve().is_relative_to(ROOT) or out.resolve()==ROOT:
        raise ValueError('output_inside_review_required')
    out.mkdir(exist_ok=False)
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(REPO))
    for key in list(os.environ):
        if key.upper() not in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT'}:
            del os.environ[key]
    def guard(event,args):
        if event.startswith(('socket.','sqlite3.','subprocess.','os.system')):
            raise PermissionError('offline_data_audit')
        if event=='open' and isinstance(args[0],str | bytes | os.PathLike):
            p=Path(os.fsdecode(args[0])).resolve()
            mode,flags=args[1] or '',args[2] or 0
            if (any(c in mode for c in 'wax+') or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT)) and not p.is_relative_to(out):
                raise PermissionError('only_new_audit_output')
            if p.name=='.env' or p.is_relative_to(Path('C:/BRASILEIRAO/DADOS_PRESERVADOS')) or any(p.is_relative_to(REPO/d) for d in ('data','reports','research')):
                raise PermissionError('private_or_protected_data')
    sys.addaudithook(guard)
    from brasileirao_predictor.research.price_strength.historical_admission import audit_history
    from brasileirao_predictor.research.price_strength.live_capture_admission import audit_capture, strict_json_loads
    from brasileirao_predictor.research.price_strength.closing_scenario import freeze_choices, settle_frozen
    def read(path):
        return strict_json_loads(path.read_bytes())
    def save(name,value):
        (out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    universe=read(DC/'universe.json')
    acquisition=read(DC/'acquisition.json')
    assert digest((DC/'universe.json').read_bytes())==acquisition['universe_sha256']
    assert len(universe)==177 and len({f['fixture_id'] for f in universe})==177
    records={r['fixture_id']:r for r in acquisition['records']}
    repair=read(DC/'transport_repair.json')
    for record in repair['records']:
        if 'file' in records[record['fixture_id']]:
            raise ValueError('repair_would_replace_successful_source')
        records[record['fixture_id']]=record
    histories=[]
    total_bytes=0
    for fixture in universe:
        r=records[fixture['fixture_id']]
        p=(DC/r['file']).resolve()
        assert p.is_relative_to(DC/'raw')
        raw=p.read_bytes()
        assert digest(raw)==r['sha256'] and len(raw)==r['bytes'],fixture['fixture_id']
        total_bytes+=len(raw)
        result=audit_history(strict_json_loads(raw),fixture,r['received_at'])
        result['verified_source_sha256']=digest(raw)
        histories.append(result)
    save('historical_audit.json',histories)
    print('177 historical payloads checked',flush=True)
    receipt=read(DC/'prospective_pilot/receipt.json')
    catalogue=read(DC/'prospective_pilot/fixture_catalog.json')
    event=next(x for x in catalogue if x['fixtureId']=='id1000032566887012')
    fields=('participant1Id','participant2Id','sportId','tournamentId','seasonId')
    expected={k:event[k] for k in fields}
    save('frozen_identity_receipt.json',{'identity':expected,'catalogue_sha256':digest((DC/'prospective_pilot/fixture_catalog.json').read_bytes()),'selected_fixture_sha256':digest((DC/'prospective_pilot/selected_fixture.json').read_bytes()),'source':'calendar_catalog_before_pilot_odds','home':event['participant1Name'],'away':event['participant2Name']})
    pilots=[]
    for r in receipt['requests']:
        if r.get('file','').startswith('capture_'):
            raw=(DC/'prospective_pilot'/r['file']).read_bytes()
            assert digest(raw)==r['sha256']
            a=audit_capture(strict_json_loads(raw),r,event['fixtureId'],expected_identity=expected)
            a['source_sha256']=digest(raw)
            pilots.append(a)
    assert len(pilots)==3
    save('pilot_audit.json',pilots)
    raw=(DC/'public_sources/football_data_bra_origin_csv.csv').read_bytes()
    assert digest(raw)=='ba3e9ea79ab4091b117a901f3914940cea07f1fe06de0deb57af5076f664ccb6'
    # Filter year before interpreting identity, scores, prices or any other field.
    source=[row for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))) if row.get('Season')=='2025']
    assert len(source)==380
    rows=[]; labels={}; teams=Counter(); pairs=Counter()
    for row in source:
        assert row['Country']=='Brazil' and row['League']=='Serie A'
        assert row['Home']!=row['Away']
        day=datetime.strptime(row['Date'],'%d/%m/%Y').date().isoformat()
        fid=day+'|'+row['Home']+'|'+row['Away']
        teams.update((row['Home'],row['Away'])); pairs.update([(row['Home'],row['Away'])])
        rows.append({'event_id':fid,'date':day,'offer':{s:row['B365C'+c] for s,c in [('home','H'),('draw','D'),('away','A')]},'reference':{s:row['PSC'+c] for s,c in [('home','H'),('draw','D'),('away','A')]}})
        labels[fid]={'home_goals':row['HG'],'away_goals':row['AG'],'result':row['Res']}
    frozen=freeze_choices(rows)
    original=read(DC/'closing-01/frozen_choices.json')
    assert frozen==original,'choices_diverged_from_frozen_known_study'
    replay=settle_frozen(frozen,labels)
    # Independent flat stake 1X2 account from labels/prices, no settlement code.
    returned=Decimal(0); bets=0
    for pick in frozen:
        if pick['status']=='CONDITIONAL_PICK':
            label=labels[pick['event_id']]
            h,a=int(label['home_goals']),int(label['away_goals'])
            winner='home' if h>a else 'away' if a>h else 'draw'
            assert label['result']=={'home':'H','away':'A','draw':'D'}[winner]
            bets+=1
            if pick['selection']==winner:
                returned+=Decimal(pick['decimal_odds'])
    independent=returned-Decimal(bets)*Decimal('1.02')
    assert independent==Decimal(replay['net_realized_pnl'])
    save('closing_reproduction.json',replay)
    summary={'at':datetime.now(UTC).isoformat(),'historical':{'universe':177,'verified':len(histories),'bytes':total_bytes,'reasons':dict(Counter(x['reason'] for x in histories)),'execution_admitted':sum(x['execution_admitted'] for x in histories),'receipts_after_decision':sum(x['archive_received_after_decision'] for x in histories)},'pilot':{'captures':len(pilots),'independent_events':len({x['fixture_id'] for x in pilots}),'api_pairs_admitted':sum(x['pair_api_state_admitted'] for x in pilots),'execution_admitted':0},'csv_2025':{'rows':len(source),'clubs':len(teams),'appearances_per_club':dict(teams),'unique_directed_pairs':len(pairs),'duplicate_directed_pairs':sum(v-1 for v in pairs.values()),'identical_frozen_choices':True,'bets':bets,'independent_net_pnl':str(independent),'fixed_costs_and_execution_costs_known':False},'labels_2026_used':False,'protected_cohorts_read':False,'profitability_established':False}
    save('summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
