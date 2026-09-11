"""Atomic FT 1X2 admission; declared clocks are validated, not authenticated."""
import json
from dataclasses import asdict
from strict_pit import admit_selection, utc
from strict_math import CLASSES, devig, odds_vector

POLICY = {'version':'joint-1x2/1','max_age_seconds':300,'clock_skew_seconds':0,
          'period':'FT','market':'1X2','rules':'90_MIN_PLUS_STOPPAGE_NO_EXTRA_TIME',
          'snapshot':'common_id_and_receipt','method':'proportional','underround':'reject'}

def reject(rule,status='REJECT',**detail):
    return {'status':status,'rule':rule,'probabilities':None,**detail}

def admit_market(rows,context):
    """No reassembly of individually latest quotes and no older-price fallback."""
    if not isinstance(rows,list) or not isinstance(context,dict):return reject('input_shape')
    try:
        decision=utc(context['predicted_at']); kickoff=utc(context['frozen_kickoff_at'])
        if decision>=kickoff:return reject('decision_before_kickoff')
        for field in ['source','source_match_id','canonical_match_id','mapping_version','home_id','away_id','bookmaker']:
            if not isinstance(context.get(field),str) or not context[field].strip():return reject('context_identity',field=field)
        if context['home_id']==context['away_id']:return reject('distinct_teams')
        if any(context.get(k)!=POLICY[k] for k in ['market','period','rules']) or context.get('line') is not None:
            return reject('contract')
        known=[]
        for row in rows:
            if not isinstance(row,dict):return reject('row_shape')
            captured=utc(row.get('captured_at'))
            if captured<=decision:known.append(row)
        if not known:return reject('no_received_snapshot','ABSTAIN')
        latest=max(utc(r['captured_at']) for r in known)
        selected=[r for r in known if utc(r['captured_at'])==latest]
        snapshots={r.get('snapshot_id') for r in selected}
        if len(snapshots)!=1 or not all(isinstance(v,str) and v.strip() for v in snapshots): # MUT snapshot
            return reject('snapshot_conflict')
        # Exact delivery retries collapse; differing quotes at the same instant do not.
        selected=list({json.dumps(r,sort_keys=True,allow_nan=False):r for r in selected}.values())
        if len(selected)!=3 or {r.get('selection') for r in selected}!=set(CLASSES): # MUT completeness
            return reject('selection_completeness')
        selected.sort(key=lambda r:CLASSES.index(r['selection']))
        for row in selected:
            if row.get('rules')!=context['rules']: # MUT rules
                return reject('rules_mismatch')
            verdict=admit_selection([row],{**context,'selection':row['selection']})
            if verdict['status']!='ADMIT_SYNTHETIC_CONTRACT': # MUT selection_guard
                return reject(verdict['rule'],verdict['status'],selection=row['selection'])
            age=(decision-utc(row['observed_at'])).total_seconds()
            if not 0<=age<=POLICY['max_age_seconds']: # MUT freshness
                return reject('stale','ABSTAIN',selection=row['selection'],age_seconds=age)
        prices=odds_vector([r['price'] for r in selected],exhaustive=True).tolist()
        margin=devig(prices,POLICY['method'],exhaustive=True,underround=POLICY['underround'])
        if margin.probabilities is None:return reject(margin.status,'ABSTAIN',devig=asdict(margin))
        return {'status':'ADMIT','rule':None,'classes':list(CLASSES),'probabilities':list(margin.probabilities),
                'odds':prices,'devig':asdict(margin),'snapshot_id':next(iter(snapshots)),
                'captured_at':selected[0]['captured_at'],'source_authentication':'NOT_ESTABLISHED',
                'scope':'ENGINEERING_CONTRACT_ONLY'}
    except (KeyError,ValueError,TypeError,OverflowError):
        return reject('invalid_field_or_clock')
