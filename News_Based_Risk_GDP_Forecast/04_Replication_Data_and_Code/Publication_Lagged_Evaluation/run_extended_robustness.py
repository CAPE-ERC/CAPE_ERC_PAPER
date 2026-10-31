from pathlib import Path
import re, unicodedata
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import t as tdist
from statsmodels.stats.sandwich_covariance import cov_hac, cov_cluster_2groups

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OUT = HERE / 'extended_robustness'
OUT.mkdir(parents=True, exist_ok=True)

panel = pd.read_csv(BASE/'GDP_Construction'/'gre_gdp_panel_denton.csv', parse_dates=['Date'])
feat = pd.read_csv(HERE/'origin_specific_causal_features.csv', parse_dates=['Origin'])
targ = panel[['Country','Country_Key','Date','GDP_Growth12']].dropna().rename(columns={'Date':'target_date','GDP_Growth12':'y_target'})
countries = sorted(panel.Country_Key.unique())

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def release_date(d, release_month=5):
    return pd.Timestamp(d.year + 1, release_month, 1)

def one_sided_cw_summary(o, h=1):
    o = o.copy()
    o['e0'] = o.y_target - o.f0
    o['e1'] = o.y_target - o.f1
    o['cw'] = o.e0**2 - (o.e1**2 - (o.f0-o.f1)**2)
    s = o.groupby('target_date').cw.mean()
    fit = sm.OLS(s.values, np.ones((len(s),1))).fit()
    se = np.sqrt(cov_hac(fit, nlags=max(h-1,0))[0,0])
    t_hac = float(s.mean()/se)
    p_hac = float(1-tdist.cdf(t_hac, len(s)-1))
    mod = sm.OLS(o.cw.values, np.ones((len(o),1))).fit()
    cc = pd.Categorical(o.Country_Key).codes
    tt = pd.Categorical(o.target_date).codes
    cov,_,_ = cov_cluster_2groups(mod, cc, tt)
    se2 = np.sqrt(cov[0,0])
    t2 = float(o.cw.mean()/se2)
    df2 = min(len(set(cc))-1, len(set(tt))-1)
    p2 = float(1-tdist.cdf(t2,df2))
    return {
        'N':len(o),'TargetMonths':o.target_date.nunique(),
        'Benchmark_RMSFE':float(np.sqrt(np.mean(o.e0**2))),
        'Signal_RMSFE':float(np.sqrt(np.mean(o.e1**2))),
        'Relative_RMSFE':float(np.sqrt(np.mean(o.e1**2))/np.sqrt(np.mean(o.e0**2))),
        'Benchmark_MAE':float(np.mean(np.abs(o.e0))),
        'Signal_MAE':float(np.mean(np.abs(o.e1))),
        'Relative_MAE':float(np.mean(np.abs(o.e1))/np.mean(np.abs(o.e0))),
        'CW_HAC_t':t_hac,'CW_HAC_p':p_hac,'CW_2Way_t':t2,'CW_2Way_p':p2,
    }

def forecast_with_extra(p, signal_col, factor_cols=(), h=1, release_month=5):
    p = p.copy()
    p['target_date'] = p.Origin + pd.offsets.MonthBegin(h)
    p = p.merge(targ, on=['Country','Country_Key','target_date'], how='inner')
    p['target_release'] = p.target_date.map(lambda d: release_date(d,release_month))
    needed = ['y_lag0','y_lag1','y_lag2',signal_col,'y_target'] + list(factor_cols)
    p = p.dropna(subset=needed).reset_index(drop=True)
    nc = len(countries)
    codes = pd.Categorical(p.Country_Key, categories=countries).codes
    cd = np.zeros((len(p),nc-1)); ok = codes>0
    cd[np.arange(len(p))[ok], codes[ok]-1] = 1
    mons = p.target_date.dt.month.to_numpy(); md = np.zeros((len(p),11))
    for m in range(2,13): md[:,m-2] = (mons==m)
    X0 = np.column_stack([np.ones(len(p)),cd,p[['y_lag0','y_lag1','y_lag2']].to_numpy(),md,p[list(factor_cols)].to_numpy() if factor_cols else np.empty((len(p),0))])
    X1 = np.column_stack([X0,p[signal_col].to_numpy()])
    y = p.y_target.to_numpy(); outs=[]
    for td in pd.date_range('2020-01-01','2025-12-01',freq='MS'):
        origin = td-pd.offsets.MonthBegin(h)
        train = p.target_release<=origin; test = p.Origin==origin
        if train.sum()<=X1.shape[1]+10 or test.sum()==0: continue
        b0 = np.linalg.lstsq(X0[train],y[train],rcond=None)[0]
        b1 = np.linalg.lstsq(X1[train],y[train],rcond=None)[0]
        ii = np.flatnonzero(test)
        o = p.iloc[ii][['Country','Country_Key','Origin','target_date','y_target']].copy()
        o['f0'] = X0[ii]@b0; o['f1'] = X1[ii]@b1
        outs.append(o)
    return pd.concat(outs,ignore_index=True)

# -----------------------------------------------------------------------------
# 1. Mechanism: stale annual-information set versus post-release months
# -----------------------------------------------------------------------------
release_files = {
    'May': (5, HERE/'causal_ar_errors.csv'),
    'July': (7, HERE/'release_month_sensitivity'/'july_errors.csv'),
    'November': (11, HERE/'release_month_sensitivity'/'november_errors.csv'),
}
rows=[]; stacked=[]
for name,(rm,path) in release_files.items():
    d = pd.read_csv(path,parse_dates=['Origin','target_date'])
    d = d[d.Horizon==1].copy()
    d['State'] = np.where(d.Origin.dt.month<rm,'Stale pre-release','Refreshed post-release')
    d['ReleaseConvention'] = name; d['ReleaseMonth'] = rm
    d['raw_gain'] = d.e0**2-d.e1**2
    d['info_age_months'] = np.where(d.Origin.dt.month>=rm,d.Origin.dt.month,d.Origin.dt.month+12)
    stacked.append(d)
    for state,g in d.groupby('State'):
        s = g.groupby('target_date').cw.mean()
        fit = sm.OLS(s.values,np.ones((len(s),1))).fit()
        se = np.sqrt(cov_hac(fit,nlags=0)[0,0])
        th = float(s.mean()/se); ph = float(1-tdist.cdf(th,len(s)-1))
        rows.append({
            'ReleaseConvention':name,'ReleaseMonth':rm,'State':state,
            'N':len(g),'TargetMonths':g.target_date.nunique(),
            'Relative_RMSFE':float(np.sqrt(np.mean(g.e1**2))/np.sqrt(np.mean(g.e0**2))),
            'Relative_MAE':float(np.mean(np.abs(g.e1))/np.mean(np.abs(g.e0))),
            'CW_HAC_t':th,'CW_HAC_p':ph,
        })
mechanism = pd.DataFrame(rows)
mechanism.to_csv(OUT/'mechanism_stale_information.csv',index=False)

# Stacked convention diagnostic: does incremental gain rise monotonically with information age?
st = pd.concat(stacked,ignore_index=True)
ag = st.groupby(['ReleaseConvention','Origin','info_age_months'],as_index=False).agg(raw_gain=('raw_gain','mean'),cw=('cw','mean'))
age_rows=[]
for dep in ['raw_gain','cw']:
    X = pd.concat([
        ag[['info_age_months']].reset_index(drop=True),
        pd.get_dummies(ag.Origin.dt.strftime('%Y-%m'),prefix='origin',drop_first=True,dtype=float).reset_index(drop=True),
        pd.get_dummies(ag.ReleaseConvention,prefix='release',drop_first=True,dtype=float).reset_index(drop=True),
    ],axis=1)
    X = sm.add_constant(X)
    mod = sm.OLS(ag[dep].to_numpy(),X).fit(cov_type='cluster',cov_kwds={'groups':pd.Categorical(ag.Origin).codes})
    age_rows.append({'Outcome':dep,'beta_info_age':mod.params['info_age_months'],'SE_cluster_origin':mod.bse['info_age_months'],'t':mod.tvalues['info_age_months'],'p_two_sided':mod.pvalues['info_age_months'],'N':len(ag)})
pd.DataFrame(age_rows).to_csv(OUT/'mechanism_information_age_regression.csv',index=False)

# Does GRE predict the revision from publication-lagged current growth to final-vintage growth at the origin?
final_at_origin = panel[['Country_Key','Date','GDP_Growth12']].rename(columns={'Date':'Origin','GDP_Growth12':'final_growth_at_origin'})
eval_pairs = pd.read_csv(HERE/'causal_ar_errors.csv',parse_dates=['Origin','target_date'])
eval_pairs = eval_pairs[eval_pairs.Horizon==1][['Country_Key','Origin']].drop_duplicates()
rev = feat.merge(final_at_origin,on=['Country_Key','Origin'],how='left').merge(eval_pairs,on=['Country_Key','Origin'],how='inner')
rev['revision'] = rev.final_growth_at_origin-rev.y_lag0
rev = rev.dropna(subset=['revision','zgre']).reset_index(drop=True)
X = pd.concat([
    rev[['zgre']],
    pd.get_dummies(rev.Country_Key,prefix='country',drop_first=True,dtype=float),
    pd.get_dummies(rev.Origin.dt.strftime('%Y-%m'),prefix='origin',drop_first=True,dtype=float),
],axis=1)
X = sm.add_constant(X)
mod = sm.OLS(rev.revision.to_numpy(),X).fit()
cov,_,_ = cov_cluster_2groups(mod,pd.Categorical(rev.Country_Key).codes,pd.Categorical(rev.Origin).codes)
i = list(X.columns).index('zgre'); se=np.sqrt(cov[i,i]); t=float(mod.params['zgre']/se)
p2 = float(2*(1-tdist.cdf(abs(t),min(rev.Country_Key.nunique()-1,rev.Origin.nunique()-1))))
pd.DataFrame([{'Outcome':'final_growth_at_origin_minus_publication_lagged_growth','beta_zGRE':mod.params['zgre'],'SE_two_way':se,'t':t,'p_two_sided':p2,'N':len(rev)}]).to_csv(OUT/'mechanism_revision_regression.csv',index=False)

# -----------------------------------------------------------------------------
# 2. Article-level exact-text deduplication sensitivity for GRE
# -----------------------------------------------------------------------------
def key(s):
    return re.sub(r'[^a-z0-9]+','',unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower())
ded = pd.read_csv(BASE/'Scoring_Documentation'/'Article_Level_Sensitivity'/'aeri_pillars_country_period.csv')
ded['Country_Key'] = ded.Country.map(key); ded['Origin'] = pd.to_datetime(ded.Period+'-01')
pre = ded[(ded.Origin>='2015-01-01')&(ded.Origin<='2018-12-01')]
stats = pre.groupby('Country_Key').GrowthRealEconomyRisk.agg(['mean','std']).rename(columns={'mean':'m','std':'s'})
ded = ded.join(stats,on='Country_Key'); ded['zgre_dedup']=(ded.GrowthRealEconomyRisk-ded.m)/ded.s.replace(0,1)
f = feat.merge(ded[['Country_Key','Origin','zgre_dedup']],on=['Country_Key','Origin'],how='left')
# Common sample: require deduplicated GRE for both original and deduplicated runs.
f = f[f.zgre_dedup.notna()].copy()
ded_rows=[]
for sig,label in [('zgre','Original GRE, common sample'),('zgre_dedup','Exact-text-deduplicated GRE')]:
    o = forecast_with_extra(f,sig,h=1)
    smry = one_sided_cw_summary(o,h=1); smry['Signal']=label
    ded_rows.append(smry)
pd.DataFrame(ded_rows).to_csv(OUT/'deduplicated_GRE_forecast_sensitivity.csv',index=False)
# Level correlation of original and deduplicated GRE before standardization.
orig = panel[['Country_Key','Date','GrowthRealEconomyRisk']].rename(columns={'Date':'Origin','GrowthRealEconomyRisk':'GRE_original'})
lev = orig.merge(ded[['Country_Key','Origin','GrowthRealEconomyRisk']],on=['Country_Key','Origin'],how='inner').rename(columns={'GrowthRealEconomyRisk':'GRE_deduplicated'})
within = lev.groupby('Country_Key').apply(lambda g:g.GRE_original.corr(g.GRE_deduplicated),include_groups=False)
pd.DataFrame([{
    'CommonCountryMonths':len(lev),
    'Pearson':lev[['GRE_original','GRE_deduplicated']].corr().iloc[0,1],
    'Spearman':lev[['GRE_original','GRE_deduplicated']].corr(method='spearman').iloc[0,1],
    'MedianWithinCountryCorrelation':within.median(),
}]).to_csv(OUT/'deduplicated_GRE_level_correlation.csv',index=False)

# -----------------------------------------------------------------------------
# 3. Genuine wide macro factor benchmark
#    Candidate information set: cross-country publication-lagged GDP growth plus
#    lagged inflation and FX depreciation. Retain series with >=24 pre-evaluation
#    observations; freeze means, SDs, and PCA loadings using 2016-03--2018-12.
#    Number of factors is the minimum needed to explain >=80% of pre-evaluation variance.
# -----------------------------------------------------------------------------
wg = feat.pivot(index='Origin',columns='Country_Key',values='y_lag0'); wg.columns=['GDP_'+c for c in wg.columns]
macro = panel[['Country_Key','Date','Inflation_Raw','FX_Change_Raw']]
factor_rows=[]
for macro_lag in [1,2]:
    mac = macro.copy(); mac['Origin']=mac.Date+pd.offsets.MonthBegin(macro_lag)
    wi=mac.pivot(index='Origin',columns='Country_Key',values='Inflation_Raw'); wi.columns=['INF_'+c for c in wi.columns]
    wx=mac.pivot(index='Origin',columns='Country_Key',values='FX_Change_Raw'); wx.columns=['FX_'+c for c in wx.columns]
    W=wg.join(wi,how='outer').join(wx,how='outer').sort_index()
    preW=W.loc[(W.index>=pd.Timestamp('2016-03-01'))&(W.index<=pd.Timestamp('2018-12-01'))]
    counts=preW.notna().sum(); cols=list(counts[counts>=24].index)
    mu=preW[cols].mean(); sd=preW[cols].std(ddof=1)
    cols=[c for c in cols if pd.notna(sd[c]) and sd[c]>1e-10]
    Z=((preW[cols]-mu[cols])/sd[cols]).fillna(0).to_numpy()
    U,S,Vt=np.linalg.svd(Z,full_matrices=False); cum=np.cumsum(S**2)/np.sum(S**2)
    k=int(np.searchsorted(cum,.80)+1)
    load=Vt[:k].T
    ZA=((W[cols]-mu[cols])/sd[cols]).fillna(0).to_numpy()
    factors=pd.DataFrame(ZA@load,index=W.index,columns=[f'MF{i+1}' for i in range(k)]).reset_index().rename(columns={'index':'Origin'})
    f=feat.merge(factors,on='Origin',how='left')
    factor_cols=[f'MF{i+1}' for i in range(k)]
    o=forecast_with_extra(f,'zgre',factor_cols=factor_cols,h=1)
    smry=one_sided_cw_summary(o,h=1)
    smry.update({'MacroLagMonths':macro_lag,'CandidateMacroSeries':len(W.columns),'RetainedMacroSeries':len(cols),'Factors':k,'CumulativeVarianceExplained':float(cum[k-1])})
    factor_rows.append(smry)
pd.DataFrame(factor_rows).to_csv(OUT/'wide_macro_factor_benchmark_h1.csv',index=False)

print('Wrote extended robustness outputs to',OUT)
