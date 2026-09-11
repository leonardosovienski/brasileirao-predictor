import json,pathlib,time,itertools,math,statistics
import numpy as np
from scipy.stats import nbinom
import market_pricer as mp
from baseline_goal import _score_grid
from adaptive_goals import adaptive_grid,mass_diagnostic,SupportLimitError
ROOT=pathlib.Path(__file__).resolve().parent.parent
P=json.loads((ROOT/'PROTOCOL.json').read_text())['N01']

def market_vector(g):
    out={}
    def add(prefix,v):
        if isinstance(v,dict):
            for k,x in v.items():add(prefix+'/'+str(k),x)
        else:out[prefix]=float(v)
    add('1X2',mp.result_1x2(g));add('DC',mp.double_chance(g));add('BTTS',mp.both_teams_to_score(g));add('DNB',mp.draw_no_bet(g))
    for line in [.5,2,2.5,5.5]:add('OU'+str(line),mp.over_under(g,line))
    for line in [-1.25,0,.75]:add('AH'+str(line),mp.asian_handicap(g,line))
    add('0-0',mp.exact_score(g,0,0));add('1-1',mp.exact_score(g,1,1))
    return out

def reference(params):
    h,a,alpha,rho=params;r=1/alpha
    ph=r/(r+h);pa=r/(r+a)
    # Independent four-cell construction; tail bound certified for THIS grid.
    correction=0.
    for i,j,f in [(0,0,1-h*a*rho),(0,1,1+h*rho),(1,0,1+a*rho),(1,1,1-rho)]:
        correction+=float(nbinom.pmf(i,r,ph)*nbinom.pmf(j,r,pa)*(f-1))
    z=1+correction;k=64
    while True:
        sfh=float(nbinom.sf(k,r,ph));sfa=float(nbinom.sf(k,r,pa));tail=(sfh+sfa-sfh*sfa)/z
        if tail<=P['reference_tail_tolerance']:break
        if k>=P['reference_max_goals']:raise AssertionError('reference tail uncertified')
        k=min(k*2,P['reference_max_goals'])
    v=np.arange(k+1);raw=np.outer(nbinom.pmf(v,r,ph),nbinom.pmf(v,r,pa))
    raw[0,0]*=1-h*a*rho;raw[0,1]*=1+h*rho;raw[1,0]*=1+a*rho;raw[1,1]*=1-rho
    assert abs(float(raw.sum())/z-(1-tail))<=1e-10
    return raw/raw.sum(),{'max_goals':k,'omitted_mass':tail,'Z':z}

cases=list(P['reproduce_first'])
for h,a,alpha,fraction in itertools.product(P['grid_mu'],P['grid_mu'],P['grid_alpha'],P['rho_fractions_of_open_bounds']):
    lower=max(-1/h,-1/a);upper=min(1/(h*a),1)
    rho=(-fraction*lower) if fraction<0 else fraction*upper
    cases.append([h,a,alpha,rho])
rows=[]
for params in cases:
    t=time.perf_counter();base=_score_grid(*params,12);baseline_seconds=time.perf_counter()-t
    t=time.perf_counter();cand=adaptive_grid(*params,mass_tolerance=P['mass_tolerance'],max_goals=P['candidate_max_goals']);candidate_seconds=time.perf_counter()-t
    ref,refdiag=reference(params);cm=market_vector(cand.grid);rm=market_vector(ref);bm=market_vector(base)
    error=max(abs(cm[k]-rm[k]) for k in cm);base_error=max(abs(bm[k]-rm[k]) for k in bm)
    reverse=adaptive_grid(params[1],params[0],*params[2:])
    symmetry=float(np.max(np.abs(cand.grid-reverse.grid.T)))
    assert cand.diagnostic['omitted_mass']<=P['mass_tolerance']
    assert error<=P['market_abs_error_tolerance']
    assert np.isfinite(cand.grid).all() and cand.grid.min()>=0 and abs(cand.grid.sum()-1)<=1e-12
    assert symmetry<=P['normalization_symmetry_tolerance']
    k=cand.diagnostic['max_goals']
    assert k==1 or mass_diagnostic(*params,k-1)['omitted_mass']>P['mass_tolerance']
    one=mp.result_1x2(cand.grid);ah=mp.asian_handicap(cand.grid,0)
    assert abs(ah['push']-one['X'])<=1e-12 and abs(ah['win']-one['1'])<=1e-12
    for line in [0,2,2.5]:assert abs(sum(mp.over_under(cand.grid,line).values())-1)<=1e-12
    revah=mp.asian_handicap(reverse.grid,1.25);ah=mp.asian_handicap(cand.grid,-1.25)
    assert abs(revah['win']-ah['lose'])<=1e-12
    rows.append({'params':params,'baseline_omitted_mass':mass_diagnostic(*params,12)['omitted_mass'],'candidate':cand.diagnostic,'reference':refdiag,'baseline_max_market_error':base_error,'candidate_max_market_error':error,'transpose_error':symmetry,'baseline_seconds':baseline_seconds,'candidate_seconds':candidate_seconds})
invalid=[(float('nan'),1,.1,0),(1,float('inf'),.1,0),(True,1,.1,0),('1',1,.1,0),(0,1,.1,0),(.049,1,.1,0),(11,1,.1,0),(1,1,0,0),(1,1,2.1,0),(1,1,.1,1),(1,1,.1,-1)]
invalid_results=[]
for args in invalid:
    try:adaptive_grid(*args)
    except ValueError:invalid_results.append({'input_repr':repr(args),'rejected':True})
    else:raise AssertionError(('invalid input accepted',args))
for kwargs in [{'max_goals':True},{'max_goals':2.5},{'max_goals':1025},{'mass_tolerance':float('nan')},{'mass_tolerance':0}]:
    try:adaptive_grid(1,1,.1,0,**kwargs)
    except ValueError:invalid_results.append({'input_repr':repr(kwargs),'rejected':True})
    else:raise AssertionError(kwargs)
try:adaptive_grid(10,10,2,0,max_goals=2)
except SupportLimitError as e:limit=e.diagnostic
else:raise AssertionError('resource limit must fail')
out={'status':'PASS','cases':rows,'invalid_inputs':invalid_results,'support_limit':limit,'summary':{'case_count':len(rows),'maximum_market_error':max(r['candidate_max_market_error'] for r in rows),'maximum_candidate_tail':max(r['candidate']['omitted_mass'] for r in rows),'support_min':min(r['candidate']['max_goals'] for r in rows),'support_max':max(r['candidate']['max_goals'] for r in rows),'maximum_reference_tail':max(r['reference']['omitted_mass'] for r in rows),'median_baseline_seconds':statistics.median(r['baseline_seconds'] for r in rows),'median_candidate_seconds':statistics.median(r['candidate_seconds'] for r in rows)}}
with (ROOT/'evidence/N01.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2,allow_nan=False)
print(json.dumps(out['summary']))
