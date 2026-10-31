# JBES submission package — AERI/ARS

Journal: *Journal of Business & Economic Statistics* (JBES). The package was first prepared for World Development and has been converted to the JBES format requested by the editorial office: 12-point type, fully double-spaced (26 lines of text per page), one-inch margins, at most 35 pages including the title page, abstract, tables, figures and references.

Start with `07_Submission_Guide/SUBMISSION_CHECKLIST.md`.

- `01_Title_Page/` — identifying material: the **author copy of the paper** (`Measuring_Economic_Risk_in_Africa_JBES_Authors.pdf` and `.tex`) and the separate title page.
- `02_Anonymized_Manuscript/` — **blinded paper** (`Measuring_Economic_Risk_in_Africa.tex` / `.pdf`; `Measuring_Economic_Risk_in_Africa_JBES.pdf` is an identical copy).
- `03_Supplementary_Material/` — **anonymous supplement** (`Supplementary_Material.tex` / `.pdf`; `JBES_Supplementary_Material.*` are identical copies) and `Supplementary_Data/` with every supplementary table and figure source.
- `04_Figures/` — figure artwork; `Figure_Captions.txt` maps files to figure numbers.
- `05_Tables/` — editable LaTeX tables; `Table_Captions.txt` maps files to table numbers.
- `06_Bibliography/` — `aeri_refs_JAE_JBES.bib` (used by the LaTeX files) and an identical `aeri_refs.bib`.
- `07_Submission_Guide/` — checklist and metadata.
- `02_Anonymized_Manuscript - Copy/` and files ending in `_old` — author backups of earlier versions; **do not upload**.

JBES accepts manuscripts in PDF format only. The `.tex` files are kept for future revisions; build each one from inside its own folder with pdflatex, biber, then pdflatex twice.
