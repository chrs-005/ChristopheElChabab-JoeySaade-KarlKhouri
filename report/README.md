# Sprint I common report

The report follows the handout's outline: title page, named contents, introduction, architecture, implementation, database design, validation/errors, API documentation, authentication/authorization, Git contributions and references. It uses the evidence set selected by the team for submission.

Compile `main.tex` with XeLaTeX twice or Tectonic. `report-style.tex` controls typography, colors, captions and evidence layout; `workflows.tex` draws the status sequences. Owner implementation/API files describe the services. `api-contracts.tex` adds inputs, response fields, errors, three captured-run examples and collection links.

The cover uses the unchanged white AUB logo from the [official university website](https://www.aub.edu.lb/Style%20Library/AUB/images/American%20University%20of%20Beirut-AUB.png), displayed on a dark background. Keep `assets/aub-logo.png` with the report sources; it is included in the portable ZIP and is not an execution screenshot.

The portable ZIP includes all report sources, the official logo and 180 supplied screenshots: 94 Christophe/shared under `evidence/`, 32 Joey under `joey-screenshots/`, 50 Karl under `karl-screenshots/` and four Git captures under `git-screenshots/`. Only the Joey files referenced by `joey-evidence.tex` are included; unused duplicate database images remain untouched in the repository. Import the ZIP into Overleaf and select `main.tex`. In this checkout, Christophe's and Git images load from `../../Christophe-ElChabab-Screenshots` and `../../GitHub-Screenshots`; these images and the generated PDF/ZIP remain local outside Git.

The submission date is 20/10/2026. CREATES and References include the team's supplied text. Karl's permission review is resolved by `ff39351`. The four actual Git screenshots show the history at capture time, through `e236431`; later report and evidence changes remain in the live repository history. No history or screenshot was fabricated.

All 32 numbered Joey captures are supplied: 27 individual request/response views and five record queries. The API and database captures come from separate runs (sample user 4 versus 2), not one continuous execution. The report describes the actual views without claiming that queued outbox rows establish successful delivery. Original screenshots are unchanged.

Never include private `.env` files, service keys, tokens or credential-bearing Postman environments. The handout supplies an outline, not a Word template; confirm PDF acceptance if Moodle restricts upload types. The editable Overleaf ZIP is report material, not the complete project submission.
