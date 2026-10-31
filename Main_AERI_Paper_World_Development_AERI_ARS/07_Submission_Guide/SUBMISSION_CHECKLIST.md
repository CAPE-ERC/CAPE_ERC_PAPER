# JBES submission checklist — AERI/ARS

## Files to upload (PDF only)

1. **Blinded paper**: `02_Anonymized_Manuscript/Measuring_Economic_Risk_in_Africa.pdf` (35 pages).
2. **Unblinded paper (with authors)**: `01_Title_Page/Measuring_Economic_Risk_in_Africa_JBES_Authors.pdf` (35 pages).
3. **Supplementary material (anonymous, for review)**: `03_Supplementary_Material/Supplementary_Material.pdf` (27 pages).

## Editorial-office requirements and how they are met

- **12-point font**: `\documentclass[12pt]{article}`; body text is set in 12-point type.
- **Fully double-spaced, 26 lines per page**: `\setstretch{1.75}` gives a 25.4-point line pitch and exactly 26 lines on a full page of text. Tables, figure notes and footnotes are single-spaced.
- **One-inch margins**: `\usepackage[letterpaper,margin=1in]{geometry}` on US letter paper.
- **35 pages or fewer, including the title page, abstract, tables, figures and references**: both copies of the paper are 35 pages.
- **Material moved to an anonymous supplement**: the former appendices A–E and lower-priority exhibits are in the supplement. The paper points to each item by its supplementary number.
- **Both copies**: the blinded and author copies come from the same source and differ only on the title page.
- **Anonymity**: the blinded paper and the supplement contain no author names, affiliations or emails, including in the PDF metadata.

## What moved from the paper to the supplement

| Former location in paper | Now |
|---|---|
| Lit. review 2.1–2.2 (full text), 2.6, part of 2.5 and 2.7 | Supplementary Section S8 (condensed versions remain in the paper) |
| Table 2 (keyword taxonomy, worked example) | Supplementary Table S9 |
| Table 4 (eight-pillar PCA weights) | Supplementary Table S10 |
| Table 6 (pillar profile by subperiod) | Supplementary Table S11 |
| Table 7 (deduplication) | Supplementary Table S2 (already there) |
| Figure 3 (weighting sensitivity) | Supplementary Figure S5 |
| Figure 4 (annual AERI, ten economies) | Supplementary Figure S6 |
| Figure 5 (average pillar indices) | Supplementary Figure S7 |
| Appendix A (data-collection architecture) | Supplementary Section S11 |
| Appendix B (archive-depth diagnostic, Table B.1) | Supplementary Section S12, Table S12 |
| Appendix C (external-identification diagnostics, Table C.1) | Supplementary Section S13, Table S6 |
| Appendix D (PVAR details, Table D.1) | Supplementary Section S3, Table S1 |
| Appendix E (ten-country table, Table E.1) | Supplementary Table S8 |

## Author actions before upload

- **Affiliations**: the author copy lists all seven authors under CAPE Economic Research and Consulting, as in the current title page. An earlier version of this package assigned Laniran, Akanni and Taiwo to the Central Bank of Nigeria and Adeleke and Alobaloke to the University of Ibadan. Confirm which is correct.
- **Author names, order and emails**: confirm that they match the submission system exactly.
- **Competing interests and acknowledgements**: complete these in the submission system if it asks; the title page still holds a placeholder.
- **Keywords**: the JBES template asks for keywords that do not repeat the title, so "Economic risk" and "Africa" were replaced. The keywords are now: Alternative data; Newspapers; Panel VAR; Risk measurement; Text as data.
- **If you rebuild the PDFs** from the `.tex` files, check that each copy of the paper is still 35 pages or fewer. The supplied PDFs were built with Computer Modern fonts; a Latin Modern build looks almost identical but can break lines slightly differently.
