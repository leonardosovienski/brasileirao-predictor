"""Public offline diagnostic consumer: python goals_demo.py [explicit JSON]."""
import json,sys
from pathlib import Path
import fast_goals
from workflow import guarded
import artifacts
ROOT=Path(__file__).resolve().parent.parent

def diagnose(values):
    results=[]
    for p in values:
        try:
            x=fast_goals.adaptive_grid(*p,max_goals=1024)
            g=x.grid;h=float(__import__('numpy').tril(g,-1).sum());d=float(g.trace());a=float(__import__('numpy').triu(g,1).sum())
            denominator=h+a
            results.append({'parameters':p,'status':'TOLERANCE_MET','diagnostic':x.diagnostic,
                'probabilities_1X2':[h,d,a],'non_draw_mass_in_grid':denominator,
                'home_given_non_draw':h/denominator if denominator else None,
                'conditional_error_bound':min(1,2*x.diagnostic['omitted_mass']/denominator) if denominator else None,
                'conditional_bound_note':'conservative bound; not an assertion of 1e-6 conditional accuracy'})
        except fast_goals.SupportLimitError as e:
            results.append({'parameters':p,'status':'SUPPORT_LIMIT','diagnostic':e.diagnostic,'probabilities_1X2':None})
        except (ValueError,ArithmeticError) as e:
            results.append({'parameters':p,'status':'INVALID_OR_NUMERIC_FAILURE','reason':str(e),'probabilities_1X2':None})
    return results

if __name__=='__main__':
    # child_boot leaves its script path in argv; custom CLI inputs end in .json.
    given=sys.argv[1] if len(sys.argv)>1 and sys.argv[1].endswith('.json') else str(ROOT/'examples/goals.json')
    path=guarded(given);payload=artifacts.read_json(path)
    result=diagnose(payload['parameters'])
    (ROOT/'evidence/goals-demo.json').open('x',encoding='utf-8').write(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({'cases':len(result),'statuses':[r['status'] for r in result]}))
