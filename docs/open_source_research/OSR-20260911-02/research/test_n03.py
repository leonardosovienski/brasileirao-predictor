"""Synthetic adversarial tests AND true source-mutated function comparisons."""
import json,pathlib,copy,sqlite3,types,hashlib
import baseline_pit as b
import strict_pit as s
ROOT=pathlib.Path(__file__).resolve().parent.parent

def quote(**updates):
    row={'source':'SYNTH','source_match_id':'SYN-1','canonical_match_id':'OSR-SYN-1','mapping_version':b.MAPPING_VERSION,'home_id':'SYN-H','away_id':'SYN-A','kickoff_at':'2030-01-01T20:00:00Z','observed_at':'2030-01-01T17:00:00Z','published_at':'2030-01-01T17:01:00Z','available_at':'2030-01-01T17:02:00Z','captured_at':'2030-01-01T17:03:00Z','bookmaker':'SYN-BOOK','market':'1X2','selection':'1','period':'FT','line':None,'status':'ACTIVE','raw_odds':2.,'data_quality_status':'OK'}
    row.update(updates);return row

CTX={k:v for k,v in quote().items() if k in ['source','source_match_id','canonical_match_id','mapping_version','home_id','away_id','bookmaker','market','selection','period','line']}
CTX.update(predicted_at='2030-01-01T18:00:00Z',frozen_kickoff_at='2030-01-01T20:00:00Z')
cases=[]
def case(id,rows,expected,rule=None,context=None):
    cases.append({'id':id,'rows':rows,'context':context or CTX,'expected':expected,'expected_rule':rule})
case('valid',[quote()],'ADMIT_SYNTHETIC_CONTRACT')
case('late_publication',[quote(published_at='2030-01-01T18:01:00Z')],'REJECT','before_cutoff')
case('late_receipt',[quote(captured_at='2030-01-01T18:01:00Z')],'ABSTAIN','no_received_version')
case('future_revision_ignored',[quote(),quote(captured_at='2030-01-01T19:00:00Z',status='SUSPENDED')],'ADMIT_SYNTHETIC_CONTRACT')
case('revision_known_suspended',[quote(),quote(captured_at='2030-01-01T17:30:00Z',status='SUSPENDED')],'ABSTAIN','latest_status')
case('kickoff_rescheduled',[quote(kickoff_at='2030-01-02T20:00:00Z')],'REJECT','kickoff_frozen')
case('inverted_home_away',[quote(home_id='SYN-A',away_id='SYN-H')],'REJECT','identity')
case('conflicting_source_id',[quote(source_match_id='SYN-OTHER')],'REJECT','identity')
case('mapping_version',[quote(mapping_version='SYN-V2')],'REJECT','identity')
case('identical_duplicate',[quote(),quote()],'ADMIT_SYNTHETIC_CONTRACT')
case('conflicting_duplicate',[quote(),quote(raw_odds=3.)],'REJECT','conflict')
case('missing_publication',[quote(published_at=None)],'REJECT','required_clock')
case('missing_receipt',[quote(captured_at=None)],'REJECT','required_clock')
case('naive_timestamp',[quote(observed_at='2030-01-01T17:00:00')],'REJECT','required_clock')
case('clock_chain',[quote(available_at='2030-01-01T17:00:30Z')],'REJECT','clock_chain')
case('at_kickoff',[quote()], 'REJECT','decision_before_kickoff',{**CTX,'predicted_at':CTX['frozen_kickoff_at']})
case('same_instant_offset',[quote(published_at='2030-01-01T14:01:00-03:00')],'ADMIT_SYNTHETIC_CONTRACT')
case('simultaneous_other_fixture',[quote(source_match_id='SYN-2',canonical_match_id='OSR-SYN-2')],'ADMIT_SYNTHETIC_CONTRACT',context={**CTX,'source_match_id':'SYN-2','canonical_match_id':'OSR-SYN-2'})

def adapter_failures(fn):
    failed=[];observed=[]
    for c in cases:
        try:
            result=fn(copy.deepcopy(c['rows']),copy.deepcopy(c['context']))
            ok=result['status']==c['expected'] and (c['expected_rule'] is None or result['rule']==c['expected_rule'])
        except Exception as e:result={'error':type(e).__name__};ok=False
        observed.append({'id':c['id'],'expected':c['expected'],'expected_rule':c['expected_rule'],'observed':result,'pass':ok})
        if not ok:failed.append(c['id'])
    return failed,observed

failures,adapter_results=adapter_failures(s.admit_selection)
assert not failures,failures

def curate_result(module,row):
    conn=sqlite3.connect(':memory:');conn.executescript(module.SCHEMA)
    try:
        module.curate_odds(conn,row,canonical_match_id='OSR-SYN-1',batch_id='OSR-SYN-BATCH')
        return 'ACCEPT'
    except ValueError:return 'REJECT'
    finally:conn.close()

def closing(module,rows):
    try:
        result=module.choose_closing(rows,kickoff_at=quote()['kickoff_at'],bookmaker='SYN-BOOK',market='1X2',selection='1')
        return 'ABSTAIN' if result is None else 'ACCEPT'
    except ValueError:return 'REJECT'

def eval_rows(module,items):
    conn=sqlite3.connect(':memory:');conn.executescript(module.SCHEMA)
    try:
        for i,x in enumerate(items):
            conn.execute('INSERT INTO curated_matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('SYNTH',x.get('id','SYN-1'),x.get('canonical','OSR-SYN-1'),x.get('kickoff','2030-01-01T20:00:00+00:00'),x.get('received','2030-01-01T17:00:00+00:00'),'SYN-H','SYN-A',x.get('home','SYN-H'),'SYN-A',None,None,'SYN-MAP','EXACT','OK','SYN-BATCH',str(i),x.get('status','SCHEDULED')))
        conn.commit()
        return module.evaluation_view(conn,predicted_at=CTX['predicted_at'])
    finally:conn.close()

# Assertions correspond to the ACTUAL scoped contract, not a claim that it
# enforces the new stricter cutoff/identity contract by itself.
def baseline_tests(module):
    checks=[]
    def check(id,fn,expected):
        try:actual=fn();ok=actual==expected
        except ValueError:actual='REJECT';ok=expected=='REJECT'
        checks.append({'id':id,'expected':expected,'observed':actual,'pass':ok})
    check('pit_late_available',lambda:module.pit_eligible(available_at='2030-01-01T18:01:00Z',predicted_at=CTX['predicted_at'],kickoff_at=CTX['frozen_kickoff_at']),False)
    check('pit_equal_cutoff',lambda:module.pit_eligible(available_at=CTX['predicted_at'],predicted_at=CTX['predicted_at'],kickoff_at=CTX['frozen_kickoff_at']),True)
    check('pit_at_kickoff',lambda:module.pit_eligible(available_at=CTX['predicted_at'],predicted_at=CTX['frozen_kickoff_at'],kickoff_at=CTX['frozen_kickoff_at']),False)
    check('curate_valid',lambda:curate_result(module,quote()),'ACCEPT')
    check('curate_publication_after_capture',lambda:curate_result(module,quote(published_at='2030-01-01T17:04:00Z')),'REJECT')
    check('curate_available_after_capture',lambda:curate_result(module,quote(available_at='2030-01-01T17:04:00Z')),'REJECT')
    check('curate_observed_after_capture',lambda:curate_result(module,quote(observed_at='2030-01-01T17:04:00Z')),'REJECT')
    check('closing_suspended_latest',lambda:closing(module,[quote(),quote(captured_at='2030-01-01T17:30:00Z',status='SUSPENDED')]),'ABSTAIN')
    check('closing_conflicting_duplicates',lambda:closing(module,[quote(),quote(raw_odds=3.)]),'ABSTAIN')
    check('closing_identical_duplicates',lambda:closing(module,[quote(),quote()]),'ACCEPT')
    check('closing_mixed_source_id',lambda:closing(module,[quote(),quote(source_match_id='SYN-2')]),'REJECT')
    check('view_late_revision_ignored',lambda:len(eval_rows(module,[{}, {'received':'2030-01-01T19:00:00+00:00','status':'POSTPONED'}])),1)
    check('view_postponed_not_resurrected',lambda:len(eval_rows(module,[{}, {'received':'2030-01-01T17:30:00+00:00','status':'POSTPONED','kickoff':'2029-12-31T20:00:00+00:00'}])),0)
    check('view_tied_conflict',lambda:len(eval_rows(module,[{}, {'home':'SYN-CONFLICT'}])),'REJECT')
    check('view_simultaneous_events',lambda:len(eval_rows(module,[{}, {'id':'SYN-2','canonical':'OSR-SYN-2'}])),2)
    return checks

baseline_results=baseline_tests(b)
assert all(x['pass'] for x in baseline_results),baseline_results
gaps=[
 {'case':'curate_missing_published','observed':curate_result(b,quote(published_at=None)),'required_for_strict_study':'REJECT','interpretation':'curated schema allows null publication; not proof of predictive admission'},
 {'case':'curate_receipt_after_decision','observed':curate_result(b,quote(captured_at='2030-01-01T18:01:00Z')),'required_for_strict_study':'ABSTAIN','interpretation':'curate checks kickoff/capture, not study decision cutoff'},
 {'case':'curate_home_inversion','observed':curate_result(b,quote(home_id='SYN-A',away_id='SYN-H')),'required_for_strict_study':'REJECT','interpretation':'curate_odds does not verify these added identity fields against canonical mapping'},
 {'case':'closing_missing_published','observed':closing(b,[quote(published_at=None)]),'required_for_strict_study':'REJECT','interpretation':'last-observed-state utility has weaker completeness than strict study contract'}]

# Real source mutations; each must compile, import and execute. An invalid
# mutant is reported separately and never counted as killed.
mutations=[]
source=pathlib.Path(s.__file__).read_text(encoding='utf-8')
replacements=[
 ('M01','decision_before_kickoff','if not decision<kickoff:','if False:'),
 ('M02','cutoff_receipt','if utc(row.get(\'captured_at\'))>decision:continue','if False:continue'),
 ('M03','conflict',"if len({json.dumps(r,sort_keys=True,allow_nan=False) for r in latest_rows})>1:",'if False:'),
 ('M04','before_cutoff',"if not all(clocks[k]<=decision for k in ['observed_at','published_at','available_at','captured_at']):",'if False:'),
 ('M05','clock_chain',"if not clocks['observed_at']<=clocks['published_at']<=clocks['available_at']<=clocks['captured_at']:",'if False:'),
 ('M06','kickoff_frozen',"if clocks['kickoff_at']!=kickoff:",'if False:'),
 ('M07','identity',"if key not in row or key not in context or row[key]!=context[key]:",'if False:'),
 ('M08','latest_status',"if row.get('status')!='ACTIVE':",'if False:')]
for mid,rule,old,new in replacements:
    assert source.count(old)==1,(mid,old)
    altered=source.replace(old,new,1);namespace={}
    exec(compile(altered,'<'+mid+'>','exec'),namespace)
    failed,_=adapter_failures(namespace['admit_selection'])
    mutations.append({'id':mid,'target':'strict_pit.py','rule':rule,'replacement_from':old,'replacement_to':new,'source_sha256':hashlib.sha256(altered.encode()).hexdigest(),'compiled':True,'status':'KILLED' if failed else 'SURVIVED','failed_cases':failed})

base_source=pathlib.Path(b.__file__).read_text(encoding='utf-8')
base_mutants=[
 ('MB01','availability', 'return available <= predicted < kickoff','return predicted < kickoff'),
 ('MB02','publication', 'if published > captured:', 'if False:'),
 ('MB03','observed_clock', 'if observed > captured:', 'if False:'),
 ('MB04','latest_state', 'latest = max(captured for captured, _ in candidates)','latest = min(captured for captured, _ in candidates)'),
 ('MB05','tied_conflict', 'if len(signatures) != 1:','if False:'),
 ('MB06','identity', 'if len(identities) > 1:', 'if False:'),
 ('MB07','strict_kickoff','return available <= predicted < kickoff','return available <= predicted <= kickoff')]
for mid,rule,old,new in base_mutants:
    assert base_source.count(old)==1,(mid,old)
    altered=base_source.replace(old,new,1);namespace={}
    exec(compile(altered,'<'+mid+'>','exec'),namespace)
    checks=baseline_tests(types.SimpleNamespace(**namespace));failed=[x['id'] for x in checks if not x['pass']]
    mutations.append({'id':mid,'target':'references/baseline_pit.py','rule':rule,'replacement_from':old,'replacement_to':new,'source_sha256':hashlib.sha256(altered.encode()).hexdigest(),'compiled':True,'status':'KILLED' if failed else 'SURVIVED','failed_cases':failed})
out={'status':'PASS_WITH_SCOPE_LIMITS','fixtures':cases,'adversarial_results':adapter_results,'existing_contract_results':baseline_results,'existing_contract_scope_gaps':gaps,'mutations':mutations,'summary':{'adapter_cases':len(cases),'baseline_assertions':len(baseline_results),'mutants':len(mutations),'killed':sum(x['status']=='KILLED' for x in mutations),'survived':[x['id'] for x in mutations if x['status']=='SURVIVED'],'invalid_mutants':0},'uncovered':['source authenticity','complete fixture universe','cross-provider canonical mapping authenticity','dynamic timezone/kickoff external revisions','whole-market selection completeness and common vintage','operational collectors/cache and .NET worker','mutation of all SQL/window predicates; chosen mutants are not exhaustive']}
with (ROOT/'evidence/N03.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2,allow_nan=False)
print(json.dumps(out['summary']))
