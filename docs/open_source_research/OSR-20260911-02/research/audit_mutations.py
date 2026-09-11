"""Distinguish changes in admission from changes only in rejection reason."""
import pathlib,json,hashlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
record=json.loads((ROOT/'evidence/N03.json').read_text())
source=(ROOT/'research/strict_pit.py').read_text(encoding='utf-8')
rows=[]
for m in record['mutations']:
    if m['target']!='strict_pit.py':continue
    altered=source.replace(m['replacement_from'],m['replacement_to'],1)
    assert hashlib.sha256(altered.encode()).hexdigest()==m['source_sha256']
    ns={};exec(compile(altered,'<'+m['id']+'>','exec'),ns)
    status_changes=[];reason_only=[];unsafe_admissions=[]
    for c in record['fixtures']:
        try:got=ns['admit_selection'](c['rows'],c['context'])
        except ValueError:got={'status':'INPUT_EXCEPTION','rule':'timestamp'}
        if got['status']!=c['expected']:
            status_changes.append(c['id'])
            if got['status']=='ADMIT_SYNTHETIC_CONTRACT':unsafe_admissions.append(c['id'])
        elif c['expected_rule'] is not None and got['rule']!=c['expected_rule']:reason_only.append(c['id'])
    rows.append({'id':m['id'],'status_changes':status_changes,'reason_only':reason_only,'unsafe_admissions':unsafe_admissions,'classification':'LOSS_OF_ADMISSION_GUARD_DETECTED' if unsafe_admissions else 'VALID_VINTAGE_OR_STATUS_BEHAVIOR_CHANGED' if status_changes else 'REASON_ONLY_NO_UNSAFE_ADMISSION_WITNESS' if reason_only else 'SURVIVED'})
out={'purpose':'semantic refinement of same mutant experiment, not additional independent tests','rows':rows,'note':'M04 cutoff guard is redundant for exclusion given received<=cutoff and full ordered clock chain; its deletion changes the diagnostic reason in the witness, not acceptance. M02 changes vintage handling and refusal status without an unsafe acceptance in the supplied witnesses.'}
with (ROOT/'evidence/N03-mutation-audit.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print(json.dumps(rows))
