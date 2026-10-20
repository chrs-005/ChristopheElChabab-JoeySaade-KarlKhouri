# Sprint I LaTeX report

The report follows the 11 required headings in the supplied handout. The handout supplies an outline, not a Word-only template. It does not explicitly name LaTeX; confirm PDF acceptance if the Moodle upload restricts file types.

Compile main.tex with XeLaTeX twice, or with Tectonic. The source uses only genuine local screenshots and marks missing team material explicitly. It is a draft, not the completed common submission.

When building from this repository's report folder, screenshots are read from ../../Christophe-ElChabab-Screenshots. They remain outside Git by Christophe's choice. For an Overleaf upload, use the local ZIP prepared alongside the repository: it contains the same LaTeX source with an evidence folder. Do not upload the private .env, database secrets or Postman credential environment.

main.tex contains the common outline and diagrams. christophe-implementation.tex and joey-implementation.tex contain the respective service explanations; joey-api.tex adds Joey's route table. evidence.tex contains captioned references to Christophe's unchanged images. karl-implementation.tex, karl-api.tex and karl-database.tex contain Karl Khouri's explanations, route table and schema. karl-evidence.tex lists Karl's 43 captioned screenshots under report/karl-screenshots/. Joey's 32 captioned individual slots are in joey-evidence.tex: 27 Postman requests and 5 database views. Save his real PNGs with the exact filenames under report/joey-screenshots/; the next build loads them automatically, and missing files display a named pending box. Follow [Joey's screenshot guide](JOEY-SCREENSHOT-GUIDE.md). Earlier folder-run captures remain as supplementary files. Automated CLI output does not replace screenshots.

Tectonic setup source: https://tectonic-typesetting.github.io/book/latest/installation/
