import json, copy, inspect, hashlib
from pathlib import Path
import joint_market as jm
import workflow as wf
import artifacts

ROOT=Path(__file__).resolve().parent.parent
before=artifacts.read_json(ROOT/'examples/before.json')
valid=before['fixtures'][0]
cases=[]
def case(name,edit,status):
    f=copy.deepcopy(valid);edit(f);cases.append((name,f,status))
case('valid',lambda f:None,'ADMIT')
case('permuted',lambda f:f['quotes'].reverse(),'ADMIT')
case('exact_retry',lambda f:f['quotes'].append(copy.deepcopy(f['quotes'][0])),'ADMIT')
case('missing',lambda f:f['quotes'].pop(),'REJECT')
case('conflicting_duplicate',lambda f:f['quotes'].append({**f['quotes'][0],'price':2.2}),'REJECT')
case('mixed_fixture',lambda f:f['quotes'][1].update(canonical_match_id='SYN-other'),'REJECT')
case('mixed_period',lambda f:f['quotes'][1].update(period='H1'),'REJECT')
case('mixed_rules',lambda f:f['quotes'][1].update(rules='QUALIFICATION'),'REJECT')
case('mixed_book',lambda f:f['quotes'][1].update(bookmaker='SYN-other'),'REJECT')
case('mixed_snapshot',lambda f:f['quotes'][1].update(snapshot_id='other'),'REJECT')
case('mando',lambda f:f['quotes'][1].update(home_id='SYN-away',away_id='SYN-home'),'REJECT')
case('suspended',lambda f:f['quotes'][1].update(status='SUSPENDED'),'ABSTAIN')
case('stale',lambda f:f['quotes'][1].update(observed_at='2030-01-01T10:54:59Z'),'ABSTAIN')
case('missing_clock',lambda f:f['quotes'][1].pop('published_at'),'REJECT')
case('future_publication',lambda f:f['quotes'][1].update(published_at='2030-01-01T11:00:01Z'),'REJECT')
case('inconsistent_clock',lambda f:f['quotes'][1].update(available_at='2030-01-01T10:58:01Z'),'REJECT')
case('invalid_price',lambda f:f['quotes'][1].update(price=True),'REJECT')
case('underround',lambda f:[r.update(price=10.) for r in f['quotes']],'ABSTAIN')
case('late_revision_ignored',lambda f:f['quotes'].extend([{**r,'captured_at':'2030-01-01T11:01:00Z','snapshot_id':'late','status':'SUSPENDED'} for r in f['quotes']]),'ADMIT')
case('new_incomplete_no_resurrection',lambda f:f['quotes'].append({**f['quotes'][0],'captured_at':'2030-01-01T10:59:30Z','snapshot_id':'new'}),'REJECT')
case('latest_suspension_no_resurrection',lambda f:f['quotes'].extend([{**r,'captured_at':'2030-01-01T10:59:30Z','snapshot_id':'new','status':'SUSPENDED'} for r in f['quotes']]),'ABSTAIN')
results=[]
for name,f,status in cases:
    r=jm.admit_market(f['quotes'],f['context']);assert r['status']==status,(name,r)
    if status=='ADMIT':
        assert len(r['probabilities'])==3 and abs(sum(r['probabilities'])-1)<1e-12
        assert max(abs(p-q) for p,q in zip(r['probabilities'],[.48,.30,.22]))<1e-12
    else:assert r['probabilities'] is None
    results.append({'name':name,'expected':status,'observed':r,'input':f})
source=inspect.getsource(jm)
mutants=[]
for name,old,new in [
 ('MM1_snapshot',"if len(snapshots)!=1 or not all(isinstance(v,str) and v.strip() for v in snapshots): # MUT snapshot","if False: # MUT snapshot"),
 ('MM2_completeness',"if len(selected)!=3 or {r.get('selection') for r in selected}!=set(CLASSES): # MUT completeness","if False: # MUT completeness"),
 ('MM3_rules',"if row.get('rules')!=context['rules']: # MUT rules","if False: # MUT rules"),
 ('MM4_selection',"if verdict['status']!='ADMIT_SYNTHETIC_CONTRACT': # MUT selection_guard","if False: # MUT selection_guard"),
 ('MM5_freshness',"if not 0<=age<=POLICY['max_age_seconds']: # MUT freshness","if False: # MUT freshness")]:
    assert source.count(old)==1
    modified=source.replace(old,new);scope={};exec(compile(modified,'<'+name+'>','exec'),scope)
    unsafe=[];false_refusals=[];other=[]
    for cname,f,status in cases:
        try:r=scope['admit_market'](f['quotes'],f['context']);actual=r['status']
        except Exception as e:actual='EXCEPTION:'+type(e).__name__
        if actual=='ADMIT' and status!='ADMIT':unsafe.append(cname)
        elif actual!='ADMIT' and status=='ADMIT':false_refusals.append(cname)
        elif actual!=status:other.append(cname)
    assert unsafe,(name,'must witness unsafe admission; diagnostic-only kills do not pass')
    mutants.append({'id':name,'sha256':hashlib.sha256(modified.encode()).hexdigest(),'status':'KILLED',
                    'unsafe_admissions':unsafe,'false_refusals':false_refusals,'other_status_changes':other})
# Actual consumer, not a parallel implementation of the math.
a=wf.evaluate(before)
assert a['coverage']['total']==3 and a['coverage']['admitted']==1 and a['coverage']['scored']==1
assert a['records'][1]['probabilities'] is None and 'score' not in a['records'][1]
assert abs(a['market_scores']['log_loss_mean']-(-__import__('math').log(.48)))<1e-12
invalid=[]
for raw in ['{"x":1,"x":2}','{"x":NaN}','{"x":1e999}']:
    try:artifacts._decode(raw)
    except ValueError:invalid.append(raw)
    else:raise AssertionError('parser accepted invalid JSON')
for edit in [lambda x:x.update(purpose='PREDICTIVE'),lambda x:x['fixtures'].append(x['fixtures'][0])]:
    f=copy.deepcopy(before);edit(f)
    try:wf.evaluate(f)
    except ValueError:pass
    else:raise AssertionError('invalid consumer input')
result={'status':'PASS','joint_cases':results,'mutants':mutants,'workflow_coverage':a['coverage'],
        'json_invalid_rejected':invalid,'limits':['synthetic source identity not authenticated','not all selection-level predicates mutated','receipt-based estimand only','no operational consumer imported']}
(ROOT/'evidence/market-tests.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({'status':'PASS','cases':len(cases),'mutants_with_unsafe_witnesses':len(mutants),'coverage':a['coverage']}))
