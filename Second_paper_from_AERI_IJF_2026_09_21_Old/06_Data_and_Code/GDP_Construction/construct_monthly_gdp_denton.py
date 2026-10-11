from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ANNUAL = HERE / "annual_gdp_ppp_weo_labeled_final_vintage_2015_2025.csv"
OUT = HERE / "monthly_gdp_ppp_denton_reproduced.csv"
years = list(range(2015, 2026))
n_years = len(years)
n_months = 12*n_years
A = np.zeros((n_years, n_months))
for j in range(n_years): A[j, 12*j:12*(j+1)] = 1.0
D = np.zeros((n_months-1, n_months))
for t in range(n_months-1): D[t,t], D[t,t+1] = -1.0, 1.0
Q = D.T @ D + np.eye(n_months)*1e-10
K = np.block([[Q, A.T], [A, np.zeros((n_years,n_years))]])
def disaggregate(v):
    rhs = np.r_[np.zeros(n_months), np.asarray(v,dtype=float)]
    return np.linalg.solve(K,rhs)[:n_months]
annual = pd.read_csv(ANNUAL)
dates = pd.date_range('2015-01-01','2025-12-01',freq='MS')
rows=[]
for _,r in annual.iterrows():
    x=disaggregate(r[[str(y) for y in years]].to_numpy(float))
    rows.extend((r['Country'],d,v) for d,v in zip(dates,x))
pd.DataFrame(rows,columns=['Country','Date','GDP_PPP_Denton_Monthly']).to_csv(OUT,index=False)
print(OUT)
