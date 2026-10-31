# Methodological pivot — editorial and mathematical audit

**Working title:** Forecast Rankings with Temporally Disaggregated Targets: Denton Benchmark Propagation and Information-Set Leakage  
**Date:** 31 October 2026

## Changes to the paper

1. The title, abstract, and opening now foreground the closed-form Denton weight result rather than African coverage or text mining. Neither the 21.3 million article count nor the source registry leads the paper.
2. The paper has five numbered sections: Introduction; Benchmark Propagation and Information-Set Admissibility; Forecast Designs and Simulation; Empirical Illustration: African GDP; Conclusion.
3. Proposition 1 has been moved into Section 2, with an explicit proof showing the within-year minimum-norm construction, annual-boundary recurrence, characteristic polynomial, and within-year back-substitution.
4. The proposition is **exact for the bounded impulse response of the doubly infinite block system**. The finite-panel weights are not exactly geometric at the endpoints. The benchmark-root identity was checked against the supplied verification script (mu = -0.264745493444) and the block quadratic and interpolation coefficients were independently checked symbolically.
5. The formula applies to **monthly GDP levels**, not directly to log growth, RMSFE differences, or a uniform forecast distortion. The Monte Carlo section shows that rankings can shift in either direction.
6. The empirical application now serves as an illustration of the information-set problem. The main text defines the GRE measure briefly, without collection, vocabulary or deduplication discussion; these remain in the supplement.
7. The supporting information has been reordered to open with the Denton proof, target timing, and simulations. The news archive and scoring specification remain available for reproducibility later in that document.
8. Existing empirical coefficients, ratios, simulation results, figures, and loss-difference statistics were **not re-estimated or altered**. The source code and data are preserved, except that one description of the partially timing-restricted design was corrected.
9. The former Journal of Forecasting cover letter and obsolete PDFs are excluded so they cannot accidentally be submitted to a new journal. The title page is journal-neutral.

## Essential methodological qualification before submission

The current code reconstructs **forecast-origin GDP lagged regressors** using benchmark years allowed by a May release rule (with July/November checks), but the **recursive training outcome values** are still derived from the full final-vintage monthly GDP path. The code delays when each target date may enter estimation; it does not reconstruct those labels using the annual benchmarks and actual values available at the time. Because Denton weights extend to adjacent future annual blocks, delay alone does not establish information-set admissibility of the final training labels. This limitation is now stated in the abstract, Introduction, Section 2, and Conclusion.

The analysis is best described as a comparison of **retrospective and publication-date-restricted final-vintage designs**, not a fully real-time replication. A strong follow-up before an econometrics-journal submission would construct admissible as-of-date training labels from archived annual vintages (or, in an explicitly partial-vintage sensitivity design, from benchmark years released by each origin) and rerun the model comparison. That additional experiment is **not part of this revision**, and the reported results should not be represented as having passed it.

Other limits: annual GDP is WEO-labeled but the actual WEO release vintage is unidentified in the supplied workbook; annual release dates are assumed rather than observed; the results are small in magnitude and the short-horizon incremental-news evidence weakens against a data-rich factor benchmark. A journal-specific cover letter, anonymization and author declarations should be checked at submission.

## Reproducibility

The replication folder contains the frozen annual GDP source, monthly paths, derived panel, evaluation and simulation scripts, results, GRE scoring documentation, and the Denton weight verification script. It does not contain the copyrighted full raw news archive. The figure/table files are duplicated within the main/supplement LaTeX folders for self-contained compilation. The changed manuscript compiles with `pdflatex`/`latexmk`; the PDF has 26 pages and the supporting information has 18 pages.
