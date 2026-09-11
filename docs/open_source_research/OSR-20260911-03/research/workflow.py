"""Small offline consumer of joint admission and the existing artifact interface.

No discovery, service, model fitting, network, operational config or DB imports.
CLI inputs are explicit development fixtures in this run's examples/evidence.
"""
import argparse, hashlib, json, sys, time
from pathlib import Path
from collections import Counter
import artifacts
from joint_market import POLICY, admit_market
from strict_math import score_1x2, calibration_bins, probabilities

ROOT=Path(__file__).resolve().parent.parent
artifacts.PACKAGE_ROOT=Path(__file__).resolve().parent
artifacts.REPOSITORY_ROOT=ROOT.parents[2]

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()

def evaluate(payload):
    if payload.get('purpose')!='ENGINEERING_SYNTHETIC':raise ValueError('this consumer is scoped to development fixtures; no real study admission')
    fixtures=payload.get('fixtures')
    if not isinstance(fixtures,list) or not fixtures:raise ValueError('nonempty fixture universe required')
    ids=[r['context']['canonical_match_id'] for r in fixtures]
    if any(not isinstance(x,str) or not x.startswith('SYN-') for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('unique SYN fixture IDs required')
    records=[]; ps=[]; ys=[]; model_ps=[]; model_ys=[]; paired_market=[]
    for fixture in fixtures:
        verdict=admit_market(fixture['quotes'],fixture['context'])
        row={'fixture_id':fixture['context']['canonical_match_id'],**verdict}
        if verdict['status']=='ADMIT':
            if 'model_probabilities' in fixture:
                model=probabilities(fixture['model_probabilities'],3).tolist()
                row['model_probabilities']=model
                row['model_minus_market']=[p-q for p,q in zip(model,verdict['probabilities'])]
            if 'label' in fixture:
                label=fixture['label']; score=score_1x2([verdict['probabilities']],[label]);row['score']=score
                ps.append(verdict['probabilities']);ys.append(label)
                if 'model_probabilities' in row:
                    model_ps.append(row['model_probabilities']);model_ys.append(label);paired_market.append(verdict['probabilities'])
        records.append(row)
    counts=Counter(r['status'] for r in records)
    return {'schema':'offline-market-diagnostic/1','purpose':payload['purpose'],'policy':POLICY,
            'universe':sorted(ids),'universe_sha256':digest(sorted(ids)),
            'coverage':{'total':len(ids),'admitted':counts['ADMIT'],'fraction':counts['ADMIT']/len(ids),
                        'scored':len(ys),'by_status':dict(counts),'by_reason':dict(Counter(r['rule'] for r in records if r['rule']))},
            'records':records,'market_scores':score_1x2(ps,ys) if ys else None,
            'model_scores':score_1x2(model_ps,model_ys) if model_ys else None,
            'market_scores_on_model_panel':score_1x2(paired_market,model_ys) if model_ys else None,
            'model_scored_count':len(model_ys),
            'calibration':calibration_bins(ps,ys) if ys else None,
            'claims':{'ENGINEERING_STATUS':'OFFLINE_CONSUMER','DATA_ADMISSIBILITY':'SYNTHETIC_ONLY',
                      'PREDICTIVE_EVIDENCE':'NOT_EVALUATED','ECONOMIC_EVIDENCE':'NOT_EVALUATED'}}

def guarded(path):
    p=Path(path).resolve()
    if not any(p.is_relative_to(ROOT/k) for k in ['examples','evidence']):
        raise ValueError('explicit local development input only; protected studies are not inputs')
    return p

def run(input_path,output_path):
    path=guarded(input_path); output=Path(output_path).resolve()
    if not output.is_relative_to(ROOT/'evidence'):raise ValueError('output must be a new directory under evidence')
    start=time.perf_counter();payload,h=artifacts.read_hashed(path,jsonl=False)
    result=evaluate(payload)
    return artifacts.write_artifacts(output,inputs={'fixture':path},artifacts={'diagnostic.json':result},
        metadata={'input_hashes_used':{'fixture':h},'purpose':payload['purpose'],'policy_sha256':digest(POLICY),
                  'elapsed_compute_seconds':time.perf_counter()-start,'python':sys.version,'command':sys.argv,
                  'scope':'research-only, no source authentication or predictive/economic test'})

def load_verified(directory):
    directory=guarded(directory)
    manifest=artifacts.read_json(directory/'manifest.json')
    if manifest.get('status')!='COMPLETE':raise ValueError('incomplete run')
    value,h=artifacts.read_hashed(directory/'diagnostic.json',jsonl=False)
    if h!=manifest['artifacts']['diagnostic.json']['sha256']:raise ValueError('artifact hash mismatch')
    return value,manifest

def compare(left,right):
    a,ma=load_verified(left);b,mb=load_verified(right)
    if a['universe']!=b['universe'] or a['policy']!=b['policy']:raise ValueError('NOT_DIRECTLY_COMPARABLE: universe/policy differ')
    changes=[]
    rb={r['fixture_id']:r for r in b['records']}
    for x in a['records']:
        y=rb[x['fixture_id']]
        delta=[v-u for u,v in zip(x['probabilities'],y['probabilities'])] if x['probabilities'] is not None and y['probabilities'] is not None else None
        changes.append({'fixture_id':x['fixture_id'],'before_status':x['status'],'after_status':y['status'],
                        'before_reason':x['rule'],'after_reason':y['rule'],'probability_delta':delta,
                        'snapshot_changed':x.get('snapshot_id')!=y.get('snapshot_id')})
    return {'status':'DIAGNOSTIC_COMPARISON','changes':changes,'before_coverage':a['coverage'],'after_coverage':b['coverage'],
            'input_changed':ma['inputs']['fixture']['sha256']!=mb['inputs']['fixture']['sha256'],
            'code_changed':ma['source_code']!=mb['source_code'],
            'warning':'Probability changes are observations, not causal attribution. Different coverage has no paired performance claim.'}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    r=sub.add_parser('run');r.add_argument('input');r.add_argument('output')
    c=sub.add_parser('compare');c.add_argument('left');c.add_argument('right')
    a=p.parse_args(argv)
    result=run(a.input,a.output) if a.action=='run' else compare(a.left,a.right)
    print(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2))
    return result

if __name__=='__main__':main()
