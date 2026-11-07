# EgPU PVAR: estimation, diagnostics, IRFs, FEVDs

Implements the PVAR specification in the instruction: y_it = sum_j A_j y_{i,t-j} + mu_i + tau_t + eps_it,
with y = (EgPU, GDP growth, CPI inflation), quarterly.

## What was and was not estimated

**Not estimated on real data.** The attached `egpu_data_readiness_audit.csv` contains
dimensions and diagnostics, not observations: it has 25 checks (7,607 country-month
index rows, 54 countries, 141 months) but no EgPU, GDP, or CPI values by
country-quarter. Its own rows MOD-04, MOD-05 and MOD-06 are marked NOT RUN. No
coefficient, IRF, or FEVD in this package is an estimate of the real EgPU panel.

**Estimated on a calibration panel.** To prove the machinery works end to end, the
pipeline runs on a simulated panel with the exact dimensions the audit reports for its
balanced candidate (MOD-02): the same 18 countries, 45 quarters (2015-Q1 to 2026-Q1),
810 observations, from a known stationary VAR(1) with country and quarter effects. The
known DGP makes the run a validation exercise: the estimators can be scored against the
truth (see `outputs/monte_carlo_summary.csv` and `outputs/fig6_validation.png`).

## Running it on the real panel

Prepare a long CSV with columns `country, quarter, egpu, gdp_growth, cpi_inflation`
(quarter as `2025-Q1`). Then:

    python -c "
    import pandas as pd, pvar_run_real as pr
    df = pd.read_csv('egpu_quarterly_panel.csv')
    pr.run(df, out='outputs_real')"

or edit `pvar_run.py`: replace `df = simulate()` with
`df = pd.read_csv('egpu_quarterly_panel.csv')` and keep everything after it.
`pvar_core.quarterly_panel()` builds that file from the monthly index plus the macro
sheets, with `egpu_agg='mean'` (3-month mean) or `'end'` (last month of the quarter);
run both to satisfy the aggregation-sensitivity check.

## Estimators

| estimator | what it does | known limitation |
|---|---|---|
| FE (two-way within OLS) | removes country and quarter effects, country-clustered SEs | Nickell bias of order -1/T (about -0.023 per coefficient at T=44) |
| GMM in first differences | Arellano-Bond style: lagged levels as instruments, collapsed, depth 2, two-step, Hansen J, AR(1)/AR(2) | weak instruments for EgPU (partial R2 = 0.14), high variance |

The Monte Carlo comparison (20 replications, `fig6`) shows the expected trade-off: GMM
has the smaller bias on the persistent diagonal (0.022 versus -0.031 for FE) and far
larger variance on the EgPU cross-terms (sd 0.54 to 0.73). Report both; do not present
GMM as automatically superior.

## Results on the calibration panel (illustrative, not the real index)

- Lag selection: BIC and HQ choose p = 1 (the true lag); AIC chooses p = 4.
- Stability: max |eigenvalue| = 0.751 (FE) and 0.922 (GMM). Both inside the unit circle.
- AR(2) in differenced residuals: p = 0.054 (EgPU), 0.49, 0.80: no second-order serial
  correlation at 5 percent.
- Hansen J: p ~ 1.00 (valid instruments in a synthetic DGP; expect a real test to bite).
- Instrument count: 17 instruments against 18 countries: at the limit, not over it.
- Generalized IRF, EgPU shock: GDP growth -3.12 index/pp at h=1, -3.32 at h=2, fading to
  -0.19 by h=12; CPI +2.21 at h=1 fading to 0.06; EgPU itself decays from 11.90 to 0.18.
- Generalized FEVD at h=12: EgPU variance 94.1 percent own-shock; GDP growth 83.1 percent
  from EgPU; CPI 83.2 percent from EgPU, 12.2 percent own.

## Identification

Generalized IRFs are the primary presentation (ordering-free, descriptive, not structural).
Cholesky IRFs are shown under three orderings; the GDP response to an EgPU shock at h=2
ranges from -3.32 (EgPU first) to +0.15 (EgPU last), which is exactly why the ordering
must be stated and justified rather than assumed. Nothing here is a causal policy shock.

## Outputs

`outputs/`: panel_dimensions, unit_root, lag_selection, coef_fe, coef_gmm, hansen,
ar_tests, gmm_first_stage, stability, irf_generalized, irf_cholesky, fevd_generalized,
fevd_row_sums (all 100.0), fevd_summary_h12, monte_carlo, monte_carlo_summary,
diagnostics_summary; figures fig1 to fig7.

## Real-panel decisions the audit flags before estimation

1. IDX-07: 17.6 percent of index values are exactly zero. Choose the representation
   openly (level with a floor, or log1p) and report both; `pvar_core.winsorize_series()`
   is provided for the tail.
2. IDX-09: maximum 3,828 with a single-site month. Run with and without low-coverage
   country-months; report the sensitivity.
3. IDX-05: five post-baseline country-months are missing, and IDX-04 has two Seychelles
   baseline gaps. Use the 18-country balanced panel (MOD-02) as primary, and repeat on
   the 36-country unbalanced sample with a stated estimator choice.
4. MAC-01: quarterly GDP is labelled as a same-quarter growth rate; confirm vintage and
   that late quarters are not forecasts before use.
5. RUN-01: outputs end 2026-09 with a 2026-10 manifest; refresh before current-period work.
