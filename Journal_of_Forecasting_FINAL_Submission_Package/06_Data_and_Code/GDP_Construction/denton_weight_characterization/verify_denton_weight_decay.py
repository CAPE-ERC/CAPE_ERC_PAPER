from pathlib import Path
import numpy as np
import pandas as pd
from math import sqrt

OUT = Path(__file__).resolve().parent
M = 12
MU = (12*sqrt(438)-289)/143

# Closed-form local coefficients for month r within an annual block.
def local_coeffs(r):
    a = (r-12)*(3*r-13)/156
    b = r*(3*r-25)/132
    c = r*(12-r)/286
    return a,b,c

# Green function for the annual boundary-level recurrence
# (1/3)e_{y-1} + (578/429)e_y + (1/3)e_{y+1} = rhs_y.
a = 578/429
b = 1/3
K0 = 1/(a + 2*b*MU)
def K(n):
    return K0*(MU**abs(n))

def boundary_weight(boundary_offset, source_offset):
    n = boundary_offset-source_offset
    return K(n)/11 + K(n+1)/13

def monthly_weight(r, source_offset):
    aa,bb,cc = local_coeffs(r)
    direct = cc if source_offset == 0 else 0.0
    return aa*boundary_weight(-1, source_offset) + bb*boundary_weight(0, source_offset) + direct

profile=[]
for r in range(1,13):
    h0=monthly_weight(r,0)
    h1=monthly_weight(r,1)
    h2=monthly_weight(r,2)
    profile.append({
        'month_in_year': r,
        'own_year_weight': h0,
        'next_year_weight': h1,
        'second_future_year_weight': h2,
        'abs_next_to_own_ratio': abs(h1/h0),
        'tail_ratio_h2_over_h1': h2/h1,
    })
pd.DataFrame(profile).to_csv(OUT/'denton_interior_month_profile.csv', index=False)

pd.DataFrame({
    'additional_annual_steps': range(1,7),
    'abs_mu_power': [abs(MU)**j for j in range(1,7)]
}).to_csv(OUT/'denton_geometric_decay.csv', index=False)

# Finite 2015-2025 cross-check: 11 annual blocks = 132 months.
ny=11; T=ny*M
D=np.zeros((T-1,T))
for i in range(T-1):
    D[i,i]=-1; D[i,i+1]=1
Q=2*D.T@D
A=np.zeros((ny,T))
for y in range(ny):
    A[y,y*M:(y+1)*M]=1
KKT=np.block([[Q,A.T],[A,np.zeros((ny,ny))]])
rhs=np.vstack([np.zeros((T,ny)),np.eye(ny)])
H=np.linalg.solve(KKT,rhs)[:T,:]
checks=[]
for y0 in (3,4,5):
    for r in (1,6,12):
        row=y0*M+(r-1)
        for k in (1,2,3):
            if y0+k+1 < ny:
                ratio=H[row,y0+k+1]/H[row,y0+k]
                checks.append({
                    'base_year_index_0_is_2015': y0,
                    'month_in_year': r,
                    'future_offset_k': k,
                    'finite_tail_ratio': ratio,
                    'interior_mu': MU,
                    'absolute_difference': abs(ratio-MU),
                })
pd.DataFrame(checks).to_csv(OUT/'denton_finite_sample_crosscheck.csv', index=False)

print(f'mu={MU:.12f}')
print(f'max finite cross-check abs diff={max(x["absolute_difference"] for x in checks):.6g}')
