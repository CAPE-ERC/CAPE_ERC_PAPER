import os, math, zipfile, warnings
import numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import chi2
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from numba import njit
warnings.filterwarnings('ignore')

OUT='/mnt/data/nberi_15_country_garch_robust'
os.makedirs(OUT,exist_ok=True)
SRC='/mnt/data/NBERI_GARCH_FAMILY_EXTENSION_RESULTS_2026-09-14.zip'
sel_corr={
    'Zambia':0.718,'Ghana':0.668,'Malawi':0.649,'Tanzania':0.561,'Algeria':0.549,
    'Burundi':0.480,'Libya':0.415,'Nigeria':0.322,'Tunisia':0.296,'Morocco':0.285,
    'Liberia':0.279,'Namibia':0.268,'Congo DRC':0.266,'Guinea':0.263,'Benin':0.247}
selected=list(sel_corr)

with zipfile.ZipFile(SRC) as z:
    df=pd.read_csv(z.open('macro_panel_inflation_fx.csv'))
df['Date']=pd.to_datetime(df.Date)
df=df[(df.Date>='2015-01-01')&(df.Date<='2025-12-01')].sort_values(['Country','Date']).copy()
df['r']=df.groupby('Country').Exchange_Rate_Raw.transform(lambda s:100*np.log(s/s.shift(1)))
df=df[df.Country.isin(selected)].copy()
df['x']=df.groupby('Country').FXExternalRisk.transform(lambda s:(s-s.mean())/s.std(ddof=1))

@njit(cache=True)
def tlogpdf_std(z,nu):
    return math.lgamma((nu+1)/2)-math.lgamma(nu/2)-0.5*math.log((nu-2)*math.pi)-0.5*(nu+1)*math.log1p(z*z/(nu-2))

@njit(cache=True)
def eabs_t(nu):
    return 2*math.sqrt(nu-2)*math.exp(math.lgamma((nu+1)/2)-math.lgamma(nu/2))/(math.sqrt(math.pi)*(nu-1))

@njit(cache=True)
def nll_phys(p,r,rlag,x,fam,usex):
    # p physical parameterization
    mu=p[0]; phi=p[1]
    n=len(r)
    if fam==0: # GARCH: mu phi omega alpha beta nu [delta]
        omega=p[2]; alpha=p[3]; beta=p[4]; nu=p[5]; j=6
        if omega<=0 or alpha<0 or beta<0 or alpha+beta>=0.999 or nu<=2.01: return 1e100
    elif fam==1: # EGARCH: mu phi omega alpha gamma beta nu [delta]
        omega=p[2]; alpha=p[3]; gamma=p[4]; beta=p[5]; nu=p[6]; j=7
        if abs(beta)>=0.999 or nu<=2.01: return 1e100
    else: # GJR: mu phi omega alpha gamma beta nu [delta]
        omega=p[2]; alpha=p[3]; gamma=p[4]; beta=p[5]; nu=p[6]; j=7
        if omega<=0 or alpha<0 or beta<0 or alpha+gamma<0 or alpha+0.5*gamma+beta>=0.999 or nu<=2.01: return 1e100
    delta=p[j] if usex else 0.0
    e=np.empty(n); h=np.empty(n)
    for t in range(n):
        e[t]=r[t]-mu-phi*rlag[t]
    v=0.0
    for t in range(n): v += e[t]*e[t]
    h[0]=max(v/n,1e-6)
    E=eabs_t(nu)
    ll=tlogpdf_std(e[0]/math.sqrt(h[0]),nu)-0.5*math.log(h[0])
    for t in range(1,n):
        if fam==0:
            hv=omega+alpha*e[t-1]*e[t-1]+beta*h[t-1]
            if usex: hv*=math.exp(max(-20,min(20,delta*x[t])))
        elif fam==2:
            I=1.0 if e[t-1]<0 else 0.0
            hv=omega+(alpha+gamma*I)*e[t-1]*e[t-1]+beta*h[t-1]
            if usex: hv*=math.exp(max(-20,min(20,delta*x[t])))
        else:
            zprev=e[t-1]/math.sqrt(max(h[t-1],1e-12))
            lh=omega+alpha*(abs(zprev)-E)+gamma*zprev+beta*math.log(max(h[t-1],1e-12))
            if usex: lh += delta*x[t]
            lh=max(-30,min(30,lh)); hv=math.exp(lh)
        if not math.isfinite(hv) or hv<=1e-12 or hv>1e12: return 1e100
        h[t]=hv
        ll += tlogpdf_std(e[t]/math.sqrt(hv),nu)-0.5*math.log(hv)
    return -ll


def initial_grid(r,rlag,fam,usex,base=None):
    X=np.column_stack([np.ones(len(r)),rlag]); b=np.linalg.lstsq(X,r,rcond=None)[0]
    mu=float(b[0]); phi=float(np.clip(b[1],-.8,.8)); e=r-mu-phi*rlag; v=max(float(np.var(e)),1e-4)
    starts=[]
    if base is not None:
        for d in ([0,.08,-.08,.2,-.2,.5,-.5] if usex else [0]):
            q=base.copy()
            if usex: q=np.r_[q,d]
            starts.append(q)
    if fam==0:
        for a,be in [(0.05,.90),(.10,.85),(.20,.70),(.35,.50)]:
            omega=max(v*(1-a-be),v*.005,1e-6); p=np.array([mu,phi,omega,a,be,8.0])
            if usex:
                for d in [0,.1,-.1,.3,-.3]: starts.append(np.r_[p,d])
            else: starts.append(p)
    elif fam==2:
        for a,g,be in [(.05,.05,.88),(.10,.05,.82),(.15,.10,.70),(.05,-.02,.90)]:
            if a+g<0 or a+.5*g+be>=.995: continue
            omega=max(v*(1-a-.5*g-be),v*.005,1e-6); p=np.array([mu,phi,omega,a,g,be,8.0])
            if usex:
                for d in [0,.1,-.1,.3,-.3]: starts.append(np.r_[p,d])
            else: starts.append(p)
    else:
        lv=math.log(max(v,1e-5))
        for a,g,be in [(.10,0,.90),(.20,-.05,.85),(.15,.10,.75),(.30,0,.60)]:
            om=(1-be)*lv; p=np.array([mu,phi,om,a,g,be,8.0])
            if usex:
                for d in [0,.1,-.1,.3,-.3]: starts.append(np.r_[p,d])
            else: starts.append(p)
    # deterministic jitter starts
    rng=np.random.default_rng(20260914+fam+(100 if usex else 0))
    base_starts=list(starts[:min(6,len(starts))])
    for st in base_starts:
        for _ in range(2):
            q=st.copy(); scale=np.maximum(np.abs(q),1.0); q += rng.normal(0,.05,len(q))*scale
            # reset/clip sensitive dims later by bounds
            starts.append(q)
    return starts


def bounds(r,fam,usex):
    sd=max(np.std(r),1.0); var=max(np.var(r),1e-4)
    mb=(-10*sd,10*sd); ph=(-.95,.95); om=(1e-10, max(var*20,1.0)); nu=(2.05,80.0); delta=(-2.0,2.0)
    if fam==0:
        b=[mb,ph,om,(1e-8,.998),(1e-8,.998),nu]
    elif fam==2:
        b=[mb,ph,om,(1e-8,.998),(-.95,1.95),(1e-8,.998),nu]
    else:
        b=[mb,ph,(-15,15),(-3,3),(-3,3),(-.998,.998),nu]
    if usex: b.append(delta)
    return b


def sanitize_start(st,bds):
    q=st.copy()
    for i,(lo,hi) in enumerate(bds): q[i]=min(max(q[i],lo+1e-8),hi-1e-8)
    return q


def optimize_one(r,rlag,x,fam,usex,base_params=None):
    bds=bounds(r,fam,usex)
    starts=[sanitize_start(s,bds) for s in initial_grid(r,rlag,fam,usex,base_params)]
    best=None
    # L-BFGS first for many starts
    for st in starts:
        opt=minimize(lambda p:nll_phys(p,r,rlag,x,fam,usex),st,method='L-BFGS-B',bounds=bds,
                     options={'maxiter':3000,'ftol':1e-12,'gtol':1e-7,'maxls':80})
        if np.isfinite(opt.fun) and opt.fun<1e90 and (best is None or opt.fun<best.fun): best=opt
    # refine best with Powell then L-BFGS
    if best is not None:
        powell=minimize(lambda p:nll_phys(p,r,rlag,x,fam,usex),best.x,method='Powell',bounds=bds,
                        options={'maxiter':6000,'ftol':1e-10,'xtol':1e-8})
        cand=powell if np.isfinite(powell.fun) and powell.fun<best.fun else best
        final=minimize(lambda p:nll_phys(p,r,rlag,x,fam,usex),cand.x,method='L-BFGS-B',bounds=bds,
                       options={'maxiter':4000,'ftol':1e-13,'gtol':1e-8,'maxls':100})
        if np.isfinite(final.fun) and final.fun<best.fun: best=final
        elif np.isfinite(cand.fun) and cand.fun<best.fun: best=cand
    return best


def residuals(p,r,rlag,x,fam,usex):
    mu=p[0]; phi=p[1]; n=len(r); e=r-mu-phi*rlag; h=np.empty(n); h[0]=max(np.mean(e*e),1e-6)
    if fam==0: omega,alpha,beta,nu=p[2:6]; j=6
    else: omega,alpha,gamma,beta,nu=p[2:7]; j=7
    delta=p[j] if usex else 0.0; E=eabs_t.py_func(nu)
    for t in range(1,n):
        if fam==0:
            hv=omega+alpha*e[t-1]**2+beta*h[t-1]
            if usex: hv*=np.exp(np.clip(delta*x[t],-20,20))
        elif fam==2:
            hv=omega+(alpha+gamma*(e[t-1]<0))*e[t-1]**2+beta*h[t-1]
            if usex: hv*=np.exp(np.clip(delta*x[t],-20,20))
        else:
            zp=e[t-1]/np.sqrt(max(h[t-1],1e-12)); lh=omega+alpha*(abs(zp)-E)+gamma*zp+beta*np.log(max(h[t-1],1e-12))
            if usex: lh+=delta*x[t]
            hv=np.exp(np.clip(lh,-30,30))
        h[t]=hv
    return e/np.sqrt(h)

rows=[]
for ci,c in enumerate(selected,1):
    g=df[df.Country==c].sort_values('Date').copy(); g['rlag']=g.r.shift(1); g['xlag']=g.x.shift(1)
    g=g.dropna(subset=['r','rlag','xlag']); r=g.r.to_numpy(float); rlag=g.rlag.to_numpy(float); x=g.xlag.to_numpy(float)
    print(f'[{ci}/{len(selected)}] {c} N={len(r)}',flush=True)
    for fam,name in [(0,'GARCH'),(1,'EGARCH'),(2,'GJR/TGARCH')]:
        bfit=optimize_one(r,rlag,x,fam,False,None)
        basep=bfit.x.copy(); baseLL=-bfit.fun
        xfit=optimize_one(r,rlag,x,fam,True,basep)
        # ensure nesting: if X fails to beat base, use exact nested solution with delta=0
        nested=np.r_[basep,0.0]
        nested_nll=nll_phys(nested,r,rlag,x,fam,True)
        if xfit is None or xfit.fun>nested_nll+1e-7:
            class Obj: pass
            tmp=Obj(); tmp.x=nested; tmp.fun=nested_nll; tmp.success=True; xfit=tmp
        for usex,fit in [(False,bfit),(True,xfit)]:
            p=fit.x; ll=-fit.fun; k=len(p); z=residuals(p,r,rlag,x,fam,usex)
            try: lb=float(acorr_ljungbox(z*z,lags=[5],return_df=True).lb_pvalue.iloc[0])
            except: lb=np.nan
            try: ap=float(het_arch(z,nlags=5)[1])
            except: ap=np.nan
            if fam==0:
                mu,phi,omega,alpha,beta,nu=p[:6]; gamma=np.nan; delta=p[6] if usex else np.nan
            else:
                mu,phi,omega,alpha,gamma,beta,nu=p[:7]; delta=p[7] if usex else np.nan
            lr=max(0,2*(ll-baseLL)) if usex else np.nan; lrp=float(chi2.sf(lr,1)) if usex else np.nan
            rows.append(dict(Country=c,Correlation=sel_corr[c],Family=name,Model=name+('-X' if usex else ''),Uses_X=usex,N=len(r),loglik=ll,AIC=2*k-2*ll,BIC=k*np.log(len(r))-2*ll,converged=getattr(fit,'success',True),mu=mu,phi=phi,omega=omega,alpha=alpha,gamma=gamma,beta=beta,nu=nu,delta=delta,LR=lr,LR_p=lrp,LB_sq5_p=lb,ARCH_LM5_p=ap))

res=pd.DataFrame(rows); res['BH_FDR_q']=np.nan
for fam,idx in res[res.Uses_X].groupby('Family').groups.items(): res.loc[idx,'BH_FDR_q']=multipletests(res.loc[idx,'LR_p'].values,method='fdr_bh')[1]
res.to_csv(os.path.join(OUT,'garch_family_robust_all.csv'),index=False)
xr=res[res.Uses_X].copy().sort_values(['Country','Family']); xr.to_csv(os.path.join(OUT,'garch_x_robust.csv'),index=False)
best=res.loc[res.groupby('Country').AIC.idxmin(),['Country','Correlation','Model','AIC','BIC','loglik']].sort_values('Country'); best.to_csv(os.path.join(OUT,'best_model_aic.csv'),index=False)
sig=xr[xr.BH_FDR_q<.10].sort_values(['BH_FDR_q','Country']); sig.to_csv(os.path.join(OUT,'x_models_fdr_q10.csv'),index=False)
print('\nSIG q<.10')
print(sig[['Country','Family','delta','LR_p','BH_FDR_q','AIC','LB_sq5_p','ARCH_LM5_p']].to_string(index=False))
print('\nBEST')
print(best.to_string(index=False))
