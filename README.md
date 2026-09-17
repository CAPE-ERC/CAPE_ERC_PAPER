<p align="center">
  <img src="assets/banner.svg" alt="CAPE ERC — CAPE Economic Research and Consulting" width="100%">
</p>

<h1 align="center">CAPE ERC Research Papers</h1>

<p align="center">
  <b>Applied macro-finance and text-as-data research on African economies</b><br/>
  News-based risk measurement &nbsp;·&nbsp; market alignment &nbsp;·&nbsp; forecast-evaluation methodology
</p>

<p align="center">
  <a href="#-papers"><img alt="Papers" src="https://img.shields.io/badge/papers-3-0B2545"></a>
  <a href="#-papers"><img alt="Coverage" src="https://img.shields.io/badge/coverage-54_African_economies-13315C"></a>
  <a href="#-papers"><img alt="Data" src="https://img.shields.io/badge/data-2015%E2%80%932025-13315C"></a>
  <a href="#-license--use"><img alt="Status" src="https://img.shields.io/badge/status-active_research-D4A017"></a>
  <a href="mailto:stewogbade@capeeconomicconsult.com"><img alt="Contact" src="https://img.shields.io/badge/contact-CAPE%20ERC-0B2545"></a>
</p>

<p align="center">
  📄 <a href="#-papers">Papers</a> |
  🗂️ <a href="#%EF%B8%8F-repository-structure">Structure</a> |
  📚 <a href="#-citation">Citation</a> |
  ✉️ <a href="#-contact">Contact</a>
</p>

---

## 🎯 Overview

This repository collects the working and submission-ready research papers produced at **CAPE Economic Research and Consulting (CAPE ERC)**. All three papers build on a shared text-as-data infrastructure — large-scale news article corpora spanning **54 African economies from January 2015 to December 2025** — and use it to construct novel economic-risk and exchange-rate-risk indices, study their transmission into macro-financial outcomes, and formalize the forecast-evaluation pitfalls that arise when constructed, revision-prone targets are used for out-of-sample scoring.

Each paper ships as a self-contained submission package: title page, anonymized/full manuscript, supplementary material, figures, tables, bibliography, and a submission guide.

## 🔥 Updates

- **Sep 16, 2026** — Repository reorganized into per-paper submission packages; front matter and navigation added.
- **Sep 14, 2026** — Restored full-length edition of the *Forecast Evaluation with Constructed High-Frequency Targets* manuscript (IJF), with the two-DGP Monte Carlo and publication-lagged robustness checks integrated into the main text.
- **Sep 2026** — *Measuring Economic Risk in Africa* (AERI/ARS) submission package finalized for **World Development**, double-anonymized.

## 📄 Papers

### 1 · Measuring Economic Risk in Africa: The African Economic Risk Index and African Risk Score
**Target journal:** World Development (double-anonymized review) · [`Main_AERI_Paper_World_Development_AERI_ARS/`](Main_AERI_Paper_World_Development_AERI_ARS/)

A multidimensional news-based framework for measuring economic risk across 54 African economies (2015–2025). Introduces the **African Economic Risk Index (AERI)** — built from 21.3M retained article records across eight non-exclusive risk pillars — and the **African Risk Score (ARS)**, a bounded 0–100 composite of intensity, breadth, severity, and structural spread. Validates the index against panel VAR and external monetary-policy shock designs.

| | |
|---|---|
| Authors | Emmanuel Akande*, **Shakir Tewogbade**, Temitope J. Laniran, Elijah Akanni, Oyedamola Funmibi Taiwo, Honey Adenike Adeleke, Kafayat Ajoke Alobaloke |
| JEL | E37 · C55 · C81 · O55 |
| Contents | [Title page](Main_AERI_Paper_World_Development_AERI_ARS/01_Title_Page/) · [Manuscript](Main_AERI_Paper_World_Development_AERI_ARS/02_Anonymized_Manuscript/) · [Supplementary material](Main_AERI_Paper_World_Development_AERI_ARS/03_Supplementary_Material/) · [Figures](Main_AERI_Paper_World_Development_AERI_ARS/04_Figures/) · [Tables](Main_AERI_Paper_World_Development_AERI_ARS/05_Tables/) |

### 2 · Forecast Evaluation with Constructed High-Frequency Targets: Information-Set Leakage and an African GDP Application
**Target journal:** International Journal of Forecasting (IJF) · [`Second_paper_from AERI_IJF_2026-09-14/`](Second_paper_from%20AERI_IJF_2026-09-14/)

A methodological forecast-evaluation paper: when a final-vintage, high-frequency target is built with a linear benchmarking operator (e.g. Denton), pre-origin values can silently depend on annual benchmarks not yet released at forecast origin. Gives an information-set admissibility condition, two Monte Carlo signal DGPs plus a pure-noise placebo, and a publication-lagged empirical audit of an African GDP application that retires an earlier 12-month reversal result.

| | |
|---|---|
| Authors | Emmanuel Akande*, **Shakir Tewogbade**, Temitope J. Laniran, Elijah Akanni, Oyedamola Funmibi Taiwo, Honey Adenike Adeleke, Kafayat Ajoke Alobaloke |
| JEL | C53 · C82 · E37 · O55 |
| Contents | [Title page](Second_paper_from%20AERI_IJF_2026-09-14/01_Title_Page/) · [Manuscript](Second_paper_from%20AERI_IJF_2026-09-14/02_Main_Manuscript/) · [Supplementary material](Second_paper_from%20AERI_IJF_2026-09-14/03_Supplementary_Material/) · [Figures](Second_paper_from%20AERI_IJF_2026-09-14/04_Figures/) · [Data & code](Second_paper_from%20AERI_IJF_2026-09-14/06_Data_and_Code/) |

### 3 · News-Based Exchange-Rate Risk, Market Alignment, and Volatility Dynamics across African Economies
**Status:** Working paper · [`NBERI_Market_Alignment_Paper/`](NBERI_Market_Alignment_Paper/)

Introduces a market-alignment framework separating three often-conflated objects in FX-risk transmission: information content, conditional-variance transmission, and forecast value. Using a 51-country African panel, shows the **News-Based Exchange-Rate Risk Index (NBERI)** carries leading information for FX volatility, with transmission concentrated in markets where the risk narrative aligns with the bilateral exchange-rate level.

| | |
|---|---|
| Authors | **Shakir Tewogbade** et al., CAPE Economic Research and Consulting |
| JEL | F31 · C22 · C23 · C53 · G15 |
| Contents | [Manuscript source](NBERI_Market_Alignment_Paper/main.tex) · [Compiled PDF](NBERI_Market_Alignment_Paper/News_Based_FX_Risk_Market_Alignment_Volatility_Africa_LATEX_FINAL.pdf) · [Figures](NBERI_Market_Alignment_Paper/figures/) · [Supplement](NBERI_Market_Alignment_Paper/supplement/) |

## 🗂️ Repository Structure

```text
CAPE_ERC_PAPER/
├── Main_AERI_Paper_World_Development_AERI_ARS/   # Paper 1 — World Development submission package
│   ├── 01_Title_Page/
│   ├── 02_Anonymized_Manuscript/
│   ├── 03_Supplementary_Material/
│   ├── 04_Figures/
│   ├── 05_Tables/
│   ├── 06_Bibliography/
│   └── 07_Submission_Guide/
├── Second_paper_from AERI_IJF_2026-09-14/        # Paper 2 — IJF submission package
│   ├── 01_Title_Page/
│   ├── 02_Main_Manuscript/
│   ├── 03_Supplementary_Material/
│   ├── 04_Figures/
│   ├── 05_Tables/
│   ├── 06_Data_and_Code/
│   └── 07_Submission_Guide/
├── NBERI_Market_Alignment_Paper/                 # Paper 3 — working paper
│   ├── main.tex
│   ├── figures/
│   └── supplement/
├── Sample_Title_Page/                            # Shared title-page template
└── assets/                                       # README assets
```

Each submission package follows the same convention: numbered folders in reading order, `.tex` files as editable source, `.pdf` files as verification copies, and a `README_FIRST.md` / submission checklist at the top level for reviewers.

## 📚 Citation

If you reference this work, please cite the relevant paper:

```bibtex
@unpublished{tewogbade2026aeri,
  title  = {Measuring Economic Risk in Africa: The African Economic Risk Index and African Risk Score},
  author = {Akande, Emmanuel and Tewogbade, Shakir and Laniran, Temitope J. and Akanni, Elijah and Taiwo, Oyedamola Funmibi and Adeleke, Honey Adenike and Alobaloke, Kafayat Ajoke},
  year   = {2026},
  note   = {Submitted to World Development},
  institution = {CAPE Economic Research and Consulting}
}

@unpublished{tewogbade2026forecast,
  title  = {Forecast Evaluation with Constructed High-Frequency Targets: Information-Set Leakage and an African GDP Application},
  author = {Akande, Emmanuel and Tewogbade, Shakir and Laniran, Temitope J. and Akanni, Elijah and Taiwo, Oyedamola Funmibi and Adeleke, Honey Adenike and Alobaloke, Kafayat Ajoke},
  year   = {2026},
  note   = {Submitted to the International Journal of Forecasting},
  institution = {CAPE Economic Research and Consulting}
}

@unpublished{tewogbade2026nberi,
  title  = {News-Based Exchange-Rate Risk, Market Alignment, and Volatility Dynamics across African Economies},
  author = {Tewogbade, Shakir and others},
  year   = {2026},
  note   = {Working paper},
  institution = {CAPE Economic Research and Consulting}
}
```

## License & Use

These manuscripts are shared for review and research-collaboration purposes. All rights are reserved by the authors and CAPE Economic Research and Consulting; please contact the corresponding author before redistributing or reusing any material.

## ✉️ Contact

**Shakir Tewogbade**
CAPE Economic Research and Consulting
1 Sunny Alebiosu Street, Iyana Ipaja, Lagos State, Nigeria
📧 [stewogbade@capeeconomicconsult.com](mailto:stewogbade@capeeconomicconsult.com)
