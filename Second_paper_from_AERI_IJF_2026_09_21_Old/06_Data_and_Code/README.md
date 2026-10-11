# Data and code guide

Canonical forecasting outputs are in `Publication_Lagged_Evaluation/`.

- `run_publication_lagged_evaluation.py`: reconstructs the forecast-origin GDP information set under the May release rule, recursively estimates the benchmark and GRE models, computes horizon results, comparators, block-bootstrap results, and country-level RMSFE ratios.
- `origin_specific_causal_features.csv`: forecast-origin GDP-growth lags constructed without future annual years.
- `causal_ar_main_horizons.csv`: canonical 1/3/6/12-month horizon profile.
- `causal_ar_text_comparators_h1.csv`: GRE, broad AERI, Inflation Risk, and FX/External Risk at one month.
- `causal_ar_bootstrap_h1.csv`: 5,000-draw moving-block bootstrap for the corrected one-month result.
- `release_month_sensitivity/`: July and November release-convention outputs.

`GDP_Construction/` contains the exact author-supplied workbook, the cleaned final-vintage annual `GDP (PPP)-WEO` panel, the final-vintage Denton monthly outcome proxy, and construction code.

`Retrospective_Final_Vintage_Audit/` contains earlier final-vintage-lag forecast outputs **only to reproduce the target-information audit**. Those files are not the canonical forecasting evidence.

`Scoring_Documentation/` documents the frozen GRE scoring rule. `News_Source_Registry/` contains the newspaper-source files used to document source coverage.

## Constructed-target Monte Carlo
`Simulation_Target_Information/` reproduces the methodological simulation in Section 3. It contains the standalone simulation script, full replication-level arrays, summary CSV, figure, and a README. The current-state DGP is designed to contain contemporaneous activity information but no next-year innovation; the pure-noise placebo is reported separately.
