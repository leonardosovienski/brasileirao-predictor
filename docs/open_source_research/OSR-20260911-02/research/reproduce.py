import json,pathlib,math,os,sys,socket,subprocess,sqlite3
import numpy as np
import scipy
from scipy.stats import nbinom
from baseline_goal import _score_grid
ROOT=pathlib.Path(__file__).resolve().parent.parent
protocol=json.loads((ROOT/'PROTOCOL.json').read_text())
checks=[]
for name,fn in [('network',lambda:socket.socket()),('process',lambda:subprocess.Popen(['not-a-real-command'])),('outside_read',lambda:open('C:/BRASILEIRAO/OSR_NONEXISTENT_CANARY','r')),('outside_write',lambda:open(ROOT/'forbidden-canary','w')),('sqlite_disk',lambda:sqlite3.connect(str(ROOT/'forbidden.db')))]:
    try:fn()
    except PermissionError:checks.append({'control':name,'blocked':True})
    else:raise AssertionError(name)
assert 'OSR_PARENT_CANARY' not in os.environ
rows=[]
for h,a,alpha,rho in protocol['N01']['reproduce_first']:
    r=1/alpha;ph=r/(r+h);pa=r/(r+a)
    hp=nbinom.pmf([0,1],r,ph);ap=nbinom.pmf([0,1],r,pa)
    factors=[1-h*a*rho,1+h*rho,1+a*rho,1-rho]
    correction=sum(p*q*(t-1) for p,q,t in zip([hp[0],hp[0],hp[1],hp[1]],[ap[0],ap[1],ap[0],ap[1]],factors))
    z=1+correction
    sfh=nbinom.sf(12,r,ph);sfa=nbinom.sf(12,r,pa)
    omitted=(sfh+sfa-sfh*sfa)/z
    grid=_score_grid(h,a,alpha,rho,12)
    rows.append({'params':[h,a,alpha,rho],'lost_mass':float(omitted),'normalized_grid_sum':float(grid.sum()),'dc_total_mass':float(z)})
out={'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'isolation_controls':checks,'inherited_canary_absent':True,'T01_reproduced':rows}
with (ROOT/'evidence/reproduction.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print(json.dumps(out))
