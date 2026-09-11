"""Small research adapters; no silent de-vig fallback or fitting."""
from dataclasses import dataclass
from numbers import Real
import math
import numpy as np
from scipy.optimize import brentq

CLASSES=('1','X','2')

def probabilities(values,n,*,sum_tolerance=1e-10):
    if not isinstance(values,(list,tuple,np.ndarray)) or len(values)!=n:raise ValueError('probability shape')
    if any(isinstance(x,(bool,np.bool_)) or not isinstance(x,Real) for x in values):raise ValueError('probability type')
    p=np.array(values,dtype=float)
    if p.ndim!=1 or not np.isfinite(p).all() or np.any(p<0) or np.any(p>1):raise ValueError('probability domain')
    if abs(math.fsum(p)-1)>sum_tolerance:raise ValueError('probability sum')
    return p

def odds_vector(values,*,exhaustive):
    if exhaustive is not True:raise ValueError('mutually exclusive exhaustive contract not acknowledged')
    if not isinstance(values,(list,tuple,np.ndarray)) or not 2<=len(values)<=32:raise ValueError('odds shape')
    if any(isinstance(x,(bool,np.bool_)) or not isinstance(x,Real) or not math.isfinite(float(x)) or x<=1 for x in values):raise ValueError('decimal odds must be finite >1')
    return np.array(values,dtype=float)

@dataclass(frozen=True)
class DevigResult:
    probabilities:tuple[float,...]|None
    requested_method:str
    method_used:str|None
    regime:str
    status:str
    overround:float
    detail:str=''

def devig(values,method,*,exhaustive,underround='reject',maxiter=200):
    if method not in {'proportional','shin','power'}:raise ValueError('unknown method')
    if underround not in {'reject','proportional'}:raise ValueError('unknown underround policy')
    if isinstance(maxiter,bool) or not isinstance(maxiter,int) or not 1<=maxiter<=200:raise ValueError('maxiter')
    odds=odds_vector(values,exhaustive=exhaustive);q=1/odds;s=float(q.sum());margin=s-1
    regime='FAIR' if abs(margin)<=1e-12 else 'OVERROUND' if margin>0 else 'UNDERROUND'
    if regime=='UNDERROUND' and underround=='reject':return DevigResult(None,method,None,regime,'UNSUPPORTED_REGIME',margin)
    if regime!='OVERROUND' or method=='proportional':
        status='EXPLICIT_PROPORTIONAL_SCENARIO' if regime=='UNDERROUND' else 'FAIR_NORMALIZATION' if regime=='FAIR' else 'OK'
        p=probabilities((q/s).tolist(),len(q))
        return DevigResult(tuple(p),method,'proportional',regime,status,margin)
    try:
        if method=='power':
            upper=max(2.,2*math.log(len(q))/-math.log(float(q.max())))
            root,info=brentq(lambda k:float(np.power(q,k).sum())-1,1.,upper,xtol=1e-13,maxiter=maxiter,full_output=True,disp=False)
            p=np.power(q,root)
        else:
            # Rationalized expression avoids subtractive cancellation.
            def implied(z):return 2*q*q/s/(np.sqrt(z*z+4*(1-z)*q*q/s)+z)
            root,info=brentq(lambda z:float(implied(z).sum())-1,0.,1.,xtol=1e-13,maxiter=maxiter,full_output=True,disp=False)
            p=implied(root)
        if not info.converged:return DevigResult(None,method,None,regime,'CONVERGENCE_FAILED',margin)
        p=probabilities(p,len(q))
        return DevigResult(tuple(p),method,method,regime,'OK',margin)
    except (ValueError,ArithmeticError,RuntimeError):
        return DevigResult(None,method,None,regime,'SOLVER_OR_OUTPUT_FAILED',margin)

def checked_engine(values,engine,*,exhaustive):
    """engine returns (probabilities, converged); no fabricated fallback."""
    odds=odds_vector(values,exhaustive=exhaustive)
    try:
        p,converged=engine(odds.tolist())
        if converged is not True:return {'status':'CONVERGENCE_FAILED','probabilities':None}
        p=probabilities(p,len(odds))
        return {'status':'OK','probabilities':p.tolist()}
    except (ValueError,TypeError,ArithmeticError,RuntimeError):
        return {'status':'ENGINE_OR_OUTPUT_FAILED','probabilities':None}

def score_1x2(predictions,labels,*,classes=CLASSES):
    if tuple(classes)!=CLASSES:raise ValueError('class order must be 1,X,2')
    if not isinstance(predictions,(list,tuple,np.ndarray)) or len(predictions)==0 or len(predictions)!=len(labels):raise ValueError('batch length')
    p=np.array([probabilities(row,3) for row in predictions]);y=np.zeros_like(p)
    for i,label in enumerate(labels):
        if label not in CLASSES:raise ValueError('label must be canonical string')
        y[i,CLASSES.index(label)]=1
    chosen=np.sum(p*y,axis=1);brier=np.sum((p-y)**2,axis=1);loss=-np.log(np.maximum(chosen,1e-12))
    return {'brier_mean':float(brier.mean()),'brier_per_match':brier.tolist(),'log_loss_mean':float(loss.mean()),'log_loss_per_match':loss.tolist(),'clipped_count':int((chosen<1e-12).sum()),'classes':list(CLASSES),'brier_scale':'sum 0..2','log_loss_unit':'nats, lower clipped at 1e-12'}

def calibration_bins(predictions,labels):
    score_1x2(predictions,labels)
    p=np.asarray(predictions,dtype=float);edges=np.linspace(0,1,6);out={}
    for j,c in enumerate(CLASSES):
        bins=[]
        for k in range(5):
            mask=(p[:,j]>=edges[k])&((p[:,j]<edges[k+1]) if k<4 else (p[:,j]<=1))
            n=int(mask.sum())
            bins.append({'lower':float(edges[k]),'upper':float(edges[k+1]),'count':n,'mean_prediction':float(p[mask,j].mean()) if n else None,'observed_frequency':float(np.mean(np.asarray(labels)[mask]==c)) if n else None})
        out[c]=bins
    return {'bins':out,'status':'DIAGNOSTIC_ONLY_NO_MODEL_CALIBRATION_CLAIM'}
