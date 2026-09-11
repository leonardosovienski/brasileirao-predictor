import json,pathlib,math,dataclasses
import numpy as np
from strict_math import devig,checked_engine,score_1x2,calibration_bins,probabilities
from baseline_shin import shin_probabilities
from baseline_power import power_probabilities
from baseline_scores import brier_score_multiclass,log_loss_matrix
from pbmethods import _power,_shin
ROOT=pathlib.Path(__file__).resolve().parent.parent
P=json.loads((ROOT/'PROTOCOL.json').read_text())['N02']
comparisons=[]
for odds in P['odds_cases']:
    for method,base,external in [('power',power_probabilities,_power),('shin',shin_probabilities,_shin)]:
        got=devig(odds,method,exhaustive=True)
        ext=checked_engine(odds,lambda x:(external(x).probabilities,True),exhaustive=True)
        local=list(map(float,base(odds)[0]))
        row={'odds':odds,'method':method,'candidate':dataclasses.asdict(got),'baseline':local,'external':ext}
        if got.status=='OK':
            assert got.probabilities is not None
            row['baseline_difference']=float(np.max(np.abs(np.asarray(got.probabilities)-local)))
            assert row['baseline_difference']<=1e-8
            if ext['status']=='OK':
                row['external_difference']=float(np.max(np.abs(np.asarray(got.probabilities)-ext['probabilities'])))
                assert row['external_difference']<=1e-8
        elif got.regime=='UNDERROUND':
            assert got.probabilities is None
            explicit=devig(odds,method,exhaustive=True,underround='proportional')
            q=1/np.array(odds);assert np.max(np.abs(np.array(explicit.probabilities)-q/q.sum()))<=1e-12
            row['explicit_scenario']=dataclasses.asdict(explicit)
            row['comparison']='NOT_DIRECTLY_COMPARABLE: external power may solve k<1; local uses proportional'
        else:assert got.status=='FAIR_NORMALIZATION'
        comparisons.append(row)
bad_inputs=[[float('nan'),2],[float('inf'),2],[0,2],[-1,2],[1,2],[True,2],['2',3],[2],[]]
input_checks=[]
for odds in bad_inputs:
    try:devig(odds,'shin',exhaustive=True)
    except ValueError:input_checks.append({'input_repr':repr(odds),'rejected':True})
    else:raise AssertionError(odds)
try:devig([2,3],'power',exhaustive=False)
except ValueError:input_checks.append({'input_repr':'nonexhaustive','rejected':True})
else:raise AssertionError('contract')
engines=[('negative',lambda x:([-.1,.5,.6],True)),('nan',lambda x:([float('nan'),.5,.5],True)),('sum_wrong',lambda x:([.2,.2,.2],True)),('wrong_length',lambda x:([.5,.5],True)),('not_converged',lambda x:([.3,.4,.3],False))]
def broken(x):raise RuntimeError('synthetic solver failure')
engines.append(('exception',broken));engine_checks=[]
for name,engine in engines:
    result=checked_engine([2,3,4],engine,exhaustive=True)
    assert result['probabilities'] is None and result['status']!='OK'
    engine_checks.append({'case':name,**result})
convergence=devig([2.7,2.3,4.4],'shin',exhaustive=True,maxiter=1)
assert convergence.status=='CONVERGENCE_FAILED' and convergence.probabilities is None
# Exact known predictions, followed by nonuniform manual formula and differential.
cases=[('perfect',[[1.,0.,0.]],['1'],0.,0.),('uniform',[[1/3]*3],['X'],2/3,math.log(3)),('wrong',[[1.,0.,0.]],['2'],2.,-math.log(1e-12)),('mixed',[[.2,.5,.3],[.6,.1,.3]],['X','2'],None,None)]
scores=[]
for name,pred,labels,brier,loss in cases:
    got=score_1x2(pred,labels)
    if brier is not None:
        assert abs(got['brier_mean']-brier)<=1e-12 and abs(got['log_loss_mean']-loss)<=1e-12
    # Put the three outcome classes in a 2x2 tensor, fourth class zero.
    # This is a formula/axis comparison, not an assertion that outcomes are scores.
    tensor=np.zeros((len(pred),2,2));onehot=np.zeros_like(tensor)
    for i,(p,l) in enumerate(zip(pred,labels)):
        tensor[i].flat[:3]=p;onehot[i].flat[['1','X','2'].index(l)]=1
    b=brier_score_multiclass(tensor,onehot);l=log_loss_matrix(tensor,onehot)
    assert abs(got['brier_mean']-b)<=1e-12 and abs(got['log_loss_mean']-l)<=1e-12
    scores.append({'case':name,'candidate':got,'baseline_tensor_brier':b,'baseline_tensor_log_loss':l})
invalid_scores=[]
for case,p,l,kw in [('negative',[[-.1,.5,.6]],['1'],{}),('nonfinite',[[float('inf'),0,0]],['1'],{}),('sum',[[.5,.2,.2]],['1'],{}),('class_order',[[.3,.4,.3]],['1'],{'classes':['1','2','X']}),('invalid_label',[[.3,.4,.3]],['home'],{}),('empty',[],[],{})]:
    try:score_1x2(p,l,**kw)
    except ValueError:invalid_scores.append({'case':case,'rejected':True})
    else:raise AssertionError(case)
bins=calibration_bins([[1.,0,0],[0,.5,.5],[0,0,1.]],['1','X','2'])
assert bins['bins']['1'][4]['count']==1 and bins['bins']['1'][4]['observed_frequency']==1
assert bins['bins']['1'][1]['count']==0 and bins['bins']['1'][1]['observed_frequency'] is None
assert all(sum(b['count'] for b in v)==3 for v in bins['bins'].values())
out={'status':'PASS','margin_comparisons':comparisons,'invalid_inputs':input_checks,'invalid_external_outputs':engine_checks,'forced_nonconvergence':dataclasses.asdict(convergence),'scores':scores,'invalid_scores':invalid_scores,'calibration_formula_fixture':bins,'claim':'mathematical contracts only; no empirical calibration of real model'}
with (ROOT/'evidence/N02.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2,allow_nan=False)
print(json.dumps({'status':'PASS','margin_pairs':len(comparisons),'rejected_bad_inputs':len(input_checks),'rejected_bad_outputs':len(engine_checks),'score_cases':len(scores),'score_contract_rejections':len(invalid_scores)}))
