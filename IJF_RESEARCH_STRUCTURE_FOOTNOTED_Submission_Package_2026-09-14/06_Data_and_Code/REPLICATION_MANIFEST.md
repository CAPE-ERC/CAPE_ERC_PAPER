# Replication manifest — target-information discipline design

## GDP data
- Source file: `GDP_Construction/GDP_Data_African_countries_AUTHOR_SUPPLIED_2026-09-13.xlsx`
- Series used: `GDP (PPP)-WEO`
- Study years: 2015–2025
- Replication vintage: file frozen as supplied 13 September 2026
- Historical WEO release vintage: not embedded in the workbook and therefore not claimed
- Clean annual extract: `GDP_Construction/annual_gdp_ppp_weo_labeled_final_vintage_2015_2025.csv`
- Final-vintage monthly outcome proxy: additive first-difference Denton

## Forecast-information rule
Baseline annual-data availability: year y becomes usable May of y+1. Forecast-origin GDP histories are reconstructed using only permitted annual years; months after the last permitted annual year are extrapolated using the log-monthly rate implied by the last two permitted annual totals. A target dated in year y enters training only from May of y+1. July and November sensitivity runs are supplied.

Because permitted annual observations use final-vintage values, this is a publication-lagged final-vintage simulation, not a historical-vintage real-time evaluation.

## Canonical horizon results
May rule, January 2020–December 2025 target dates:
- h=1: relative RMSFE 0.996382; relative MAE 0.989702; target-month HAC CW p=0.000587; two-way p=0.052776.
- h=3: relative RMSFE 0.997734; relative MAE 0.992814; HAC p=0.040713; two-way p=0.084432.
- h=6: relative RMSFE 1.003743.
- h=12: relative RMSFE 1.004838.
- h=1 moving-block bootstrap CW p=0.036593; raw 95% RMSFE-improvement interval approximately [-0.50, 1.44] percent.
- h=1 country-level RMSFE below one in 33/54 economies; median country ratio 0.991105.

Release sensitivity at h=1:
- July: relative RMSFE 0.996887; two-way p=0.039209; bootstrap CW p=0.037792.
- November: relative RMSFE 0.997341; two-way p=0.030108; bootstrap CW p=0.018996.

## Extended robustness
Outputs are in `Publication_Lagged_Evaluation/extended_robustness/` and are reproduced by `run_extended_robustness.py`.

### Information-staleness diagnostics
- May: stale pre-release relative RMSFE 0.9925; refreshed post-release 0.9985.
- July: stale 0.9937; refreshed 1.0010.
- November: stale 0.9975; refreshed 0.9961.
- Stacked information-age regression: p=0.625 for raw loss improvement and p=0.539 for Clark–West adjusted loss.
- GRE revision regression: coefficient -0.073 percentage points, two-way p=0.765.

### Article-level exact-text sensitivity
- Reconstructed duplicate removals: 497,091 records (2.33%), including 186,379 cross-outlet copies.
- Original vs deduplicated GRE: Pearson 0.9689, Spearman 0.9806, median within-country correlation 0.9990.
- Deduplicated GRE common-sample h=1 relative RMSFE 0.996929; relative MAE 0.990512; HAC CW p=0.001670; two-way p=0.068396.
- Underlying deduplicated pillar outputs and source snapshots are stored in `Scoring_Documentation/Article_Level_Sensitivity/`.

### Wide macro factor benchmark
- Candidate series: 162 cross-country monthly macro series (publication-lagged GDP growth, inflation, FX depreciation across 54 economies).
- Retained after pre-evaluation availability/variance screen: 159.
- PCA calibration window: 2016-03 through 2018-12.
- Six factors retained as the minimum to exceed 80% cumulative pre-evaluation variance (82.1%).
- One-month macro lag: +GRE relative RMSFE 0.998710; relative MAE 0.994636; HAC p=0.111937; two-way p=0.147650.
- Two-month macro lag: +GRE relative RMSFE 1.000595; relative MAE 0.997163; HAC p=0.450585; two-way p=0.457282.

The inflation and FX inputs are supplied final-vintage macro series without archived historical release vintages; the lagged factor exercise is a data-rich robustness benchmark, not a fully real-time-vintage benchmark.

## Retrospective target-information audit
The earlier final-vintage monthly-lag specification yielded a favorable h=12 ratio (0.9961, nominal CW p=0.033). It is retained only to show how target-information timing changes the conclusion and is not used as corrected pseudo-out-of-sample evidence.

## Simulation_Target_Information
- `run_target_information_monte_carlo.py`: standalone 54-economy constructed-target Monte Carlo.
- `target_information_monte_carlo.csv`: reported summary for the current-state and placebo DGPs.
- `current_state_signal.npy`, `persistent_state_stress.npy`, `pure_noise_placebo.npy`: replication-level relative RMSFE arrays for the two signal DGPs and the placebo.
- Persistent-state stress calibration: h=12 mean relative RMSFE 0.9962 under retrospective final-vintage information versus 1.0122 under publication-lagged information. This is an existence/stress calibration used to reproduce the direction of the empirical reversal, not an estimate of the empirical mechanism.
- `Figure_Simulation_Horizon_Distortion.pdf`: manuscript simulation figure.
