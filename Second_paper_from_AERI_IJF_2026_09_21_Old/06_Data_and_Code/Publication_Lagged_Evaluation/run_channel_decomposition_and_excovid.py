from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import t as tdist
from statsmodels.stats.sandwich_covariance import cov_hac,cov_cluster_2groups
BASE=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent/'evidence_upgrade';OUT.mkdir(parents=True,exist_ok=True)
panel=pd.read_csv(BASE/'growth_real_economy_signal_gdp_panel.csv',parse_dates=['Date'])
feat=pd.read_csv(Path(__file__).resolve().parent/'origin_specific_causal_features.csv',parse_dates=['Origin'])
final=panel[['Country','Country_Key','Date','GDP_Growth12']].copy()
for j in range(3): final[f'fv_lag{j}']=final.groupby('Country_Key')['GDP_Growth12'].shift(j)
final=final.rename(columns={'Date':'Origin'})[['Country','Country_Key','Origin','fv_lag0','fv_lag1','fv_lag2']]
feat=feat.merge(final,on=['Country','Country_Key','Origin'],how='left')
targ=panel[['Country','Country_Key','Date','GDP_Growth12']].dropna().rename(columns={'Date':'target_date','GDP_Growth12':'y_target'})
countries=sorted(panel.Country_Key.unique()); nc=len(countries)
def release_date(d): return pd.Timestamp(d.year+1,5,1)

def infer_two_sided(d,h):
    s=d.groupby('target_date')['metric'].mean().sort_index()
    mod=sm.OLS(s.values,np.ones((len(s),1))).fit(); se=np.sqrt(cov_hac(mod,nlags=max(h-1,0))[0,0]); t=float(s.mean()/se); p=float(2*(1-tdist.cdf(abs(t),len(s)-1)))
    mod2=sm.OLS(d.metric.values,np.ones((len(d),1))).fit(); cc=pd.Categorical(d.Country_Key).codes; tt=pd.Categorical(d.target_date).codes
    cov,_,_=cov_cluster_2groups(mod2,cc,tt); se2=float(np.sqrt(cov[0,0])); t2=float(d.metric.mean()/se2); df=min(len(set(cc))-1,len(set(tt))-1); p2=float(2*(1-tdist.cdf(abs(t2),df)))
    return dict(mean=float(d.metric.mean()),hac_t=t,hac_p=p,two_way_t=t2,two_way_p=p2,target_months=len(s),N=len(d))

def solve(A,b):
    try:return np.linalg.solve(A,b)
    except np.linalg.LinAlgError:return np.linalg.pinv(A)@b

def build_design(h,use_causal_lags,delay_training,eval_start='2020-01-01',eval_end='2025-12-01'):
    p=feat.copy();p['target_date']=p.Origin+pd.offsets.MonthBegin(h);p=p.merge(targ,on=['Country','Country_Key','target_date'],how='inner')
    lagcols=['y_lag0','y_lag1','y_lag2'] if use_causal_lags else ['fv_lag0','fv_lag1','fv_lag2']
    p=p.dropna(subset=lagcols+['zgre','y_target']).reset_index(drop=True);p['avail']=p.target_date.map(release_date) if delay_training else p.target_date
    codes=pd.Categorical(p.Country_Key,categories=countries).codes;cd=np.zeros((len(p),nc-1));ok=codes>0;cd[np.arange(len(p))[ok],codes[ok]-1]=1
    mons=p.target_date.dt.month.to_numpy();md=np.zeros((len(p),11));
    for m in range(2,13):md[:,m-2]=(mons==m)
    X0=np.column_stack([np.ones(len(p)),cd,p[lagcols].to_numpy(),md]);X1=np.column_stack([X0,p.zgre.to_numpy()]);y=p.y_target.to_numpy()
    order=np.argsort(p.avail.values); pos=0; A0=np.zeros((X0.shape[1],X0.shape[1]));b0=np.zeros(X0.shape[1]);A1=np.zeros((X1.shape[1],X1.shape[1]));b1=np.zeros(X1.shape[1]);outs=[]
    eval_tds=pd.date_range(eval_start,eval_end,freq='MS')
    for td in eval_tds:
        origin=td-pd.offsets.MonthBegin(h)
        while pos<len(order) and p.avail.iloc[order[pos]]<=origin:
            i=order[pos];x0=X0[i];x1=X1[i];yy=y[i];A0+=np.outer(x0,x0);b0+=x0*yy;A1+=np.outer(x1,x1);b1+=x1*yy;pos+=1
        if pos<=X1.shape[1]+10:continue
        test=np.flatnonzero(p.Origin.values==np.datetime64(origin))
        if len(test)==0:continue
        B0=solve(A0,b0);B1=solve(A1,b1);o=p.iloc[test][['Country','Country_Key','Origin','target_date','y_target']].copy();o['f0']=X0[test]@B0;o['f1']=X1[test]@B1;o['e0']=o.y_target-o.f0;o['e1']=o.y_target-o.f1;o['raw_gain']=o.e0**2-o.e1**2;o['cw_gain']=o.e0**2-(o.e1**2-(o.f0-o.f1)**2);outs.append(o)
    return pd.concat(outs,ignore_index=True)
labels={'R':(False,False,'Retrospective: final-vintage lags + immediate training'),'L':(True,False,'Lag-corrected only: publication-lagged GDP lags + immediate training'),'T':(False,True,'Training-corrected only: final-vintage lags + delayed outcomes'),'P':(True,True,'Fully publication-lagged: feasible GDP lags + delayed outcomes')}
summary=[]; allerrs={}
for h in [1,3,6,12]:
  for k,(cl,dt,desc) in labels.items():
    o=build_design(h,cl,dt);allerrs[(h,k)]=o;r0=np.sqrt(np.mean(o.e0**2));r1=np.sqrt(np.mean(o.e1**2));summary.append(dict(Horizon=h,Design=k,Description=desc,N=len(o),Benchmark_RMSFE=r0,GRE_RMSFE=r1,Relative_RMSFE=r1/r0,Benchmark_MAE=np.mean(abs(o.e0)),GRE_MAE=np.mean(abs(o.e1)),Relative_MAE=np.mean(abs(o.e1))/np.mean(abs(o.e0)),Raw_gain_mean=np.mean(o.raw_gain),CW_gain_mean=np.mean(o.cw_gain)))
pd.DataFrame(summary).to_csv(OUT/'channel_design_summary.csv',index=False)
rows=[]
for h in [1,12]:
  base=allerrs[(h,'R')][['Country_Key','target_date','raw_gain','cw_gain']].rename(columns={'raw_gain':'raw_R','cw_gain':'cw_R'})
  for k in ['L','T','P']:
    q=allerrs[(h,k)][['Country_Key','target_date','raw_gain','cw_gain']].rename(columns={'raw_gain':f'raw_{k}','cw_gain':f'cw_{k}'});base=base.merge(q,on=['Country_Key','target_date'])
  for metric in ['raw','cw']:
    comps={'Total information-set correction (P-R)':base[f'{metric}_P']-base[f'{metric}_R'],'GDP-lag channel (Shapley average)':.5*((base[f'{metric}_L']-base[f'{metric}_R'])+(base[f'{metric}_P']-base[f'{metric}_T'])),'Training-timing channel (Shapley average)':.5*((base[f'{metric}_T']-base[f'{metric}_R'])+(base[f'{metric}_P']-base[f'{metric}_L']))}
    for name,v in comps.items():
      d=base[['Country_Key','target_date']].copy();d['metric']=v.values;rows.append(dict(Horizon=h,Loss=metric,Contrast=name,**infer_two_sided(d,h)))
pd.DataFrame(rows).to_csv(OUT/'formal_design_difference_tests.csv',index=False)

# Paired target-month block bootstrap for the nonlinear relative-RMSFE contrast at h=12.
# This preserves contemporaneous cross-country dependence and 12-month overlap.
def rel_rmsfe_monthly_arrays(o):
    g=o.groupby('target_date').apply(lambda z: pd.Series({
        'e0sq': float(np.sum(z.e0.to_numpy()**2)),
        'e1sq': float(np.sum(z.e1.to_numpy()**2)),
        'n': int(len(z))
    }))
    return g.sort_index()

h12m={k:rel_rmsfe_monthly_arrays(allerrs[(12,k)]) for k in labels}
common_months=sorted(set.intersection(*[set(v.index) for v in h12m.values()]))
h12m={k:v.loc[common_months] for k,v in h12m.items()}

def rel_from_counts(a, counts):
    w=np.asarray(counts,dtype=float)
    n=float(np.sum(w*a['n'].to_numpy()))
    m0=float(np.sum(w*a['e0sq'].to_numpy())/n)
    m1=float(np.sum(w*a['e1sq'].to_numpy())/n)
    return np.sqrt(m1)/np.sqrt(m0)

ones=np.ones(len(common_months))
rr={k:rel_from_counts(v,ones) for k,v in h12m.items()}
actual=np.array([
    rr['P']-rr['R'],
    .5*((rr['L']-rr['R'])+(rr['P']-rr['T'])),
    .5*((rr['T']-rr['R'])+(rr['P']-rr['L']))
])
rng=np.random.default_rng(20260921)
B=5000; block=12; M=len(common_months)
draws=np.zeros((B,3))
for b in range(B):
    ids=[]
    while len(ids)<M:
        st=int(rng.integers(M))
        ids.extend([(st+j)%M for j in range(block)])
    counts=np.bincount(np.asarray(ids[:M]),minlength=M)
    rb={k:rel_from_counts(v,counts) for k,v in h12m.items()}
    draws[b,0]=rb['P']-rb['R']
    draws[b,1]=.5*((rb['L']-rb['R'])+(rb['P']-rb['T']))
    draws[b,2]=.5*((rb['T']-rb['R'])+(rb['P']-rb['L']))
boot=[]
for j,name in enumerate(['Total P-R','GDP-lag Shapley','Training timing Shapley']):
    lo,hi=np.quantile(draws[:,j],[.025,.975])
    boot.append(dict(Contrast=name,Actual=float(actual[j]),p2_5=float(lo),p97_5=float(hi),share_positive=float(np.mean(draws[:,j]>0)),Draws=B,BlockMonths=block))
pd.DataFrame(boot).to_csv(OUT/'paired_block_bootstrap_relative_rmsfe_design_difference_h12.csv',index=False)

# h12 errors
pd.concat([allerrs[(12,k)].assign(Design=k) for k in labels],ignore_index=True).to_csv(OUT/'channel_decomposition_h12_errors.csv',index=False)
# Ex-COVID 2022-2025 for R and P
xc=[]
for h in [1,3,6,12]:
  for k in ['R','P']:
    cl,dt,desc=labels[k];o=build_design(h,cl,dt,'2022-01-01','2025-12-01');r0=np.sqrt(np.mean(o.e0**2));r1=np.sqrt(np.mean(o.e1**2));s=o.groupby('target_date').cw_gain.mean();mod=sm.OLS(s.values,np.ones((len(s),1))).fit();se=np.sqrt(cov_hac(mod,nlags=max(h-1,0))[0,0]);th=float(s.mean()/se);ph=float(1-tdist.cdf(th,len(s)-1));mod2=sm.OLS(o.cw_gain.values,np.ones((len(o),1))).fit();cc=pd.Categorical(o.Country_Key).codes;tt=pd.Categorical(o.target_date).codes;cov,_,_=cov_cluster_2groups(mod2,cc,tt);se2=np.sqrt(cov[0,0]);t2=float(o.cw_gain.mean()/se2);df=min(len(set(cc))-1,len(set(tt))-1);p2=float(1-tdist.cdf(t2,df));xc.append(dict(Horizon=h,Design=k,Description=desc,N=len(o),TargetMonths=o.target_date.nunique(),Benchmark_RMSFE=r0,GRE_RMSFE=r1,Relative_RMSFE=r1/r0,Benchmark_MAE=np.mean(abs(o.e0)),GRE_MAE=np.mean(abs(o.e1)),Relative_MAE=np.mean(abs(o.e1))/np.mean(abs(o.e0)),CW_HAC_p=ph,CW_2Way_p=p2))
pd.DataFrame(xc).to_csv(OUT/'excovid_2022_2025_results.csv',index=False)
print('H12 DESIGNS');print(pd.DataFrame(summary).query('Horizon==12').to_string(index=False));print('\nFORMAL');print(pd.DataFrame(rows).to_string(index=False));print('\nEXCOVID');print(pd.DataFrame(xc).to_string(index=False))
