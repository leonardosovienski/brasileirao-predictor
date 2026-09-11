"""Research admission layer atop the project's curate/closing clock vocabulary.

Requires more information than the old conditional-replay interfaces. Unknown
publication/receipt cannot be imputed. Not source authentication. One invocation
handles one canonical selection contract; group markets only after all complete
selections have independently passed and share their snapshot vintage.
"""
from datetime import datetime,timezone
import json

def utc(value):
    if not isinstance(value,str):raise ValueError('timestamp missing/type')
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.tzinfo is None or d.utcoffset() is None:raise ValueError('timezone missing')
    return d.astimezone(timezone.utc)

def admit_selection(rows,context):
    decision=utc(context['predicted_at']);kickoff=utc(context['frozen_kickoff_at'])
    if not decision<kickoff: # RULE decision_before_kickoff
        return {'status':'REJECT','rule':'decision_before_kickoff'}
    known=[]
    for row in rows:
        try:
            if utc(row.get('captured_at'))>decision:continue
        except ValueError:return {'status':'REJECT','rule':'required_clock'}
        known.append(row)
    if not known:return {'status':'ABSTAIN','rule':'no_received_version'}
    latest=max(utc(r['captured_at']) for r in known)
    latest_rows=[r for r in known if utc(r['captured_at'])==latest]
    if len({json.dumps(r,sort_keys=True,allow_nan=False) for r in latest_rows})>1: # RULE conflict
        return {'status':'REJECT','rule':'conflict'}
    row=latest_rows[0]
    clocks={}
    for name in ['observed_at','published_at','available_at','captured_at','kickoff_at']:
        try:clocks[name]=utc(row.get(name))
        except ValueError:return {'status':'REJECT','rule':'required_clock'}
    if not all(clocks[k]<=decision for k in ['observed_at','published_at','available_at','captured_at']): # RULE before_cutoff
        return {'status':'REJECT','rule':'before_cutoff'}
    if not clocks['observed_at']<=clocks['published_at']<=clocks['available_at']<=clocks['captured_at']: # RULE clock_chain
        return {'status':'REJECT','rule':'clock_chain'}
    if clocks['kickoff_at']!=kickoff: # RULE kickoff_frozen
        return {'status':'REJECT','rule':'kickoff_frozen'}
    for key in ['source','source_match_id','canonical_match_id','mapping_version','home_id','away_id','bookmaker','market','selection','period','line']:
        if key not in row or key not in context or row[key]!=context[key]: # RULE identity
            return {'status':'REJECT','rule':'identity','field':key}
    if row.get('status')!='ACTIVE': # RULE latest_status
        return {'status':'ABSTAIN','rule':'latest_status'}
    if row.get('data_quality_status')!='OK':return {'status':'REJECT','rule':'quality'}
    return {'status':'ADMIT_SYNTHETIC_CONTRACT','rule':None,'captured_at':row['captured_at'],'identical_copies':len(latest_rows),'source_authentication':'NOT_ESTABLISHED'}
