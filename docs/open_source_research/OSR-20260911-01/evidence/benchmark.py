import sys, pathlib, os, json, hashlib, time, platform, datetime
ROOT=pathlib.Path(__file__).parent.resolve()
sys.path.insert(0,str(ROOT/'lab'))
def guard(event,args):
 if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):raise PermissionError('Benchmark blocks network/process execution')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  p=pathlib.Path(os.fsdecode(args[0])).resolve()
  allowed=[ROOT,pathlib.Path(sys.prefix).resolve(),pathlib.Path(sys.base_prefix).resolve()]
  if not any(p.is_relative_to(a) for a in allowed):raise PermissionError('Read/write outside benchmark/runtime roots: '+str(p))
sys.addaudithook(guard)
import numpy as np
from scipy.stats import nbinom
import scipy
from brasileirao_predictor import model,market_pricer,math_utils
from brasileirao_predictor.research.structural_edge import power_probabilities
from brasileirao_predictor.research.shadow_portfolio import replay_shadow_portfolio
from pbref.implied import calculate_implied
from pbref.models import ImpliedProbabilities,ImpliedMethod
start=time.perf_counter()
protocol=json.loads((ROOT/'G1_PROTOCOL.json').read_text(encoding='utf-8-sig'))
out={'protocol_sha256':hashlib.sha256((ROOT/'G1_PROTOCOL.json').read_bytes()).hexdigest(),'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform(),'scope':'synthetic engineering only','T01':[],'T02':[]}
for la,lb,alpha,rho in protocol['experiments'][0]['cases']:
 r=1/alpha;normalizer=float(model._dc_normalizer_nb(la,lb,alpha,rho))
 corrected_truncated=float(nbinom.cdf(12,r,r/(r+la))*nbinom.cdf(12,r,r/(r+lb))+normalizer-1)
 lost=1-corrected_truncated/normalizer
 g=model._score_grid(la,lb,alpha,rho,12);big=model._score_grid(la,lb,alpha,rho,100)
 a=market_pricer.result_1x2(g);b=market_pricer.result_1x2(big)
 k=np.arange(13);raw=np.outer(nbinom.pmf(k,r,r/(r+la)),nbinom.pmf(k,r,r/(r+lb)))
 for i,j,t in [(0,0,1-la*lb*rho),(0,1,1+la*rho),(1,0,1+lb*rho),(1,1,1-rho)]:raw[i,j]*=t
 identity_error=abs(float(raw.sum())-corrected_truncated)
 assert identity_error<1e-10
 out['T01'].append({'params':[la,lb,alpha,rho],'lost_mass':lost,'identity_error':identity_error,'max_1x2_difference':max(abs(a[c]-b[c]) for c in a),'p12':a,'p100':b,'diagnostic_triggered':lost>1e-6})
for odds in protocol['experiments'][1]['cases']:
 for method,fn in [('shin',math_utils.shin_probabilities),('power',power_probabilities)]:
  row={'odds':odds,'method':method,'overround':sum(1/o for o in odds)-1}
  for name,f in [('local',lambda:fn(odds)[0]),('external',lambda:calculate_implied(odds,method=method).probabilities)]:
   try:row[name]=list(map(float,f()))
   except Exception as e:row[name+'_error']=type(e).__name__+': '+str(e)
  if 'local'in row and 'external'in row:row['max_abs_diff']=max(abs(x-y) for x,y in zip(row['local'],row['external']))
  out['T02'].append(row)
try:
 v=ImpliedProbabilities([-0.1,0.5,0.6],ImpliedMethod.MULTIPLICATIVE,0.0)
 out['T02_negative_control']={'accepted':True,'probabilities':v.probabilities}
except Exception as e:out['T02_negative_control']={'accepted':False,'error':type(e).__name__}
maxerr=0.0;comparisons=0
for h in range(5):
 for a in range(5):
  g=np.zeros((5,5));g[h,a]=1
  for line in [-1.25,-1,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1,1.25]:
   lines=[line-.25,line+.25] if abs(line)%1 in (.25,.75) else [line]
   expected={n:sum((h-a+l>0 if n=='win' else h-a+l==0 if n=='push' else h-a+l<0) for l in lines)/len(lines) for n in ['win','push','lose']}
   actual=market_pricer.asian_handicap(g,line)
   maxerr=max(maxerr,max(abs(actual[n]-expected[n]) for n in expected));comparisons+=1
  for line in [0,.5,1,1.5,2,2.5,3]:
   actual=market_pricer.over_under(g,line);expected={'Over':float(h+a>line),'Under':float(h+a<line),'Push':float(h+a==line)}
   maxerr=max(maxerr,max(abs(actual[n]-expected[n]) for n in expected));comparisons+=1
  assert market_pricer.result_1x2(g)=={'1':float(h>a),'X':float(h==a),'2':float(h<a)}
  assert market_pricer.draw_no_bet(g)['1']=={'win':float(h>a),'push':float(h==a),'lose':float(h<a)}
  assert market_pricer.both_teams_to_score(g)['Yes']==float(h>0 and a>0)
orders=[{'event_id':e,'predicted_at':'2030-01-01T10:00:00Z','settled_at':'2030-01-01T14:00:00Z','outcome':1,'stake_fraction':.6,'odds':2.0,'friction_rate':0.0,'selection':'over'} for e in ['SYN-A','SYN-B']]
pending=replay_shadow_portfolio(orders,as_of='2030-01-01T12:00:00Z');final=replay_shadow_portfolio(orders)
assert maxerr<=1e-12 and pending['final_cash']==40 and pending['open_stakes']==60 and final['final_cash']==160
assert any(r['event_id']=='SYN-B' and r['action']=='NO_CAPITAL' for r in final['receipts'])
out['T03']={'atomic_payoff_cases':comparisons,'max_abs_error':maxerr,'pending':pending,'final':final}
out['elapsed_seconds']=time.perf_counter()-start
out['module_hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'lab').rglob('*.py')}
dest=ROOT/'benchmark_results.json'
with dest.open('x',encoding='utf-8') as f:json.dump(out,f,indent=2,allow_nan=False)
print(json.dumps(out,indent=2,allow_nan=False))
