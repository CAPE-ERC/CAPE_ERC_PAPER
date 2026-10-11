"""Reproduce Monte Carlo exercises for constructed-target information-set treatment.
Default: 1,000 replications per DGP. Use --replications N for a smoke test.
Outputs target_information_monte_carlo.csv and NPY arrays.
"""
from pathlib import Path
import argparse, numpy as np, pandas as pd
N, NY, T, RELEASE, Y0 = 54, 11, 132, 5, 2015
OUT=Path(__file__).resolve().parent

def denton_map(ny):
    tt=12*ny; A=np.zeros((ny,tt))
    for j in range(ny): A[j,12*j:12*(j+1)]=1
    if ny==1: return np.ones((12,1))/12
    D=np.zeros((tt-1,tt)); i=np.arange(tt-1); D[i,i],D[i,i+1]=-1,1
    Q=D.T@D+np.eye(tt)*1e-9
    K=np.block([[Q,A.T],[A,np.zeros((ny,ny))]])
    B=np.zeros((tt+ny,ny)); B[tt:]=np.eye(ny)
    return np.linalg.solve(K,B)[:tt]
DM={n:denton_map(n) for n in range(1,NY+1)}

def make_features(annual,final):
    y=np.full((N,T),np.nan); y[:,12:]=100*np.log(final[:,12:]/final[:,:-12])
    fret=np.full((N,T,3),np.nan)
    for j in range(3): fret[:,14:,j]=y[:,14-j:T-j]
    fpub=np.full((N,T,3),np.nan)
    for origin in range(14,T):
        year,month=Y0+origin//12,origin%12+1
        avail=year-1 if month>=RELEASE else year-2; avail=max(Y0,min(Y0+NY-1,avail)); ny=avail-Y0+1
        hist=annual[:,:ny]@DM[ny].T
        if origin>=hist.shape[1]:
            r=np.log(annual[:,ny-1]/annual[:,ny-2])/12 if ny>=2 else np.zeros(N)
            extra=origin-hist.shape[1]+1; last=hist[:,-1]
            info=np.c_[hist,last[:,None]*np.exp(r[:,None]*np.arange(1,extra+1))]
        else: info=hist
        for j in range(3):
            d=origin-j; fpub[:,origin,j]=100*np.log(info[:,d]/info[:,d-12])
    return y,fret,fpub

def stack(F,y,z,h,dates):
    XX,ZZ,YY,CC=[],[],[],[]
    for td in dates:
        origin=td-h
        if origin<14: continue
        x=F[:,origin,:]; m=np.isfinite(x).all(1)&np.isfinite(y[:,td])&np.isfinite(z[:,origin]); ids=np.arange(N)[m]
        XX.append(x[m]); ZZ.append(z[m,origin]); YY.append(y[m,td]); CC.append(ids)
    return np.vstack(XX),np.concatenate(ZZ),np.concatenate(YY),np.concatenate(CC)

def evaluate(F,y,z,h,pub):
    train=[]
    for td in range(24,60):
        if pub:
            ty=Y0+td//12; release=(ty+1-Y0)*12+(RELEASE-1)
            if release>59: continue
        train.append(td)
    Xtr,ztr,ytr,ctr=stack(F,y,z,h,train); Xev,zev,yev,cev=stack(F,y,z,h,range(60,T))
    xm=np.zeros((N,3)); zm=np.zeros(N); ym=np.zeros(N)
    for c in range(N):
        m=ctr==c; xm[c]=Xtr[m].mean(0); zm[c]=ztr[m].mean(); ym[c]=ytr[m].mean()
    Xtr,ztr,ytr=Xtr-xm[ctr],ztr-zm[ctr],ytr-ym[ctr]; Xev,zev,yev=Xev-xm[cev],zev-zm[cev],yev-ym[cev]
    sx=Xtr.std(0); sx[sx<1e-8]=1; Xtr,Xev=Xtr/sx,Xev/sx
    b0=np.linalg.lstsq(Xtr,ytr,rcond=None)[0]; b1=np.linalg.lstsq(np.c_[Xtr,ztr],ytr,rcond=None)[0]
    f0=Xev@b0; f1=np.c_[Xev,zev]@b1
    return np.sqrt(np.mean((yev-f1)**2))/np.sqrt(np.mean((yev-f0)**2))

def replication(seed,kind):
    rng=np.random.default_rng(seed)
    if kind=='stress': ar,strength,noise=.95,.40,1.0
    else: ar,strength,noise=.25,.10,2.0
    common=np.zeros(NY)
    for yy in range(1,NY): common[yy]=.35*common[yy-1]+rng.normal(0,1)
    mu=rng.normal(3,1,N); ag=np.zeros((N,NY)); ag[:,0]=mu+.4*common[0]+rng.normal(0,2,N)
    for yy in range(1,NY): ag[:,yy]=mu+ar*(ag[:,yy-1]-mu)+.4*common[yy]+rng.normal(0,2,N)
    annual=np.empty((N,NY)); annual[:,0]=rng.lognormal(10,.7,N)
    for yy in range(1,NY): annual[:,yy]=annual[:,yy-1]*np.exp(ag[:,yy]/100)
    final=annual@DM[NY].T; y,fret,fpub=make_features(annual,final); z=np.empty((N,T))
    for tt in range(T):
        yy=tt//12
        z[:,tt]=rng.normal(0,1,N) if kind=='placebo' else strength*(ag[:,yy]-mu)+rng.normal(0,noise,N)
    z=(z-z[:,:48].mean(1,keepdims=True))/z[:,:48].std(1,ddof=1,keepdims=True)
    return np.array([[evaluate(fret,y,z,h,False),evaluate(fpub,y,z,h,True)] for h in [1,3,6,12]])

def summarize(label,arr):
    out=[]
    for hi,h in enumerate([1,3,6,12]):
        for di,d in enumerate(['Retrospective final-vintage','Publication-lagged']):
            v=arr[:,hi,di]; out.append(dict(DGP=label,Horizon=h,Design=d,Replications=len(arr),Mean_Relative_RMSFE=v.mean(),Median_Relative_RMSFE=np.median(v),P10_Relative_RMSFE=np.quantile(v,.1),P90_Relative_RMSFE=np.quantile(v,.9),Share_RMSFE_Improvement=np.mean(v<1)))
    return out
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--replications',type=int,default=1000); args=ap.parse_args(); R=args.replications
    cur=np.stack([replication(80000+i,'current') for i in range(R)])
    pla=np.stack([replication(90000+i,'placebo') for i in range(R)])
    stress=np.stack([replication(190000+i,'stress') for i in range(R)])
    pd.DataFrame(summarize('Current-state signal',cur)+summarize('Pure-noise placebo',pla)+summarize('Persistent-state stress',stress)).to_csv(OUT/'target_information_monte_carlo.csv',index=False)
    np.save(OUT/'current_state_signal.npy',cur); np.save(OUT/'pure_noise_placebo.npy',pla); np.save(OUT/'persistent_state_stress.npy',stress)
