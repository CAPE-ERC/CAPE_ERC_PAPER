# IJF submission package — constructed-target forecast evaluation revision

## Paper

**Forecast Evaluation with Constructed High-Frequency Targets: Information-Set Leakage and an African GDP Application**

The paper is now a methodological forecast-evaluation paper. The African GRE application is the empirical audit, not the sole contribution.

## Five-section structure

1. Introduction
2. Constructed targets, text measurement, and information sets
3. Forecast design and simulation evidence
4. Empirical application: African GDP forecasting
5. Discussion and conclusion

The main manuscript contains no numbered section beyond Section 5.

## Central contribution

A final-vintage high-frequency target may be used to score historical forecasts, but the same disaggregated path cannot automatically be treated as historical lagged information. With a linear benchmarking operator such as Denton, pre-origin monthly values can depend on annual benchmarks that were not yet released. The paper gives an information-set admissibility condition, a Monte Carlo illustration, and an empirical target-information audit.

## Simulation evidence

The Monte Carlo contains 54 economies over a 2015–2025 monthly calendar and now reports two complementary signal DGPs plus a pure-noise placebo. In the modest current-state DGP, a noisy contemporaneous signal with no next-year innovation has mean one-month relative RMSFE 0.9969 under publication-lagged information but 1.0002 when the full final-vintage disaggregated history is treated as historically available; this design alters the short-horizon profile but does not reproduce the empirical 12-month reversal. A separate persistent-state stress DGP is included as an existence calibration: at 12 months, relative RMSFE is 0.9962 under retrospective final-vintage information and 1.0122 under publication-lagged information, matching the direction of the African reversal. The stress calibration is not claimed to identify the empirical mechanism. The pure-noise placebo remains approximately neutral.

## African empirical audit

The earlier retrospective design gave a 12-month GRE relative RMSFE of 0.9961. Under publication-lagged GDP information, that ratio becomes 1.0048 and the long-horizon claim is retired. A modest one-month result remains under the parsimonious benchmark (relative RMSFE 0.9964; relative MAE 0.9897), but the raw RMSFE bootstrap interval includes zero, 33 of 54 economies improve, and GRE is not statistically persuasive against the 159-series factor benchmark.

## Additional robustness

- May, July, and November annual-release conventions.
- Cross-section-preserving moving-block bootstrap and complementary two-way inference.
- Exact-text article-level deduplication (497,091 records removed) with a full forecast rerun.
- Wide factor benchmark built from 159 retained macroeconomic series and six frozen factors.
- Direct information-staleness and revision diagnostics; the formal mechanism tests are null and are reported as such.
- Two complementary Monte Carlo signal DGPs plus a pure-noise placebo, including a persistent-state stress calibration that reproduces the direction of the empirical 12-month reversal.

## Data provenance

The archived annual GDP workbook is the exact author-supplied file frozen on 13 September 2026. Its relevant series is labelled `GDP (PPP)-WEO`; the workbook does not contain the underlying historical IMF WEO release identifier. The paper therefore describes the empirical design as a **publication-lagged final-vintage simulation**, not as a historical real-time-vintage forecast record.


## Restored full-length edition

This package restores the full analytical manuscript rather than the compressed submission draft. The main paper retains exactly five numbered sections while keeping the detailed GRE construction, target construction, dependence-aware inference, release-timing checks, domain comparisons, mechanism diagnostics, article-level deduplication, wide-factor benchmark, economic interpretation, limitations, and replication discussion in the main text. The later two-DGP simulation clarification is integrated into this full version rather than replacing those materials.
## Main-text figures and JEL classification

The full manuscript now contains six substantive main-text figures: (1) GRE descriptive distribution, (2) target-information leakage schematic, (3) Monte Carlo horizon distortion, (4) empirical retrospective-versus-publication-lagged horizon reversal, (5) country-level heterogeneity, and (6) release-timing plus wide-factor benchmark boundary. The figures are analytical rather than decorative and reproduce results already contained in the archived tables and CSV outputs.

JEL classification: **C53; C82; E37; O55**.


## Research-article refinement

The main manuscript is single-spaced and now includes ten substantive footnotes placed at methodological points where additional qualification helps the reader without interrupting the argument. The introduction explicitly states two research questions and includes a formal roadmap. The footnotes clarify ex-post scoring versus forecast-origin information, GDP-vintage provenance, frozen GRE specification, release-month conventions, nested-model inference, block resampling, simulation interpretation, factor-vintage scope and exact-text deduplication. The main manuscript is 38 pages in the current compiled version.

## Evidence upgrades completed 21 September 2026

Two additional referee-facing tests are now integrated into the main paper and supplement. First, the retrospective-to-publication-lagged change is decomposed into forecast-origin GDP-lag and recursive-training channels using four nested information designs and a two-factor Shapley allocation. At 12 months the total relative-RMSFE change is +0.0088 (paired 12-month block-bootstrap 95% interval [+0.0048,+0.0171]); the GDP-lag contribution is +0.0069 ([+0.0042,+0.0145]), about 79% of the point change, while the training-timing contribution is +0.0018 and its interval includes zero. Complementary HAC and two-way tests of raw and Clark-West loss-gain contrasts are archived.

Second, the complete horizon evaluation is repeated after excluding all 2020--2021 forecast targets. The 12-month reversal remains: retrospective relative RMSFE is 0.9976, while publication-lagged relative RMSFE is 1.0133. The corrected one-month ratio strengthens to 0.9926 (HAC CW p<0.001; two-way p=0.027) and the three-month ratio is 0.9929 (HAC p=0.0014; two-way p=0.0289). The WEO historical-vintage exercise is deliberately not included in this edition.

- Denton weight characterization: Section 2.3 now derives the interior geometric leakage rate, with $|\mu|=0.264745$ per additional annual tail step; the supplement provides the exact Schur-complement proof and within-year weight profile. Reproducible verification files are under `06_Data_and_Code/GDP_Construction/denton_weight_characterization/`.
Latest refinement: Section 5.2 now distinguishes unresolved real-time-vintage uncertainty from the disaggregation-weight leakage resolved by the origin-specific reconstruction; the direction of vintage substitution effects is left theoretically ambiguous.
