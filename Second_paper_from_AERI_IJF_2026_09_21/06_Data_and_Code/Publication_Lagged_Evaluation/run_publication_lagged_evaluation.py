from pathlib import Path
import os
import numpy as np,pandas as pd,statsmodels.api as sm
from scipy.stats import t as tdist
from statsmodels.stats.sandwich_covariance import cov_hac,cov_cluster_2groups
import re,unicodedata
BASE=Path(__file__).resolve().parents[1]
RELEASE_MONTH=int(os.environ.get('GDP_RELEASE_MONTH','5'))
OUT=Path(os.environ.get('OUTPUT_DIR',str(Path(__file__).resolve().parent)));OUT.mkdir(parents=True,exist_ok=True)
panel=pd.read_csv(BASE/'growth_real_economy_signal_gdp_panel.csv',parse_dates=['Date'])
annual=pd.read_csv(BASE/'GDP_Construction/annual_gdp_ppp_weo_labeled_final_vintage_2015_2025.csv')
# map annual names to panel keys via normalized country names

def norm(s): return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()).strip()
cmap=panel[['Country','Country_Key']].drop_duplicates(); cmap['nk']=cmap.Country.map(norm); mp=dict(zip(cmap.nk,cmap.Country_Key));annual['nk']=annual.Country.map(norm);annual['Country_Key']=annual.nk.map(mp)
for i,r in annual[annual.Country_Key.isna()].iterrows():
    cand=r.nk.replace(' ','_');
    if cand in set(panel.Country_Key): annual.loc[i,'Country_Key']=cand
manual={'burkina faso':'burkina_faso','cote d ivoire':'cote_divoire','democratic republic of congo':'democratic_republic_of_congo','republic of congo':'republic_of_congo'}
annual.loc[annual.Country_Key.isna(),'Country_Key']=annual.loc[annual.Country_Key.isna(),'nk'].map(manual)
assert annual.Country_Key.notna().all()
Y={r.Country_Key:{y:float(getattr(r,str(y))) if hasattr(r,str(y)) else float(r._asdict()[str(y)]) for y in range(2015,2026)} for r in []}
# easier dict rows
Y={}
for _,r in annual.iterrows(): Y[r.Country_Key]={y:float(r[str(y)]) for y in range(2015,2026)}

def denton(vals,years):
    n=len(years);T=12*n
    A=np.zeros((n,T));
    for j in range(n): A[j,12*j:12*(j+1)]=1
    if T==12:
        # flat is unique minimum first differences with sum constraint
        return np.repeat(vals[0]/12,12)
    D=np.zeros((T-1,T));
    for t in range(T-1):D[t,t],D[t,t+1]=-1,1
    Q=D.T@D+np.eye(T)*1e-10
    K=np.block([[Q,A.T],[A,np.zeros((n,n))]])
    rhs=np.r_[np.zeros(T),np.array(vals,float)]
    return np.linalg.solve(K,rhs)[:T]
cache={}
def avail_end(origin): return origin.year-1 if origin.month>=RELEASE_MONTH else origin.year-2

def info_series(country,origin):
    ae=max(2015,min(2025,avail_end(origin)));key=(country,ae)
    if key not in cache:
        yrs=list(range(2015,ae+1));vals=[Y[country][y] for y in yrs];x=denton(vals,yrs);dates=list(pd.date_range('2015-01-01',f'{ae}-12-01',freq='MS'));s=dict(zip(dates,x))
        # extrapolation monthly log trend from last two annual totals; flat if only one annual year
        if ae>=2016 and Y[country][ae-1]>0 and Y[country][ae]>0:r=np.log(Y[country][ae]/Y[country][ae-1])/12
        else:r=0.0
        last=pd.Timestamp(ae,12,1);lv=s[last]
        for d in pd.date_range(last+pd.offsets.MonthBegin(1),'2025-12-01',freq='MS'):
            lv=lv*np.exp(r);s[d]=lv
        cache[key]=s
    return cache[key]
# precompute origin features for all panel dates from 2016-03 onward
orig=panel[['Country','Country_Key','Date','TotalArticles','GrowthRealEconomyRisk','AERI','InflationRisk','FXExternalRisk']].rename(columns={'Date':'Origin'}).copy()
# frozen scaling 2015-2018
pre=panel[(panel.Date>='2015-01-01')&(panel.Date<='2018-12-01')]
for col in ['GrowthRealEconomyRisk','AERI','InflationRisk','FXExternalRisk']:
 st=pre.groupby('Country_Key')[col].agg(['mean','std']).rename(columns={'mean':f'{col}_m','std':f'{col}_s'})
 orig=orig.join(st,on='Country_Key');orig['z_'+col]=(orig[col]-orig[f'{col}_m'])/orig[f'{col}_s'].replace(0,1)
# info-set monthly 12m growth and lags at each origin; use same origin information set for t,t-1,t-2
features=[]
for r in orig.itertuples(index=False):
    o=pd.Timestamp(r.Origin)
    if o<pd.Timestamp('2016-03-01'): continue
    s=info_series(r.Country_Key,o)
    vals=[]
    ok=True
    for j in range(3):
        d=o-pd.offsets.MonthBegin(j);d12=d-pd.offsets.MonthBegin(12)
        if d not in s or d12 not in s or s[d]<=0 or s[d12]<=0: ok=False;break
        vals.append(100*np.log(s[d]/s[d12]))
    if ok: features.append((r.Country,r.Country_Key,o,*vals,r.TotalArticles,r._asdict()['z_GrowthRealEconomyRisk'],r._asdict()['z_AERI'],r._asdict()['z_InflationRisk'],r._asdict()['z_FXExternalRisk']))
feat=pd.DataFrame(features,columns=['Country','Country_Key','Origin','y_lag0','y_lag1','y_lag2','TotalArticles','zgre','z_AERI','z_InflationRisk','z_FXExternalRisk'])
feat.to_csv(OUT/'origin_specific_causal_features.csv',index=False)
targ=panel[['Country','Country_Key','Date','GDP_Growth12']].dropna().rename(columns={'Date':'target_date','GDP_Growth12':'y_target'})
def release_date(d):return pd.Timestamp(d.year+1,RELEASE_MONTH,1)

def run(sig='zgre',horizons=(1,3,6,12),eval_start='2020-01-01',eval_end='2025-12-01'):
 countries=sorted(panel.Country_Key.unique());nc=len(countries);SUM=[];ERR=[]
 for h in horizons:
  p=feat.copy();p['target_date']=p.Origin+pd.offsets.MonthBegin(h);p=p.merge(targ,on=['Country','Country_Key','target_date'],how='inner');p['target_release']=p.target_date.map(release_date);p=p.dropna(subset=['y_lag0','y_lag1','y_lag2',sig,'y_target']).reset_index(drop=True)
  codes=pd.Categorical(p.Country_Key,categories=countries).codes;cd=np.zeros((len(p),nc-1));ok=codes>0;cd[np.arange(len(p))[ok],codes[ok]-1]=1
  mons=p.target_date.dt.month.to_numpy();md=np.zeros((len(p),11));
  for m in range(2,13):md[:,m-2]=(mons==m)
  X0=np.column_stack([np.ones(len(p)),cd,p[['y_lag0','y_lag1','y_lag2']].to_numpy(),md]);X1=np.column_stack([X0,p[sig].to_numpy()]);y=p.y_target.to_numpy();outs=[]
  for td in pd.date_range(eval_start,eval_end,freq='MS'):
   origin=td-pd.offsets.MonthBegin(h);train=(p.target_release<=origin);test=(p.Origin==origin)
   if train.sum()<=X1.shape[1]+10 or test.sum()==0:continue
   b0=np.linalg.lstsq(X0[train],y[train],rcond=None)[0];b1=np.linalg.lstsq(X1[train],y[train],rcond=None)[0];ii=np.flatnonzero(test);o=p.iloc[ii][['Country','Country_Key','Origin','target_date','y_target']].copy();o['f_AR']=X0[ii]@b0;o['f_GRE']=X1[ii]@b1;o['Horizon']=h;o['signal']=sig;outs.append(o)
  if not outs: continue
  o=pd.concat(outs,ignore_index=True);e0=o.y_target-o.f_AR;e1=o.y_target-o.f_GRE;o['e0']=e0;o['e1']=e1;o['cw']=e0**2-(e1**2-(o.f_AR-o.f_GRE)**2);ERR.append(o)
  s=o.groupby('target_date').cw.mean();fit=sm.OLS(s.values,np.ones((len(s),1))).fit();se=np.sqrt(cov_hac(fit,nlags=max(h-1,0))[0,0]);th=float(s.mean()/se);ph=float(1-tdist.cdf(th,len(s)-1));mod=sm.OLS(o.cw.values,np.ones((len(o),1))).fit();cc=pd.Categorical(o.Country_Key).codes;tt=pd.Categorical(o.target_date).codes;cov,_,_=cov_cluster_2groups(mod,cc,tt);se2=np.sqrt(cov[0,0]);t2=float(o.cw.mean()/se2);df2=min(len(set(cc))-1,len(set(tt))-1);p2=float(1-tdist.cdf(t2,df2))
  SUM.append({'Signal':sig,'Horizon':h,'N':len(o),'TargetMonths':o.target_date.nunique(),'Benchmark_RMSFE':np.sqrt(np.mean(e0**2)),'GRE_RMSFE':np.sqrt(np.mean(e1**2)),'Relative_RMSFE':np.sqrt(np.mean(e1**2))/np.sqrt(np.mean(e0**2)),'Benchmark_MAE':np.mean(abs(e0)),'GRE_MAE':np.mean(abs(e1)),'Relative_MAE':np.mean(abs(e1))/np.mean(abs(e0)),'CW_HAC_p':ph,'CW_2Way_p':p2,'CW_HAC_t':th,'CW_2Way_t':t2})
 return pd.DataFrame(SUM),pd.concat(ERR,ignore_index=True) if ERR else pd.DataFrame()

s,e=run();s.to_csv(OUT/'causal_ar_main_horizons.csv',index=False);e.to_csv(OUT/'causal_ar_errors.csv',index=False);print('MAIN\n',s.to_string(index=False))
rows=[]
for sig in ['zgre','z_AERI','z_InflationRisk','z_FXExternalRisk']:
 ss,_=run(sig,horizons=(1,));rows.append(ss)
cmp=pd.concat(rows);cmp.to_csv(OUT/'causal_ar_text_comparators_h1.csv',index=False);print('\nH1 COMP\n',cmp.to_string(index=False))
# bootstraps for h1 and h12
rng=np.random.default_rng(20260914)
for h in [1,12]:
 g=e[e.Horizon==h].copy();m=g.groupby('target_date').agg(ss0=('e0',lambda x:float(np.sum(x*x))),ss1=('e1',lambda x:float(np.sum(x*x))),n=('e0','size'),cw=('cw','mean')).reset_index();T=len(m);L=12;B=5000;imp=[];cw=[]
 for b in range(B):
  idx=[]
  while len(idx)<T:
   st=int(rng.integers(0,max(1,T-L+1)));idx.extend(range(st,min(st+L,T)))
  z=m.iloc[idx[:T]];r0=np.sqrt(z.ss0.sum()/z.n.sum());r1=np.sqrt(z.ss1.sum()/z.n.sum());imp.append(100*(r0-r1)/r0);cw.append(z.cw.mean())
 imp=np.array(imp);cw=np.array(cw);actual=100*(np.sqrt(np.mean(g.e0**2))-np.sqrt(np.mean(g.e1**2)))/np.sqrt(np.mean(g.e0**2));pd.DataFrame([{'Horizon':h,'B':B,'block_months':L,'actual_improvement_pct':actual,'share_positive':np.mean(imp>0),'p2_5':np.quantile(imp,.025),'p5':np.quantile(imp,.05),'p95':np.quantile(imp,.95),'p97_5':np.quantile(imp,.975),'cw_boot_one_sided_p':(1+np.sum(cw<=0))/(B+1)}]).to_csv(OUT/f'causal_ar_bootstrap_h{h}.csv',index=False);print('\nBOOT',h,actual,np.quantile(imp,[.025,.05,.95,.975]),np.mean(imp>0),(1+np.sum(cw<=0))/(B+1))
# country ratios h1
h1=e[e.Horizon==1];cr=h1.groupby('Country_Key').apply(lambda g:pd.Series({'Relative_RMSFE':np.sqrt(np.mean(g.e1**2))/np.sqrt(np.mean(g.e0**2)),'N':len(g)}),include_groups=False).reset_index();cr.to_csv(OUT/'causal_ar_country_relative_rmsfe_h1.csv',index=False);print('H1 improve countries',sum(cr.Relative_RMSFE<1),'of',len(cr),'median',cr.Relative_RMSFE.median())
