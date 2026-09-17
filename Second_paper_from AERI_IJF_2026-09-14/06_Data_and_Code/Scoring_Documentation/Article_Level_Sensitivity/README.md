# Article-level exact-text sensitivity

This folder contains the frozen output of a within-country-month exact-text deduplication audit of the production article archive and the source snapshot used to generate it.

- `aeri_pillars_country_period.csv` is the deduplicated pillar panel used to construct the alternative Growth/Real Economy signal in the final forecasting sensitivity.
- `aeri_country_period.csv`, `aeri_diagnostics.csv`, and `summary.json` document the broader reconstruction.
- `run_exact_dedup_fast_source_snapshot.py`, `frozen_scoring.py`, and `fast_frozen_scores.py` preserve the scoring/reconstruction source used for the audit.

The source script expects the separate raw article archive and its source manifest; those raw article files are not bundled because of their size. The archived output removes 497,091 exact within-country-month duplicate records (2.33% of reconstructed rows), including 186,379 cross-outlet copies. The final paper reruns the publication-lagged one-month forecast on the common sample using the recomputed deduplicated Growth/Real Economy pillar.

This sensitivity changes the retained article universe but keeps the production lexicon, severity tiers, and emphasis coefficients fixed. It therefore does not constitute a full alternative-classifier or human-validation exercise.
