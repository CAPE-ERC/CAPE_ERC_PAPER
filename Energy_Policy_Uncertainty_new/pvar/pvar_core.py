"""Panel VAR: estimation, diagnostics, IRFs, FEVDs for the EgPU quarterly panel."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats

VARS = ["egpu", "gdp_growth", "cpi_inflation"]
LABELS = {"egpu": "EgPU", "gdp_growth": "GDP growth", "cpi_inflation": "CPI inflation"}


# ---------------------------------------------------------------- panel prep

def panel_dimensions(df, entity="country", time="quarter"):
    """Section 1: establish and report the common panel before fitting."""
    d = df.copy()
    rows = []
    rows.append({"item": "observations", "value": len(d)})
    rows.append({"item": "countries", "value": d[entity].nunique()})
    rows.append({"item": "quarters", "value": d[time].nunique()})
    per = d.groupby(entity)[time].nunique()
    rows.append({"item": "quarters per country min", "value": int(per.min())})
    rows.append({"item": "quarters per country max", "value": int(per.max())})
    rows.append({"item": "balanced", "value": bool(per.nunique() == 1)})
    for v in VARS:
        rows.append({"item": f"missing {v}", "value": int(d[v].isna().sum())})
        rows.append({"item": f"zeros {v}", "value": int((d[v] == 0).sum())})
        rows.append({"item": f"min {v}", "value": round(float(d[v].min()), 3)})
        rows.append({"item": f"max {v}", "value": round(float(d[v].max()), 3)})
    return pd.DataFrame(rows)


def balanced_subset(df, entity="country", time="quarter", min_quarters=None):
    """Keep only countries with the modal (or requested) number of quarters."""
    d = df.copy()
    per = d.groupby(entity)[time].nunique()
    target = int(min_quarters) if min_quarters else int(per.mode().iloc[0])
    keep = per[per >= target].index
    return d[d[entity].isin(keep)].copy(), sorted(keep)


def winsorize_series(s, lo=0.01, hi=0.99):
    a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)


def quarterly_panel(monthly_egpu, macro, egpu_agg="mean"):
    """Build the analysis panel.

    monthly_egpu: country, year_month, egpu (monthly index)
    macro:        country, quarter, gdp_growth, cpi_inflation
    egpu_agg:     'mean' (3-month mean) or 'end' (last non-missing month of quarter)
    """
    m = monthly_egpu.copy()
    p = pd.PeriodIndex(m["year_month"].astype(str), freq="M")
    m["quarter"] = p.asfreq("Q").astype(str)
    m["qpos"] = p.month % 3                      # 1,2,0 within quarter
    if egpu_agg == "end":
        m = m.sort_values(["country", "year_month"])
        g = m.groupby(["country", "quarter"], as_index=False).tail(1)
    else:
        m = m.dropna(subset=["egpu"])
        g = m.groupby(["country", "quarter"], as_index=False)["egpu"].mean()
    out = pd.merge(g[["country", "quarter", "egpu"]], macro, on=["country", "quarter"], how="inner")
    return out.sort_values(["country", "quarter"]).reset_index(drop=True)


def two_way_demean(df, cols, entity="country", time="quarter"):
    """Balanced two-way within transformation: y - ybar_i - ybar_t + ybar."""
    d = df.copy()
    for c in cols:
        d[c] = (d[c] - d.groupby(entity)[c].transform("mean")
                     - d.groupby(time)[c].transform("mean") + d[c].mean())
    return d


def build_xy(df, p, cols=VARS, entity="country", time="quarter", demean=True):
    """Stack regression arrays for a balanced panel with p lags."""
    d = df.sort_values([entity, time]).copy()
    if demean:
        d = two_way_demean(d, cols, entity, time)
    T = d[time].nunique()
    N = d[entity].nunique()
    Y = d[cols].to_numpy(float).reshape(N, T, len(cols))
    X_parts, Y_parts = [], []
    for t in range(p, T):
        block = [Y[:, t - j, :] for j in range(1, p + 1)]
        X_parts.append(np.hstack(block))                 # N x (p*k)
        Y_parts.append(Y[:, t, :])                       # N x k
    X = np.vstack(X_parts); Yy = np.vstack(Y_parts)
    return X, Yy, N, T - p


# ---------------------------------------------------------------- estimation

def lag_select(df, p_max=4, cols=VARS, entity="country", time="quarter"):
    """Section 3: information criteria over p = 1..p_max."""
    rows = []
    for p in range(1, p_max + 1):
        X, Y, N, Teff = build_xy(df, p, cols, entity, time)
        B, *_ = np.linalg.lstsq(X, Y, rcond=None)
        E = Y - X @ B
        S = (E.T @ E) / E.shape[0]
        sign, logdet = np.linalg.slogdet(S)
        n = E.shape[0]
        k = p * len(cols) ** 2                      # free coefficients per system
        rows.append({"p": p, "logdet_Sigma": round(float(logdet), 4),
                     "AIC": round(float(logdet + 2 * k / n), 4),
                     "BIC": round(float(logdet + k * np.log(n) / n), 4),
                     "HQ": round(float(logdet + 2 * k * np.log(np.log(n)) / n), 4),
                     "observations": n})
    out = pd.DataFrame(rows)
    out.attrs["best"] = {"AIC": int(out.loc[out.AIC.idxmin(), "p"]),
                         "BIC": int(out.loc[out.BIC.idxmin(), "p"]),
                         "HQ": int(out.loc[out.HQ.idxmin(), "p"])}
    return out


def estimate_fe(df, p, cols=VARS, entity="country", time="quarter", cluster=True):
    """Two-way fixed-effects PVAR by within OLS. Nickell bias is -O(1/T): report it."""
    X, Y, N, Teff = build_xy(df, p, cols, entity, time)
    B, *_ = np.linalg.lstsq(X, Y, rcond=None)
    E = Y - X @ B
    n, q = X.shape
    k = len(cols)
    A = [B[j * k:(j + 1) * k, :].T for j in range(p)]
    Sigma = (E.T @ E) / n
    XtX_inv = np.linalg.pinv(X.T @ X)
    rows = []
    for i, var in enumerate(cols):
        u = E[:, i]
        if cluster:
            gid = np.repeat(np.arange(N), Teff)
            meat = np.zeros((q, q))
            for g in range(N):
                m = gid == g
                if m.sum() == 0: continue
                s = X[m].T @ u[m]
                meat += np.outer(s, s)
            Vi = XtX_inv @ meat @ XtX_inv * (N / max(N - 1, 1))
        else:
            Vi = Sigma[i, i] * XtX_inv
        se_i = np.sqrt(np.clip(np.diag(Vi), 0, None))
        for j in range(p):
            for m, other in enumerate(cols):
                idx = j * k + m
                b = float(B[idx, i]); s = float(se_i[idx])
                t = b / s if s > 0 else np.nan
                rows.append({"equation": var, "regressor": f"L{j+1}.{other}",
                             "coef": round(b, 4), "se": round(s, 4),
                             "t": round(t, 2) if np.isfinite(t) else np.nan,
                             "p": round(float(2 * (1 - stats.norm.cdf(abs(t)))), 4) if np.isfinite(t) else np.nan})
    return {"A": A, "Sigma": Sigma, "resid": E, "nobs": n, "N": N, "Teff": Teff,
            "method": "FE (two-way within OLS)", "coef_table": pd.DataFrame(rows),
            "se": "country-clustered" if cluster else "homoskedastic",
            "Amat": B}


def _year_diff_dummies(df, entity="country", time="quarter"):
    """First differences of year dummies, to absorb common annual shocks in FD."""
    q = pd.PeriodIndex(df[time].astype(str), freq="Q")
    yrs = q.year
    cats = sorted(set(yrs))[1:]
    D = pd.DataFrame({f"y{y}": (yrs == y).astype(float) for y in cats})
    d = df[[entity, time]].copy()
    D[entity] = df[entity].values; D[time] = df[time].values
    D = D.sort_values([entity, time])
    cols = [f"y{y}" for y in cats]
    D[cols] = D.groupby(entity)[cols].diff()
    return D.sort_index()[cols].fillna(0.0)


def estimate_gmm(df, p, cols=VARS, entity="country", time="quarter", depth=2,
                 two_step=True, year_dummies=True):
    """System GMM in first differences (Arellano-Bond style), collapsed instruments.

    FD of a levels VAR(p) keeps the same A_j coefficients. Instruments are lagged
    LEVELS of all variables, collapsed by lag distance, depth lags beyond p.
    Sigma_eps is recovered as Sigma_du / 2 (valid under white-noise innovations).
    """
    d = df.sort_values([entity, time]).reset_index(drop=True)
    T = d[time].nunique(); N = d[entity].nunique(); k = len(cols)
    Y = d[cols].to_numpy(float).reshape(N, T, k)
    DY = np.diff(Y, axis=1)
    if year_dummies:
        nd = _year_diff_dummies(d, entity, time).to_numpy(float).reshape(N, T, -1)
        DD = np.diff(nd, axis=1)
    else:
        DD = np.zeros((N, T, 0))
    nY = DD.shape[2]

    rowsX, rowsY, rowsZ, rowsG = [], [], [], []
    for t in range(p, T - 1):
        Xb = [DY[:, t - j, :] for j in range(1, p + 1)]
        if nY: Xb.append(DD[:, t, :])
        Zb = [Y[:, t + 1 - kk, :] for kk in range(p + 1, p + 1 + depth)]   # levels
        Ze = DD[:, t, :] if nY else np.zeros((N, 0))
        rowsX.append(np.hstack(Xb)); rowsY.append(DY[:, t, :])
        rowsZ.append(np.hstack(Zb + [Ze])); rowsG.append(np.arange(N))
    X = np.vstack(rowsX); Yv = np.vstack(rowsY); Z = np.vstack(rowsZ)
    G = np.concatenate(rowsG); n = X.shape[0]

    A_mats, resid_all, hansen = [], np.zeros((n, k)), []
    for eq in range(k):
        yv = Yv[:, eq]
        PzX = Z @ np.linalg.lstsq(Z, X, rcond=None)[0]
        b = np.linalg.lstsq(PzX, yv, rcond=None)[0]
        if two_step:
            u0 = yv - X @ b
            S = np.zeros((Z.shape[1], Z.shape[1]))
            for g in range(N):
                m = G == g
                if m.sum() == 0: continue
                s = Z[m].T @ u0[m]
                S += np.outer(s, s)
            W = np.linalg.pinv(S)
            Gmom = Z.T @ X                    # L x q, moment matrix
            b = np.linalg.lstsq(Gmom.T @ W @ Gmom, Gmom.T @ W @ (Z.T @ yv), rcond=None)[0]
            u = yv - X @ b
            g_ = Z.T @ u / n
            J = float(n * g_ @ W @ g_)
            df_j = int(Z.shape[1] - X.shape[1])
            hansen.append({"equation": cols[eq], "J": round(J, 3), "df": max(df_j, 0),
                           "p": round(float(1 - stats.chi2.cdf(J, max(df_j, 1))), 4),
                           "instruments": int(Z.shape[1]), "params": int(X.shape[1])})
        else:
            u = yv - X @ b
        resid_all[:, eq] = u
        A_mats.append(b[:p * k].copy())              # eq's coeffs, ordered [L1.v1..L1.vk, L2...]

    A = []
    for j in range(p):
        M = np.zeros((k, k))
        for eq in range(k):
            M[eq, :] = A_mats[eq][j * k:(j + 1) * k]
        A.append(M)
    Sigma = (resid_all.T @ resid_all) / n / 2.0
    tbl = []
    for eq, var in enumerate(cols):
        for j in range(p):
            for m, other in enumerate(cols):
                tbl.append({"equation": var, "regressor": f"L{j+1}.{other}",
                            "coef": round(float(A[j][eq, m]), 4)})
    return {"A": A, "Sigma": Sigma, "resid": resid_all, "nobs": n, "N": N,
            "Teff": max(T - 1 - p, 1),
            "method": f"System GMM in FD (depth={depth}, collapsed, "
                      f"{'two-step' if two_step else '2SLS'})",
            "se": "two-step GMM weight matrix", "hansen": pd.DataFrame(hansen),
            "instruments_per_eq": int(Z.shape[1]), "params_per_eq": int(X.shape[1]),
            "coef_table": pd.DataFrame(tbl), "G": G}


def ar_tests_gmm(res, cols=VARS):
    """Arellano-Bond AR(1)/AR(2) on FD residuals, country-clustered."""
    u = res["resid"]; G = res["G"]; out = []
    n = u.shape[0]
    for eq, name in enumerate(cols):
        uu = u[:, eq]
        for lag in (1, 2):
            yv = uu[lag:]
            preds = [uu[lag - r:n - r] for r in range(1, lag + 1)]
            Xa = np.column_stack([np.ones(len(yv))] + preds)
            b, *_ = np.linalg.lstsq(Xa, yv, rcond=None)
            e = yv - Xa @ b
            XtXi = np.linalg.pinv(Xa.T @ Xa)
            gg = G[lag:]
            M = np.zeros((Xa.shape[1], Xa.shape[1]))
            for g in np.unique(gg):
                m = gg == g
                if m.sum() < 2: continue
                s = Xa[m].T @ e[m]; M += np.outer(s, s)
            V = XtXi @ M @ XtXi * (len(np.unique(gg)) / (len(np.unique(gg)) - 1))
            se = float(np.sqrt(max(np.diag(V)[-1], 0)))
            t = float(b[-1] / se) if se > 0 else np.nan
            out.append({"test": f"AR({lag})", "equation": name,
                        "coef_lag": round(float(b[-1]), 4), "t": round(t, 2) if np.isfinite(t) else np.nan,
                        "p": round(float(2 * (1 - stats.norm.cdf(abs(t)))), 4) if np.isfinite(t) else np.nan})
    return pd.DataFrame(out)


def pesaran_cd(resid, entity="country", time="quarter", value_col=None):
    """Pesaran (2004) CD test on residuals against cross-sectional dependence."""
    r = resid.copy()
    if value_col is None:
        num = [c for c in r.columns
               if c not in (entity, time) and pd.api.types.is_numeric_dtype(r[c])]
        value_col = num[0]
    piv = r.pivot(index=time, columns=entity, values=value_col)
    X = piv.to_numpy(float)
    T, N = X.shape
    s = 0.0; cnt = 0
    for i in range(N):
        for j in range(i + 1, N):
            m = ~(np.isnan(X[:, i]) | np.isnan(X[:, j]))
            if m.sum() < 3: continue
            rho = np.corrcoef(X[m, i], X[m, j])[0, 1]
            if np.isfinite(rho): s += rho; cnt += 1
    if cnt == 0: return {"CD": np.nan, "p": np.nan, "pairs": 0}
    CD = np.sqrt(2 * T / cnt) * s
    return {"CD": round(float(CD), 3), "p": round(float(2 * (1 - stats.norm.cdf(abs(CD)))), 4),
            "pairs": cnt}


# ------------------------------------------------- stability, IRF, FEVD

def stability(A):
    """Section: companion-matrix eigenvalues must all lie inside the unit circle."""
    p = len(A); k = A[0].shape[0]
    F = np.zeros((k * p, k * p))
    F[:k, :k] = A[0]
    for j in range(1, p):
        F[:k, j * k:(j + 1) * k] = A[j]
        F[j * k:(j + 1) * k, (j - 1) * k:j * k] = np.eye(k)
    ev = np.linalg.eigvals(F)
    return {"eigenvalues": ev, "max_modulus": float(np.max(np.abs(ev))),
            "stable": bool(np.max(np.abs(ev)) < 1.0), "companion": F}


def _psi(A, H):
    """MA coefficients Psi_0..Psi_H of the levels VAR."""
    p = len(A); k = A[0].shape[0]
    psi = [np.eye(k)]
    for h in range(1, H + 1):
        m = np.zeros((k, k))
        for j in range(1, min(p, h) + 1):
            m += A[j - 1] @ psi[h - j]
        psi.append(m)
    return psi


def irf_generalized(A, Sigma, H=12):
    """Pesaran-Shin generalized IRFs: one-sd innovation, no ordering needed."""
    k = len(A[0]); psi = _psi(A, H)
    sd = np.sqrt(np.diag(Sigma))
    out = np.zeros((H + 1, k, k))          # [h, response, shock]
    for j in range(k):
        for h in range(H + 1):
            out[h, :, j] = psi[h] @ Sigma[:, j] / sd[j]
    return out


def irf_cholesky(A, Sigma, H=12, order=None):
    """Orthogonalized IRFs under an explicit recursive ordering."""
    k = len(A[0])
    order = list(range(k)) if order is None else list(order)
    S = Sigma[np.ix_(order, order)]
    P = np.linalg.cholesky(S)
    psi = _psi(A, H)
    out = np.zeros((H + 1, k, k))
    for h in range(H + 1):
        out[h] = (psi[h] @ P)
    return out[np.ix_(range(H + 1), order, order)], order


def fevd_generalized(A, Sigma, H=12):
    """Pesaran-Shin generalized FEVD, then row-normalized so shares sum to 100.

    theta_ij(h) = sum_{l<=h} (e_i' Psi_l Sigma e_j)^2 / sigma_jj
                  ---------------------------------------------------
                  sum_{l<=h} e_i' Psi_l Sigma Psi_l' e_i
    """
    k = len(A[0]); psi = _psi(A, H)
    sd = np.sqrt(np.diag(Sigma))
    num = np.zeros((H + 1, k, k)); den = np.zeros((H + 1, k))
    for h in range(H + 1):
        for l in range(h + 1):
            for i in range(k):
                for j in range(k):
                    num[h, i, j] += (psi[l][i, :] @ Sigma[:, j]) ** 2 / sd[j] ** 2
                den[h, i] += psi[l][i, :] @ Sigma @ psi[l][i, :]
    out = np.zeros((H + 1, k, k))
    for h in range(H + 1):
        for i in range(k):
            tot = num[h, i, :].sum()
            out[h, i, :] = num[h, i, :] / tot if tot > 0 else np.nan
    return out * 100.0


def fevd_cholesky(A, Sigma, H=12, order=None):
    k = len(A[0])
    order = list(range(k)) if order is None else list(order)
    S = Sigma[np.ix_(order, order)]
    P = np.linalg.cholesky(S); psi = _psi(A, H)
    out = np.zeros((H + 1, k, k))
    for h in range(H + 1):
        cum = sum((psi[j] @ P) @ (psi[j] @ P).T for j in range(h + 1))
        tot = np.diag(cum)
        for i in range(k):
            for j in range(k):
                out[h, i, j] = 100.0 * (cum[i, j] / tot[i]) if tot[i] > 0 else np.nan
    return out[np.ix_(range(H + 1), order, order)]


def bootstrap_irf(df, p, H=12, B=300, method="fe", seed=20261106, kind="generalized"):
    """Country-level bootstrap that re-estimates the full model each replication."""
    rng = np.random.default_rng(seed)
    countries = sorted(df["country"].unique())
    point = None
    draws = []
    for b in range(B):
        pick = rng.choice(countries, size=len(countries), replace=True)
        parts = []
        for new_id, c in enumerate(pick):
            d = df[df["country"] == c].copy()
            d["country"] = f"{c}__{new_id}"
            parts.append(d)
        db = pd.concat(parts, ignore_index=True)
        try:
            res = estimate_fe(db, p) if method == "fe" else estimate_gmm(db, p)
            if kind == "generalized":
                ir = irf_generalized(res["A"], res["Sigma"], H)
            else:
                ir, _ = irf_cholesky(res["A"], res["Sigma"], H)
            draws.append(ir)
        except Exception:
            continue
    if not draws:
        return None, 0
    arr = np.stack(draws)
    lo = np.percentile(arr, 5, axis=0); hi = np.percentile(arr, 95, axis=0)
    return {"lo": lo, "hi": hi, "draws": arr}, len(draws)


def panel_unit_root(df, cols=VARS, lags=2, reps=400, seed=7):
    """CIPS-style panel unit-root test with a simulated null critical value.

    Statistic: average cross-sectionally augmented ADF t-stat (Pesaran 2007 style).
    The finite-sample null distribution is simulated, not read from a table.
    """
    def cadf_t(panel):
        N, T, k = panel.shape
        ts = []
        for i in range(N):
            for v in range(k):
                y = panel[i, :, v]
                dy = np.diff(y)
                X = [np.ones(len(dy) - lags), y[lags:-1]]
                for j in range(1, lags + 1):
                    X.append(dy[lags - j:-j])
                X.append(panel[:, lags:-1, v].mean(axis=0))          # cross-section mean level
                X.append(np.diff(panel[:, :, v].mean(axis=0))[lags - 1:-1])  # mean dy
                X = np.column_stack(X)
                yy = dy[lags:]
                bb, *_ = np.linalg.lstsq(X, yy, rcond=None)
                e = yy - X @ bb
                s2 = e @ e / (len(yy) - X.shape[1])
                V = s2 * np.linalg.pinv(X.T @ X)
                ts.append(bb[1] / np.sqrt(V[1, 1]))
        return float(np.mean(ts))

    d = df.sort_values(["country", "quarter"])
    N = d["country"].nunique(); T = d["quarter"].nunique()
    panel = d[cols].to_numpy(float).reshape(N, T, len(cols))
    stat = cadf_t(panel)
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(reps):
        rw = np.cumsum(rng.normal(size=(N, T, len(cols))), axis=1)
        null.append(cadf_t(rw))
    crit = float(np.percentile(null, 5))
    return {"CIPS": round(stat, 3), "crit_5pct": round(crit, 3),
            "reject_unit_root_5pct": bool(stat < crit), "reps": reps}
