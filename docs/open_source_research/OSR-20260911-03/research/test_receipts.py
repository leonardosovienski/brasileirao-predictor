"""Focused consumer failure paths, no original result discovery."""
import json,copy
from pathlib import Path
import workflow as wf
import artifacts
ROOT=Path(__file__).resolve().parent.parent
passed=[]
def rejects(name,fn):
    try:fn()
    except (ValueError,FileExistsError):passed.append(name)
    else:raise AssertionError(name)
rejects('overwrite',lambda:wf.run(ROOT/'examples/before.json',ROOT/'evidence/demo_before'))
rejects('outside_explicit_development_roots',lambda:wf.guarded(ROOT.parents[2]/'reports'))
a=artifacts.read_json(ROOT/'examples/after.json')
a['fixtures'][1].pop('model_probabilities')
v=wf.evaluate(a)
assert v['coverage']['scored']==2 and v['model_scored_count']==1
assert v['market_scores_on_model_panel']['log_loss_mean']==v['records'][0]['score']['log_loss_mean']
passed.append('model_scores_have_paired_market_panel')
payload=artifacts.read_json(ROOT/'examples/before.json')
payload['fixtures'].pop()
file=ROOT/'evidence/smaller-universe.json';file.write_text(json.dumps(payload),encoding='utf-8')
wf.run(file,ROOT/'evidence/different_universe')
rejects('comparison_different_universe',lambda:wf.compare(ROOT/'evidence/demo_before',ROOT/'evidence/different_universe'))
directory=ROOT/'evidence/tampered_copy';directory.mkdir()
for name in ['manifest.json','diagnostic.json']:
    (directory/name).write_bytes((ROOT/'evidence/demo_before'/name).read_bytes())
(directory/'diagnostic.json').write_text('{}',encoding='utf-8')
rejects('corrupt_artifact_hash',lambda:wf.load_verified(directory))
policy_copy=ROOT/'evidence/different_policy';policy_copy.mkdir()
d,m=wf.load_verified(ROOT/'evidence/demo_before');d['policy']['max_age_seconds']=301
content=artifacts._json_bytes(d);m['artifacts']['diagnostic.json']=artifacts._digest(content)
(policy_copy/'diagnostic.json').write_bytes(content);(policy_copy/'manifest.json').write_bytes(artifacts._json_bytes(m))
rejects('comparison_different_policy',lambda:wf.compare(ROOT/'evidence/demo_before',policy_copy))
# Existing writer refuses changed input after computation and records FAILED.
rejects('input_changed_before_publish',lambda:artifacts.write_artifacts(ROOT/'evidence/failed_input_change',
    inputs={'fixture':file},artifacts={'diagnostic.json':{}},metadata={'input_hashes_used':{'fixture':'0'*64}}))
assert not (ROOT/'evidence/failed_input_change/manifest.json').exists()
assert artifacts.read_json(ROOT/'evidence/failed_input_change/failure.json')['status']=='FAILED'
result={'status':'PASS','checks':passed,'failure_files_are_intentional_test_artifacts':True}
(ROOT/'evidence/receipt-tests.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
