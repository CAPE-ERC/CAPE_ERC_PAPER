"""Run the full PVAR protocol and save results + figures to pvar/outputs/."""
import json, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import pvar_core as pc

OUT = "outputs"; os.makedirs(OUT, exist_ok=True)
NAVY, RED, BLUE, GREY = "#1B3B6F", "#C0392B", "#2E6FB7", "#8C8C8C"
plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": "#777777",
                     "axes.labelcolor": "#333333", "axes.titlesize": 9.5})

# Audit MOD-02: the 18-country balanced candidate, 45 quarters 2015-Q1..2026-Q1
COUNTRIES = ["Angola","Benin","Botswana","Cape Verde","Egypt","Ghana","Ivory Coast",
             "Mauritius","Morocco","Mozambique","Namibia","Nigeria","Rwanda","Senegal",
             "South Africa","Tunisia","Uganda","Zambia"]
T = 45
QUARTERS = [f"{y}-Q{q}" for y in range(2015, 2027) for q in range(1, 5)][:T]

A1_TRUE = np.array([[0.62, -0.12, 0.08],
                    [-0.25, 0.55, 0.04],
                    [0.18, 0.10, 0.52]])
SIGMA_TRUE = np.array([[140.0, -2.5, 1.8],
                       [-2.5, 2.2, -0.4],
                       [1.8, -0.4, 1.2]])

def simulate(seed=20261106):
    """Known DGP: stable VAR(1) with country and quarter effects."""
    rng = np.random.default_rng(seed)
    mu = np.column_stack([rng.normal(100, 15, len(COUNTRIES)),
                          rng.normal(4.5, 1.5, len(COUNTRIES)),
                          rng.normal(7.0, 3.0, len(COUNTRIES))])
    tau = np.zeros((T, 3))
    tau[:, 0] = rng.normal(0, 5, T); tau[:, 1] = rng.normal(0, 0.6, T); tau[:, 2] = rng.normal(0, 1.0, T)
    q2020 = QUARTERS.index("2020-Q2"); q2022 = QUARTERS.index("2022-Q3")
    tau[q2020] += [35, -9, 2]; tau[q2022] += [12, -1.5, 3]
    eps = rng.multivariate_normal(np.zeros(3), SIGMA_TRUE, size=(len(COUNTRIES), T + 40))
    Y = np.zeros((len(COUNTRIES), T + 40, 3))
    c = ((np.eye(3) - A1_TRUE) @ mu.T).T          # so that E[y] = mu
    Y[:, 0, :] = mu + eps[:, 0, :]
    for t in range(1, T + 40):
        tau_t = tau[t] if t < T else tau[-1]
        # y_t = (I-A)mu + A y_{t-1} + tau_t + eps_t  (additive effects, as specified)
        Y[:, t] = c + tau_t + Y[:, t-1] @ A1_TRUE.T + eps[:, t]
    Y = Y[:, 40:, :]
    rows = []
    for i, c in enumerate(COUNTRIES):
        for t, q in enumerate(QUARTERS):
            rows.append({"country": c, "quarter": q, "egpu": Y[i, t, 0],
                         "gdp_growth": Y[i, t, 1], "cpi_inflation": Y[i, t, 2]})
    return pd.DataFrame(rows)

df = simulate()
df.to_csv(f"{OUT}/panel_simulated.csv", index=False)

# ---- 1. panel dimensions
pc.panel_dimensions(df).to_csv(f"{OUT}/panel_dimensions.csv", index=False)
print("panel:", df.shape, "| countries:", df.country.nunique(), "| quarters:", df.quarter.nunique())

# ---- 2. unit roots and cross-sectional dependence
ur = pc.panel_unit_root(df, reps=300)
pd.DataFrame([ur]).to_csv(f"{OUT}/unit_root.csv", index=False)
print("unit root:", ur)

# ---- 3. lag selection
lag = pc.lag_select(df, p_max=4)
lag.to_csv(f"{OUT}/lag_selection.csv", index=False)
print(lag.to_string(index=False)); print("best:", lag.attrs["best"])

P = 1   # information criteria select p=1 in the DGP; verify from lag table
if lag.attrs["best"]["BIC"] != 1:
    P = int(lag.attrs["best"]["BIC"])

# ---- 4. estimation
fe = pc.estimate_fe(df, P)
gmm = pc.estimate_gmm(df, P, depth=2, two_step=True)
fe["coef_table"].to_csv(f"{OUT}/coef_fe.csv", index=False)
gmm["coef_table"].to_csv(f"{OUT}/coef_gmm.csv", index=False)
gmm["hansen"].to_csv(f"{OUT}/hansen.csv", index=False)
ar = pc.ar_tests_gmm(gmm); ar.to_csv(f"{OUT}/ar_tests.csv", index=False)
print("\nFE A1:\n", np.round(fe["A"][0], 3))
print("GMM A1:\n", np.round(gmm["A"][0], 3))
print("TRUE A1:\n", A1_TRUE)

# ---- 5. stability
st = pc.stability(fe["A"]); stg = pc.stability(gmm["A"])
pd.DataFrame([{"estimator": "FE", "max_modulus": round(st["max_modulus"], 4), "stable": st["stable"]},
              {"estimator": "GMM", "max_modulus": round(stg["max_modulus"], 4), "stable": stg["stable"]}
              ]).to_csv(f"{OUT}/stability.csv", index=False)
print("stability FE:", round(st["max_modulus"], 4), st["stable"], "| GMM:", round(stg["max_modulus"], 4))

# ---- 6. first-stage strength of the GMM instruments
def first_stage_strength(df, p, depth=2):
    import pvar_core as pc
    from pvar_core import _year_diff_dummies
    d = df.sort_values(["country","quarter"]).reset_index(drop=True)
    T = d["quarter"].nunique(); N = d["country"].nunique(); k = 3
    Y = d[["egpu","gdp_growth","cpi_inflation"]].to_numpy(float).reshape(N, T, k)
    DY = np.diff(Y, axis=1)
    nd = _year_diff_dummies(d).to_numpy(float).reshape(N, T, -1); DD = np.diff(nd, axis=1)
    Xs, Zs = [], []
    for t in range(p, T-1):
        Xs.append(DY[:, t-1, :]); Zs.append(np.hstack([Y[:, t+1-kk, :] for kk in range(p+1, p+1+depth)]))
    X = np.vstack(Xs); Z = np.vstack(Zs)
    out = []
    for j in range(k):
        x = X[:, j]
        # partial out exogenous dummies from x and Z
        out.append({"endogenous": ["egpu","gdp_growth","cpi_inflation"][j],
                    "instruments": Z.shape[1], "partial_R2": None, "F": None})
    return pd.DataFrame(out)

# partial R2 / F for each endogenous regressor against its instruments
def fs_table(df, p=1, depth=2):
    from pvar_core import _year_diff_dummies
    from scipy import stats as st
    d = df.sort_values(["country","quarter"]).reset_index(drop=True)
    T = d["quarter"].nunique(); N = d["country"].nunique()
    Y = d[["egpu","gdp_growth","cpi_inflation"]].to_numpy(float).reshape(N, T, 3)
    DY = np.diff(Y, axis=1)
    Xs, Zs = [], []
    for t in range(p, T-1):
        Xs.append(DY[:, t-1, :]); Zs.append(np.hstack([Y[:, t+1-kk, :] for kk in range(p+1, p+1+depth)]))
    X = np.vstack(Xs); Z = np.vstack(Zs)
    rows = []
    for j, nm in enumerate(["egpu","gdp_growth","cpi_inflation"]):
        x = X[:, j]; Zc = np.column_stack([np.ones(len(Z)), Z])
        b, *_ = np.linalg.lstsq(Zc, x, rcond=None)
        e = x - Zc @ b
        r2 = 1 - (e @ e) / ((x - x.mean()) @ (x - x.mean()))
        q = Z.shape[1]; n = len(x)
        F = (r2 / q) / ((1 - r2) / (n - q - 1))
        rows.append({"endogenous": nm, "instruments": q, "partial_R2": round(float(r2), 3),
                     "F": round(float(F), 1), "p": round(float(1 - st.f.cdf(F, q, n - q - 1)), 4)})
    return pd.DataFrame(rows)

fs = fs_table(df); fs.to_csv(f"{OUT}/gmm_first_stage.csv", index=False)
print("\nGMM first stage:\n", fs.to_string(index=False))

# ---- 7. Monte Carlo validation of the estimators against the known DGP
def monte_carlo(reps=20):
    rows = []
    for r in range(reps):
        d = simulate(seed=1000 + r)
        fe_r = pc.estimate_fe(d, 1)
        try:
            gm_r = pc.estimate_gmm(d, 1)
        except Exception:
            gm_r = None
        for est, res in (("FE", fe_r), ("GMM", gm_r)):
            if res is None: continue
            for i in range(3):
                for j in range(3):
                    rows.append({"rep": r, "estimator": est, "resp": i, "expl": j,
                                 "value": float(res["A"][0][i, j]), "truth": float(A1_TRUE[i, j])})
    return pd.DataFrame(rows)

mc = monte_carlo(20); mc.to_csv(f"{OUT}/monte_carlo.csv", index=False)
mcs = mc.groupby(["estimator","resp","expl"]).agg(mean=("value","mean"),
                                                  sd=("value","std"),
                                                  truth=("truth","first")).reset_index()
mcs["bias"] = mcs["mean"] - mcs["truth"]
mcs["rmse"] = np.sqrt(mcs["bias"]**2 + mcs["sd"]**2)
mcs.round(3).to_csv(f"{OUT}/monte_carlo_summary.csv", index=False)
print("\nMonte Carlo (20 reps), bias by estimator:\n", mcs.round(3).to_string(index=False))

# ---- 8. IRFs: generalized (primary) and Cholesky (ordering sensitivity)
H = 12
gir = pc.irf_generalized(fe["A"], fe["Sigma"], H)
gir_gmm = pc.irf_generalized(gmm["A"], gmm["Sigma"], H)
orderings = {"EgPU first": [0, 1, 2], "EgPU last": [1, 2, 0], "CPI, EgPU, GDP": [2, 0, 1]}
chol = {k: pc.irf_cholesky(fe["A"], fe["Sigma"], H, order=o)[0] for k, o in orderings.items()}

rows = []
for s in range(3):
    for r in range(3):
        for h in range(H + 1):
            rows.append({"shock": pc.LABELS[pc.VARS[s]], "response": pc.LABELS[pc.VARS[r]],
                         "h": h, "girf": round(float(gir[h, r, s]), 3),
                         "girf_gmm": round(float(gir_gmm[h, r, s]), 3)})
pd.DataFrame(rows).to_csv(f"{OUT}/irf_generalized.csv", index=False)

rows = []
for name, arr in chol.items():
    for s in range(3):
        for r in range(3):
            for h in range(H + 1):
                rows.append({"ordering": name, "shock": pc.LABELS[pc.VARS[s]],
                             "response": pc.LABELS[pc.VARS[r]], "h": h,
                             "irf": round(float(arr[h, r, s]), 3)})
pd.DataFrame(rows).to_csv(f"{OUT}/irf_cholesky.csv", index=False)

boot, B = pc.bootstrap_irf(df, P, H=H, B=200, method="fe", seed=20261106, kind="generalized")
print(f"\nbootstrap: {B} replications")

# ---- 9. FEVD, with the sum-to-100 check the instruction requires
gv = pc.fevd_generalized(fe["A"], fe["Sigma"], H)
checks = [{"h": h, "min_row_sum": round(float(np.nanmin(gv[h].sum(axis=1))), 6),
           "max_row_sum": round(float(np.nanmax(gv[h].sum(axis=1))), 6)} for h in range(H + 1)]
pd.DataFrame(checks).to_csv(f"{OUT}/fevd_row_sums.csv", index=False)
print("FEVD row sums (should be 100):", checks[0], checks[-1])

rows = []
for h in (1, 4, 8, 12):
    for r in range(3):
        for s in range(3):
            rows.append({"h": h, "variable": pc.LABELS[pc.VARS[r]], "shock": pc.LABELS[pc.VARS[s]],
                         "share_pct": round(float(gv[h, r, s]), 2)})
pd.DataFrame(rows).to_csv(f"{OUT}/fevd_generalized.csv", index=False)
pd.DataFrame([{"variable": pc.LABELS[pc.VARS[r]], "shock": pc.LABELS[pc.VARS[s]],
               "share_pct": round(float(gv[H, r, s]), 2)} for r in range(3) for s in range(3)]
             ).to_csv(f"{OUT}/fevd_summary_h12.csv", index=False)

# ---- 10. diagnostics summary
_cs = sorted(df["country"].unique()); _qs = sorted(df["quarter"].unique())
_c_list = _cs * fe["Teff"]
_q_list = [q for q in _qs[P:] for _ in range(len(_cs))]
_resid_df = pd.DataFrame({"country": _c_list, "quarter": _q_list, "r": fe["resid"][:, 0]})
cd_test = pc.pesaran_cd(_resid_df)
diag = [
    {"check": "sample", "result": f"{fe['nobs']} obs, {fe['N']} countries, {fe['Teff']} quarters per country",
     "verdict": "INFO"},
    {"check": "lag order", "result": f"BIC selects p={lag.attrs['best']['BIC']}; AIC p={lag.attrs['best']['AIC']}; HQ p={lag.attrs['best']['HQ']}",
     "verdict": "INFO"},
    {"check": "panel unit root (CIPS)", "result": f"{ur['CIPS']} vs 5% crit {ur['crit_5pct']}",
     "verdict": "PASS" if ur["reject_unit_root_5pct"] else "FAIL"},
    {"check": "stability FE", "result": f"max |eig| = {st['max_modulus']:.3f}", "verdict": "PASS" if st["stable"] else "FAIL"},
    {"check": "stability GMM", "result": f"max |eig| = {stg['max_modulus']:.3f}", "verdict": "PASS" if stg["stable"] else "FAIL"},
    {"check": "AR(1) FD residuals", "result": "; ".join(f"{r.equation}: t={r.t}" for r in ar[ar.test=='AR(1)'].itertuples()),
     "verdict": "INFO"},
    {"check": "AR(2) FD residuals", "result": "; ".join(f"{r.equation}: p={r.p}" for r in ar[ar.test=='AR(2)'].itertuples()),
     "verdict": "PASS" if (ar[ar.test=='AR(2)'].p > 0.05).all() else "REVIEW"},
    {"check": "Hansen J", "result": "; ".join(f"{r.equation}: J={r.J} p={r.p}" for r in gmm["hansen"].itertuples()),
     "verdict": "PASS" if (gmm["hansen"].p > 0.05).all() else "REVIEW"},
    {"check": "instrument count", "result": f"{gmm['instruments_per_eq']} instruments vs {gmm['N']} countries",
     "verdict": "REVIEW" if gmm["instruments_per_eq"] > gmm["N"] else "PASS"},
    {"check": "GMM first stage", "result": "; ".join(f"{r.endogenous}: R2={r.partial_R2}, F={r.F}" for r in fs.itertuples()),
     "verdict": "REVIEW" if (fs.partial_R2 < 0.3).any() else "PASS"},
    {"check": "Pesaran CD (EgPU residuals)", "result": f"CD={cd_test['CD']}, p={cd_test['p']}", "verdict": "INFO"},
    {"check": "Nickell bias FE", "result": f"approx -1/T = {-1/fe['Teff']:.3f} per coefficient; GMM removes it",
     "verdict": "INFO"},
    {"check": "real EgPU panel (audit MOD-04..06)", "result": "NOT ESTIMATED: audit contains dimensions only, no observations",
     "verdict": "NOT RUN"},
]
pd.DataFrame(diag).to_csv(f"{OUT}/diagnostics_summary.csv", index=False)
print("\ndiagnostics written")

# ---------------- FIGURES ----------------
# fig 1: stability
fig, ax = plt.subplots(figsize=(4.2, 3.6), dpi=200)
th = np.linspace(0, 2*np.pi, 300)
ax.plot(np.cos(th), np.sin(th), color=GREY, lw=1, ls="--")
ax.scatter(st["eigenvalues"].real, st["eigenvalues"].imag, s=70, color=NAVY,
           edgecolor="white", zorder=3, label=f"FE (max |eig| = {st['max_modulus']:.2f})")
ax.scatter(stg["eigenvalues"].real, stg["eigenvalues"].imag, s=55, color=RED, marker="^",
           edgecolor="white", zorder=3, label=f"GMM (max |eig| = {stg['max_modulus']:.2f})")
ax.axhline(0, color="#DDDDDD", lw=0.8); ax.axvline(0, color="#DDDDDD", lw=0.8)
ax.set_xlim(-1.15, 1.15); ax.set_ylim(-1.15, 1.15); ax.set_aspect("equal")
ax.set_xlabel("Real part"); ax.set_ylabel("Imaginary part")
ax.set_title("Companion-matrix eigenvalues vs unit circle", color=NAVY, fontweight="bold")
ax.legend(frameon=False, fontsize=7.5, loc="upper left")
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/fig1_stability.png"); plt.close(fig)

# fig 2: lag selection
fig, ax = plt.subplots(figsize=(5.2, 3.2), dpi=200)
for col, c, m in (("AIC", NAVY, "o"), ("BIC", RED, "s"), ("HQ", BLUE, "^")):
    ax.plot(lag["p"], lag[col], marker=m, color=c, lw=1.4, ms=5, label=col)
ax.set_xlabel("Lag order p"); ax.set_ylabel("Information criterion")
ax.set_title("Lag selection: information criteria, p = 1 to 4", color=NAVY, fontweight="bold")
ax.grid(axis="y", color="#EEEEEE"); ax.legend(frameon=False, fontsize=7.5)
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/fig2_lag_selection.png"); plt.close(fig)

# fig 3: generalized IRFs with bootstrap bands
fig, axes = plt.subplots(3, 3, figsize=(8.6, 6.6), dpi=200, sharex=True)
hs = np.arange(H + 1)
for si in range(3):
    for ri in range(3):
        ax = axes[ri, si]
        point = gir[:, ri, si]
        ax.axhline(0, color="#BBBBBB", lw=0.8)
        if boot:
            ax.fill_between(hs, boot["lo"][:, ri, si], boot["hi"][:, ri, si],
                            color=NAVY, alpha=0.16, lw=0)
        ax.plot(hs, point, color=NAVY, lw=1.6)
        ax.plot(hs, point, "o", color="white", mec=NAVY, ms=3.4, mew=0.9)
        if ri == 0: ax.set_title(f"Shock: {pc.LABELS[pc.VARS[si]]}", color=NAVY, fontweight="bold")
        if si == 0: ax.set_ylabel(pc.LABELS[pc.VARS[ri]], fontsize=8)
        if ri == 2: ax.set_xlabel("Quarters after shock")
        ax.grid(axis="y", color="#F0F0F0")
        for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.suptitle("Generalized IRFs, one-SD innovation, 90% country-bootstrap bands (B=200)",
             fontsize=9.5, color="#333333")
fig.tight_layout(rect=[0, 0, 1, 0.96]); fig.savefig(f"{OUT}/fig3_irf_generalized.png"); plt.close(fig)

# fig 4: ordering sensitivity for the EgPU shock
fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.2), dpi=200)
colors = {"EgPU first": NAVY, "EgPU last": RED, "CPI, EgPU, GDP": BLUE}
for ax, ri, lab in ((axes[0], 1, "GDP growth"), (axes[1], 2, "CPI inflation")):
    ax.axhline(0, color="#BBBBBB", lw=0.8)
    for name, arr in chol.items():
        ax.plot(hs, arr[:, ri, 0], color=colors[name], lw=1.4, label=name)
    ax.plot(hs, gir[:, ri, 0], color="black", lw=1.1, ls=":", label="Generalized")
    ax.set_title(f"EgPU shock to {lab}", color=NAVY, fontweight="bold", fontsize=9)
    ax.set_xlabel("Quarters after shock"); ax.grid(axis="y", color="#F0F0F0")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
axes[0].set_ylabel("Index / percentage points")
axes[1].legend(frameon=False, fontsize=7, loc="best")
fig.suptitle("Identification sensitivity: recursive orderings versus generalized", fontsize=9.5, color="#333333")
fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(f"{OUT}/fig4_ordering.png"); plt.close(fig)

# fig 5: FEVD stacked bars
fig, axes = plt.subplots(1, 3, figsize=(8.8, 3.1), dpi=200, sharey=True)
hs_sel = [1, 4, 8, 12]
stack_cols = {"EgPU": NAVY, "GDP growth": BLUE, "CPI inflation": RED}
for ri, ax in enumerate(axes):
    bottom = np.zeros(len(hs_sel))
    for si, nm in enumerate(["EgPU", "GDP growth", "CPI inflation"]):
        vals = [gv[h, ri, si] for h in hs_sel]
        ax.bar([str(h) for h in hs_sel], vals, bottom=bottom, color=stack_cols[nm],
               edgecolor="white", lw=0.6, label=nm)
        bottom += np.array(vals)
    ax.set_title(f"{pc.LABELS[pc.VARS[ri]]}", color=NAVY, fontweight="bold", fontsize=9)
    ax.set_xlabel("Horizon h (quarters)"); ax.set_ylim(0, 100)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
axes[0].set_ylabel("Share of forecast-error variance (%)")
axes[2].legend(frameon=False, fontsize=7, loc="lower right")
fig.suptitle("Generalized FEVD, row-normalized (shares sum to 100)", fontsize=9.5, color="#333333")
fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(f"{OUT}/fig5_fevd.png"); plt.close(fig)

# fig 6: Monte Carlo validation
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.3), dpi=200, sharey=True)
names = [f"{pc.LABELS[pc.VARS[int(r.resp)]]}\n<- {pc.LABELS[pc.VARS[int(r.expl)]]}"
         for r in mcs[mcs.estimator == "FE"].itertuples()]
for ax, est, colr in ((axes[0], "FE", NAVY), (axes[1], "GMM", RED)):
    sub = mcs[mcs.estimator == est].reset_index(drop=True)
    ax.errorbar(range(len(sub)), sub["mean"], yerr=1.96*sub["sd"], fmt="o", color=colr,
                ms=4, lw=1, capsize=2, label="mean estimate, 95% MC interval")
    ax.scatter(range(len(sub)), sub["truth"], marker="_", s=180, color="black", label="true value")
    ax.axhline(0, color="#DDDDDD", lw=0.8)
    ax.set_title(f"{est} estimator vs truth (20 replications)", color=NAVY, fontweight="bold", fontsize=9)
    ax.grid(axis="y", color="#F0F0F0")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
axes[0].set_xticks(range(len(names))); axes[0].set_xticklabels(names, fontsize=6.5)
axes[0].legend(frameon=False, fontsize=7)
fig.suptitle("Parameter recovery: known DGP", fontsize=9.5, color="#333333")
fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(f"{OUT}/fig6_validation.png"); plt.close(fig)

# fig 7: simulated Nigeria series
fig, axes = plt.subplots(3, 1, figsize=(7.4, 5.4), dpi=200, sharey=False)
ng = df[df.country == "Nigeria"]
x = np.arange(len(ng))
for ax, col, lab, c in ((axes[0], "egpu", "EgPU index", NAVY),
                        (axes[1], "gdp_growth", "Real GDP growth (%, y/y)", BLUE),
                        (axes[2], "cpi_inflation", "CPI inflation (%)", RED)):
    ax.plot(x, ng[col], color=c, lw=1.5); ax.plot(x, ng[col], "o", color="white", mec=c, ms=3)
    ax.set_ylabel(lab, fontsize=8); ax.grid(axis="y", color="#F0F0F0")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
axes[2].set_xticks(x[::4]); axes[2].set_xticklabels([q.replace("-Q", "Q") for q in ng.quarter][::4], fontsize=7)
axes[0].set_title("Simulated panel, Nigeria (known DGP, not index data)", color=NAVY, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/fig7_series.png"); plt.close(fig)

print("\nfigures:", sorted(f for f in os.listdir(OUT) if f.endswith(".png")))
