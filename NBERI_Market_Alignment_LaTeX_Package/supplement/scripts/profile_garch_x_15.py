import os, math, zipfile, warnings
import numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.stats import chi2
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from numba import njit
warnings.filterwarnings('ignore')

OUT='/mnt/data/nberi_15_country_garch_profiled'
os.makedirs(OUT,exist_ok=True)
SRC='/mnt/data/NBERI_GARCH_FAMILY_EXTENSION_RESULTS_2026-09-14.zip'
BASE='/mnt/data/nberi_15_country_garch_robust/garch_family_robust_all.csv'
sel_corr={'Zambia':0.718,'Ghana':0.668,'Malawi':0.649,'Tanzania':0.561,'Algeria':0.549,'Burundi':0.480,'Libya':0.415,'Nigeria':0.322,'Tunisia':0.296,'Morocco':0.285,'Liberia':0.279,'Namibia':0.268,'Congo DRC':0.266,'Guinea':0.263,'Benin':0.247}
selected=list(sel_corr)
with zipfile.ZipFile(SRC) as z: df=pd.read_csv(z.open('macro_panel_inflation_fx.csv'))
df['Date']=pd.to_datetime(df.Date); df=df[(df.Date>='2015-01-01')&(df.Date<='2025-12-01')].sort_values(['Country','Date']).copy(); df['r']=df.groupby('Country').Exchange_Rate_Raw.transform(lambda s:100*np.log(s/s.shift(1))); df=df[df.Country.isin(selected)].copy(); df['x']=df.groupby('Country').FXExternalRisk.transform(lambda s:(s-s.mean())/s.std(ddof=1))
baseall=pd.read_csv(BASE)

@njit(cache=True)
def tlog(z,nu): return math.lgamma((nu+1)/2)-math.lgamma(nu/2)-0.5*math.log((nu-2)*math.pi)-0.5*(nu+1)*math.log1p(z*z/(nu-2))
@njit(cache=True)
def eabs(nu): return 2*math.sqrt(nu-2)*math.exp(math.lgamma((nu+1)/2)-math.lgamma(nu/2))/(math.sqrt(math.pi)*(nu-1))
@njit(cache=True)
def nll_full(p,r,rlag,x,fam,usex):
    mu=p[0]; phi=p[1]; n=len(r)
    if fam==0:
        omega,alpha,beta,nu=p[2],p[3],p[4],p[5]; j=6
        if omega<=0 or alpha<0 or beta<0 or alpha+beta>=0.999 or nu<=2.01:return 1e100
    else:
        omega,alpha,gamma,beta,nu=p[2],p[3],p[4],p[5],p[6]; j=7
        if fam==1:
            if abs(beta)>=.999 or nu<=2.01:return 1e100
        else:
            if omega<=0 or alpha<0 or beta<0 or alpha+gamma<0 or alpha+.5*gamma+beta>=.999 or nu<=2.01:return 1e100
    delta=p[j] if usex else 0.0
    e=np.empty(n);h=np.empty(n)
    for t in range(n):e[t]=r[t]-mu-phi*rlag[t]
    v=0.0
    for t in range(n):v+=e[t]*e[t]
    h[0]=max(v/n,1e-6);E=eabs(nu);ll=tlog(e[0]/math.sqrt(h[0]),nu)-.5*math.log(h[0])
    for t in range(1,n):
        if fam==0:
            hv=omega+alpha*e[t-1]**2+beta*h[t-1]
            if usex:hv*=math.exp(max(-20,min(20,delta*x[t])))
        elif fam==2:
            I=1.0 if e[t-1]<0 else 0.0;hv=omega+(alpha+gamma*I)*e[t-1]**2+beta*h[t-1]
            if usex:hv*=math.exp(max(-20,min(20,delta*x[t])))
        else:
            zp=e[t-1]/math.sqrt(max(h[t-1],1e-12));lh=omega+alpha*(abs(zp)-E)+gamma*zp+beta*math.log(max(h[t-1],1e-12))+delta*x[t]
            hv=math.exp(max(-30,min(30,lh)))
        if not math.isfinite(hv) or hv<=1e-12 or hv>1e12:return 1e100
        h[t]=hv;ll+=tlog(e[t]/math.sqrt(hv),nu)-.5*math.log(hv)
    return -ll

def bds(r,fam,usex=True):
    sd=max(np.std(r),1.0);var=max(np.var(r),1e-4);a=[(-10*sd,10*sd),(-.95,.95)]
    if fam==0:a += [(1e-10,max(var*20,1)),(1e-8,.998),(1e-8,.998),(2.05,80)]
    elif fam==1:a += [(-15,15),(-4,4),(-4,4),(-.998,.998),(2.05,80)]
    else:a += [(1e-10,max(var*20,1)),(1e-8,.998),(-.95,1.95),(1e-8,.998),(2.05,80)]
    if usex:a+=[(-2,2)]
    return a

def basevec(row,fam):
    if fam==0:return np.array([row.mu,row.phi,row.omega,row.alpha,row.beta,row.nu],float)
    return np.array([row.mu,row.phi,row.omega,row.alpha,row.gamma,row.beta,row.nu],float)

def opt_fixed_delta(basep,delta,r,rlag,x,fam,start_extra=None):
    bd=bds(r,fam,False)
    def f(q):return nll_full(np.r_[q,delta],r,rlag,x,fam,True)
    starts=[basep.copy()]
    if start_extra is not None:starts.append(start_extra.copy())
    rng=np.random.default_rng(1234+fam)
    for _ in range(2):
        q=basep.copy();q+=rng.normal(0,.03,len(q))*np.maximum(abs(q),1);starts.append(q)
    best=None
    for st in starts:
        for i,(lo,hi) in enumerate(bd):st[i]=min(max(st[i],lo+1e-8),hi-1e-8)
        o=minimize(f,st,method='L-BFGS-B',bounds=bd,options={'maxiter':2500,'ftol':1e-12,'gtol':1e-7,'maxls':80})
        if np.isfinite(o.fun) and o.fun<1e90 and (best is None or o.fun<best.fun):best=o
    return best

def joint_refine(q,delta,r,rlag,x,fam):
    p0=np.r_[q,delta];bd=bds(r,fam,True)
    o1=minimize(lambda p:nll_full(p,r,rlag,x,fam,True),p0,method='Powell',bounds=bd,options={'maxiter':4000,'ftol':1e-10,'xtol':1e-8})
    s=o1.x if np.isfinite(o1.fun) else p0
    o2=minimize(lambda p:nll_full(p,r,rlag,x,fam,True),s,method='L-BFGS-B',bounds=bd,options={'maxiter':3500,'ftol':1e-13,'gtol':1e-8,'maxls':100})
    if np.isfinite(o2.fun) and (not np.isfinite(o1.fun) or o2.fun<o1.fun):return o2
    return o1

def stdres(p,r,rlag,x,fam):
    mu=p[0];phi=p[1];n=len(r);e=r-mu-phi*rlag;h=np.empty(n);h[0]=max(np.mean(e*e),1e-6)
    if fam==0:omega,alpha,beta,nu=p[2:6];delta=p[6]
    else:omega,alpha,gamma,beta,nu=p[2:7];delta=p[7]
    E=eabs.py_func(nu)
    for t in range(1,n):
        if fam==0:hv=(omega+alpha*e[t-1]**2+beta*h[t-1])*np.exp(np.clip(delta*x[t],-20,20))
        elif fam==2:hv=(omega+(alpha+gamma*(e[t-1]<0))*e[t-1]**2+beta*h[t-1])*np.exp(np.clip(delta*x[t],-20,20))
        else:
            zp=e[t-1]/np.sqrt(max(h[t-1],1e-12));hv=np.exp(np.clip(omega+alpha*(abs(zp)-E)+gamma*zp+beta*np.log(max(h[t-1],1e-12))+delta*x[t],-30,30))
        h[t]=hv
    return e/np.sqrt(h)

grid=np.array([-1.0,-.75,-.5,-.3,-.15,0,.15,.3,.5,.75,1.0])
rows=[]; profiles=[]
for ci,c in enumerate(selected,1):
    g=df[df.Country==c].sort_values('Date').copy();g['rlag']=g.r.shift(1);g['xlag']=g.x.shift(1);g=g.dropna(subset=['r','rlag','xlag']);r=g.r.values.astype(float);rlag=g.rlag.values.astype(float);x=g.xlag.values.astype(float)
    print(f'[{ci}/15] {c}',flush=True)
    for fam,name in [(0,'GARCH'),(1,'EGARCH'),(2,'GJR/TGARCH')]:
        brow=baseall[(baseall.Country==c)&(baseall.Family==name)&(~baseall.Uses_X)].iloc[0]
        bp=basevec(brow,fam);baseLL=float(brow.loglik)
        bestfix=None;prev=None;bestdelta=None
        for dlt in grid:
            of=opt_fixed_delta(bp,dlt,r,rlag,x,fam,prev)
            if of is None:continue
            prev=of.x.copy();profiles.append(dict(Country=c,Family=name,delta=dlt,loglik=-of.fun))
            if bestfix is None or of.fun<bestfix.fun:bestfix=of;bestdelta=dlt
        jr=joint_refine(bestfix.x,bestdelta,r,rlag,x,fam)
        nested=np.r_[bp,0.0];nn=nll_full(nested,r,rlag,x,fam,True)
        if jr is None or jr.fun>nn+1e-8:
            class O: pass
            jr=O();jr.x=nested;jr.fun=nn;jr.success=True
        p=jr.x;ll=-jr.fun;k=len(p);lr=max(0,2*(ll-baseLL));lrp=float(chi2.sf(lr,1));delta=float(p[-1]);z=stdres(p,r,rlag,x,fam)
        try:lb=float(acorr_ljungbox(z*z,lags=[5],return_df=True).lb_pvalue.iloc[0])
        except:lb=np.nan
        try:ap=float(het_arch(z,nlags=5)[1])
        except:ap=np.nan
        rows.append(dict(Country=c,Correlation=sel_corr[c],Family=name,N=len(r),base_loglik=baseLL,x_loglik=ll,delta=delta,LR=lr,LR_p=lrp,AIC=2*k-2*ll,BIC=k*np.log(len(r))-2*ll,LB_sq5_p=lb,ARCH_LM5_p=ap,converged=getattr(jr,'success',True),profile_grid_best_delta=bestdelta))

res=pd.DataFrame(rows);res['BH_FDR_q']=np.nan
for fam,idx in res.groupby('Family').groups.items():res.loc[idx,'BH_FDR_q']=multipletests(res.loc[idx,'LR_p'].values,method='fdr_bh')[1]
res.to_csv(os.path.join(OUT,'profiled_garch_x_results.csv'),index=False);pd.DataFrame(profiles).to_csv(os.path.join(OUT,'delta_profiles.csv'),index=False)
sig=res[res.BH_FDR_q<.10].sort_values(['BH_FDR_q','Country']);sig.to_csv(os.path.join(OUT,'profiled_sig_q10.csv'),index=False)
print('\n',sig[['Country','Family','delta','profile_grid_best_delta','LR_p','BH_FDR_q','AIC','LB_sq5_p','ARCH_LM5_p']].to_string(index=False))
