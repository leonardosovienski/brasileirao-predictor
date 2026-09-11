"""Research-only NB x NB + four-cell DC, with an explicit truncation bound.

For K>=1 every DC correction is inside the square. The remaining raw mass is
the union of the two independent NB tails. After dividing by the exact DC
normalizer Z, this is the total variation error of conditioning on the square.
Every derived payoff in [0,1] consequently has absolute error <= omitted_mass
(up to floating point). Conditional prices/ratios do not inherit that bound.
"""
from dataclasses import dataclass
from numbers import Real,Integral
import math
import numpy as np
from scipy.stats import nbinom

class SupportLimitError(ValueError):
    def __init__(self,diagnostic):
        self.diagnostic=diagnostic
        super().__init__('SUPPORT_LIMIT: tolerance not reached; no candidate grid')

def finite_real(value,name):
    if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(float(value)):
        raise ValueError(name+' must be finite real, not bool/string')
    return float(value)

def parameters(home,away,alpha,rho):
    h,a,d,rh=(finite_real(x,n) for x,n in zip((home,away,alpha,rho),('home','away','alpha','rho')))
    if not(.05<=h<=10 and .05<=a<=10 and .01<=d<=2):raise ValueError('outside research domain')
    factors=np.array([1-h*a*rh,1+h*rh,1+a*rh,1-rh])
    if np.any(factors<=0):raise ValueError('nonpositive DC factor; no implicit clamp')
    r=1/d;ph=r/(r+h);pa=r/(r+a)
    hp=nbinom.pmf([0,1],r,ph);ap=nbinom.pmf([0,1],r,pa)
    cells=np.array([hp[0]*ap[0],hp[0]*ap[1],hp[1]*ap[0],hp[1]*ap[1]])
    correction=math.fsum(float(x) for x in cells*(factors-1))
    z=1+correction
    if not math.isfinite(z) or z<=0:raise ValueError('invalid DC normalizer')
    return h,a,d,rh,r,ph,pa,factors,z

def mass_diagnostic(home,away,alpha,rho,k):
    if isinstance(k,bool) or not isinstance(k,Integral) or not 1<=k<=1024:raise ValueError('support integer 1..1024')
    h,a,d,rh,r,ph,pa,f,z=parameters(home,away,alpha,rho)
    sh=float(nbinom.sf(k,r,ph));sa=float(nbinom.sf(k,r,pa))
    raw_tail=sh+sa-sh*sa
    omitted=raw_tail/z
    return {'max_goals':int(k),'dc_total_mass':z,'raw_tail_mass':raw_tail,'raw_retained_mass':z-raw_tail,'retained_probability_before_conditional_renormalization':1-omitted,'omitted_mass':omitted}

@dataclass(frozen=True)
class GoalGrid:
    grid:np.ndarray
    diagnostic:dict

def adaptive_grid(home,away,alpha,rho,*,mass_tolerance=1e-6,max_goals=512):
    tol=finite_real(mass_tolerance,'mass_tolerance')
    if not 1e-14<=tol<=1e-3:raise ValueError('tolerance outside 1e-14..1e-3')
    if isinstance(max_goals,bool) or not isinstance(max_goals,Integral) or not 1<=max_goals<=1024:
        raise ValueError('max_goals integer 1..1024')
    h,a,d,rh,r,ph,pa,factors,z=parameters(home,away,alpha,rho)
    probes=0
    def diagnostic(k):
        nonlocal probes
        probes+=1
        return mass_diagnostic(h,a,d,rh,k)
    lo=0;hi=1;diag=diagnostic(hi)
    while diag['omitted_mass']>tol and hi<max_goals:
        lo=hi;hi=min(2*hi,max_goals);diag=diagnostic(hi)
    if diag['omitted_mass']>tol:
        raise SupportLimitError({**diag,'requested_tolerance':tol,'support_probes':probes})
    while hi-lo>1:
        mid=(lo+hi)//2
        if diagnostic(mid)['omitted_mass']<=tol:hi=mid
        else:lo=mid
    diag=diagnostic(hi)
    k=np.arange(hi+1)
    raw=np.outer(nbinom.pmf(k,r,ph),nbinom.pmf(k,r,pa))
    for (i,j),f in zip([(0,0),(0,1),(1,0),(1,1)],factors):raw[i,j]*=f
    raw_sum=float(raw.sum())
    error=abs(raw_sum-diag['raw_retained_mass'])
    if not np.isfinite(raw).all() or np.any(raw<0) or raw_sum<=0 or error>1e-10:
        raise ArithmeticError('PMF/CDF identity or positivity failed')
    grid=raw/raw_sum;grid.setflags(write=False)
    return GoalGrid(grid,{**diag,'raw_matrix_sum':raw_sum,'mass_identity_error':error,'requested_tolerance':tol,'support_probes':probes,'bytes_grid':grid.nbytes,'status':'TOLERANCE_MET'})
