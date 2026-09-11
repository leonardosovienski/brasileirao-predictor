import json,time,statistics,itertools
from pathlib import Path
import numpy as np
from scipy.stats import nbinom
import fast_goals as fast
import previous_goals as old
from baseline_goal import _score_grid
ROOT=Path(__file__).resolve().parent.parent

def stats(g):
    i,j=np.indices(g.shape);h=float(g[i>j].sum());a=float(g[i<j].sum());d=float(np.trace(g))
    return np.array([h,d,a,float(g[(i>0)&(j>0)].sum()),float(g[i+j>2.5].sum()),float(g[i+j>5.5].sum()),float(g[0,0])])

def reference(h,a,alpha,rho):
    r=1/alpha;p=r/(r+h);q=r/(r+a)
    hp=nbinom.pmf([0,1],r,p);ap=nbinom.pmf([0,1],r,q)
    f=np.array([1-h*a*rho,1+h*rho,1+a*rho,1-rho]);z=1+float(np.dot(np.outer(hp,ap).ravel(),f-1))
    k=64
    while True:
        sh=float(nbinom.sf(k,r,p));sa=float(nbinom.sf(k,r,q));tail=(sh+sa-sh*sa)/z
        if tail<=1e-12:break
        if k==2048:raise RuntimeError('reference limit')
        k=min(k*2,2048)
    grid=_score_grid(h,a,alpha,rho,k)
    return grid,tail,k

rows=[]
for (h,a),alpha,fraction in itertools.product([(1e-4,2e-4),(.05,.1),(.2,1),(1.4,1.1),(5,4),(10,.1),(100,80)],[1e-4,.01,.5,3],[-.5,0,.5]):
    low=max(-1/h,-1/a);high=min(1,1/(h*a));rho=abs(fraction)*(low if fraction<0 else high)
    try:c=fast.adaptive_grid(h,a,alpha,rho,max_goals=1024)
    except fast.SupportLimitError as e:
        rows.append({'params':[h,a,alpha,rho],'status':'SUPPORT_LIMIT','diagnostic':e.diagnostic});continue
    ref,rt,rk=reference(h,a,alpha,rho);s=stats(c.grid);rs=stats(ref)
    err=float(np.max(abs(s-rs)));assert err<=1.0001e-6
    assert abs(c.grid.sum()-1)<1e-12 and np.all(c.grid>=0)
    inv=fast.adaptive_grid(a,h,alpha,rho,max_goals=1024);assert np.max(abs(inv.grid.T-c.grid))<1e-12
    cond=s[0]+s[2];rcond=rs[0]+rs[2]
    conditional_error=abs(s[0]/cond-rs[0]/rcond)
    bound=min(1,2*(c.diagnostic['omitted_mass']+rt)/rcond)
    assert conditional_error<=bound+1e-12
    rows.append({'params':[h,a,alpha,rho],'status':'PASS','diagnostic':c.diagnostic,'market_error':err,
                 'reference_tail':rt,'reference_support':rk,'conditional_denominator':rcond,
                 'conditional_error':conditional_error,'conditional_bound':bound})
cost=[]
for params in [(1.4,1.1,.1,-.05),(2.5,2,.5,-.05),(5,4,1,-.02)]:
    old.adaptive_grid(*params);fast.adaptive_grid(*params)
    ot=[];nt=[]
    for repeat in range(3):
        for label,fn,values in [('old',old.adaptive_grid,ot),('new',fast.adaptive_grid,nt)][::1 if repeat%2==0 else -1]:
            t=time.perf_counter();c=fn(*params);values.append(time.perf_counter()-t)
    o=old.adaptive_grid(*params);n=fast.adaptive_grid(*params)
    assert np.max(abs(o.grid-n.grid))<1e-12 and o.diagnostic['max_goals']==n.diagnostic['max_goals']
    cost.append({'params':params,'old_seconds':ot,'new_seconds':nt,'median_ratio':statistics.median(ot)/statistics.median(nt)})
invalid=[]
for params in [(0,1,.1,0),(1,1,0,0),(1,1,3.01,0),(1,1,.1,1),(True,1,.1,0),(1e-30,1,.1,0),(float('inf'),1,.1,0)]:
    try:fast.adaptive_grid(*params)
    except ValueError:invalid.append(repr(params))
    else:raise AssertionError(params)
try:fast.adaptive_grid(1e6,1e6,3,0,max_goals=2)
except fast.SupportLimitError as e:forced=e.diagnostic
else:raise AssertionError('support not rejected')
passed=[r for r in rows if r['status']=='PASS']
summary={'cases':len(rows),'passed':len(passed),'support_failures':len(rows)-len(passed),
         'max_market_error':max(r['market_error'] for r in passed),'max_conditional_error':max(r['conditional_error'] for r in passed),
         'median_speed_ratio':statistics.median(r['median_ratio'] for r in cost),'official_latency_budget':'UNKNOWN'}
out={'status':'PASS','summary':summary,'cases':rows,'cost':cost,'invalid':invalid,'forced_support_failure':forced}
(ROOT/'evidence/goals-tests.json').write_text(json.dumps(out,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps(summary))
