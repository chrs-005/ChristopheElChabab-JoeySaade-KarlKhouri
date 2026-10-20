# Joey Saade handoff

## 2026-10-17 — planning session

Changed: initialized repository documentation, task inventory, and draft auth/API contracts from the supplied brief. Files: README, CONTRIBUTING, `.env.example`, and `docs/`. No endpoints or application code exist.

Checks: inspected empty GitHub clone and extracted brief; generated task inventory. No runtime, automated, Postman, database, or integration checks could run. Remaining: choose stack and topology with team; finish auth/role contract; implement Joey's users, assets, notifications and their tests/evidence. Blockers: stack/database decisions; audit/notification contracts for integrations. Teammates can review the route list and initial ownership; no running API is ready to integrate.

Next unblocked: S-01 setup decision and S-02 authentication/role contract.

## 2026-10-17 — confirmed names and detailed handoff

Joey confirmed all three full names: Joey Saade, Karl Khoury, Christophe El Chabab. The task board, route prefixes and handoffs now use those names. Added the [Joey implementation plan](../joey-implementation-plan.md), including endpoint-by-endpoint real evidence and open architecture decisions. Documentation checks confirmed 54 required endpoint tasks and no source code or runnable tests. Remaining: team stack/database agreement, Joey's own implementation, Postman, running tests and screenshots. Teammates can use the confirmed route prefixes and review the proposed contracts; no API is running yet.

## 2026-10-17 — Joey implementation session

Implemented three FastAPI apps in `joey/users.py`, `joey/assets.py`, and `joey/notifications.py`, with shared auth/database code, SQLite schema, admin bootstrap and retryable outbox. Added `tests/test_joey.py`, `postman/joey.collection.json`, environment template and API docs. All 18 brief routes use `/api/Joey-Saade`; extra admin-role and asset-history routes are documented. Check: `python -m pytest tests/test_joey.py -q` → 5 passed; `python -m compileall -q joey postman` passed. Actual test output is in [evidence](../evidence/joey-pytest-2026-10-17.txt). No Postman screenshots or database screenshots were captured.

Additional check: `python tests/live_smoke.py` passed after starting all three services as separate processes, making real HTTP registration/login calls, and verifying automatic welcome notification delivery plus the database outbox record. [Actual output](../evidence/joey-live-http-2026-10-17.txt). The test uses a temporary database and records no screenshot.

Commits `5b067bb` (implementation) and `8f8fa69` (documentation/evidence) were pushed to `origin/main` on 2026-10-17 using the configured Joey Git identity. The local working tree was clean before this final handoff update.

Remaining: run the apps and Postman against a real local database, capture screenshots, settle team database topology, integrate Karl's assignment/threat/vulnerability triggers and asset FK deletion behavior, and deliver queued audit events once Christophe's API agrees on the schema. Teammates can now consume Joey's signed bearer token conventions and notification creation route. Next unblocked: capture Joey's live Postman/database evidence and review the shared contract with the team.

## 2026-10-19 - Postman correction and nine-service verification

Corrected `postman/generate.py` and regenerated `postman/joey.collection.json` and `postman/joey.environment.template.json`. Asset reads/history now precede cleanup; cleanup deletes the asset and both the created and automatic welcome notifications before deleting the sample user. Each run creates a fresh sample username, email, and notification event ID. Added `tests/postman_joey.py`, which boots all nine real services against a disposable database, runs Newman, checks server logs for tracebacks, and stops the processes.

Checks actually run: `python -m pytest tests/test_joey.py -q` -> 5 passed; `python tests/postman_joey.py` -> 27 requests, 29 assertions, zero failures, no server tracebacks; `python -m pytest tests -q` -> 60 passed, 42 dependency deprecation warnings. Transcripts: [Newman](../evidence/joey-postman-newman-2026-10-19.txt) and [pytest](../evidence/joey-final-pytest-2026-10-19.txt). The first local Newman attempt failed because the new runner bootstrapped `karl_admin` while logging in as `joey_admin`; the runner was corrected before the passing run. No Joey service endpoint behavior changed. Teammates can run the corrected collection and use its ordered cleanup. Remaining: actual Postman GUI and database screenshots, report sections, and review of incident/vulnerability asset references. Next unblocked: capture Joey's U/A/N evidence from a persistent demo database before running Cleanup.

## 2026-10-19 - Deleted user identity regression

Fixed the register-delete-register 500 by adding a durable `user_id_allocations` table. Registration and administrator bootstrap reserve an ID before inserting a user. `joey/common.py` seeds older databases once from live users and historical welcome/user audit events. This preserves outbox event uniqueness and prevents an old bearer token from identifying a new account. The API route and response shapes did not change; database identity behavior did. Files: `joey/schema.sql`, `joey/common.py`, `joey/users.py`, `joey/bootstrap_admin.py`, `tests/test_joey.py`, API/database docs.

Actual checks: focused Joey suite 7 passed after the final token-isolation assertion ([output](../evidence/joey-id-reuse-pytest-2026-10-19.txt)); full suite 62 passed with 42 dependency deprecation warnings before that last test-only assertion; nine-service Newman 27 requests / 29 assertions, zero failures after the ID fix ([output](../evidence/joey-postman-newman-2026-10-19-after-id-fix.txt)). An earlier full-suite attempt was interrupted after repeated migration seeding caused excessive runtime; seeding now runs once and the subsequent full run completed. No new screenshots, commit, or push. Teammates can integrate the durable user IDs and existing welcome event format. Remaining: Postman GUI/database screenshots, common report, and asset references review. Next unblocked: capture U/A/N evidence from the persistent demo database before Cleanup.

## 2026-10-20 - Joey report text and shared section names

Added Joey Saade to the common LaTeX report's non-service section headings already carrying Christophe ElChabab, while retaining Karl's service placeholder and Christophe's screenshot captions. Added `report/joey-implementation.tex` and `report/joey-api.tex` for Joey's Users, Assets and Notifications design, database relationships, permissions, validation, all 18 required route suffixes and two supporting routes. Updated `report/main.tex` and `report/README.md`. Described only checks already recorded in `docs/evidence/`; no Joey GUI/database screenshots or new runtime execution were produced.

Checks: source-to-report route and file review, TeX brace/input structural check and `git diff --check` (results recorded in this session's final response). A TeX compiler was not available locally, so no compiled PDF is claimed. Teammates can integrate the named Joey report sections. Remaining: Joey captures and embeds his actual Postman/database screenshots with captions, reviews the final PDF with the team, and adds genuine Git/CREATES evidence. Next unblocked: capture U/A/N screenshot evidence and place it in the report appendix.

## 2026-10-20 - Screenshot slots and capture order

Added `report/joey-evidence.tex`, 36 named pending-image slots in `report/main.tex`, tracked destination folders under `report/joey-screenshots/`, and `report/JOEY-SCREENSHOT-GUIDE.md`. The guide maps each Postman request and SQLite query to an exact PNG filename and puts populated database views before Cleanup. `report/README.md` now documents automatic loading after recompilation. No screenshot, persistent demo database, runtime request or compiled PDF was created this session.

Checks: compared every guide filename with the 36 LaTeX image paths, checked all destination folders, verified TeX input/brace structure and ran `git diff --check`; see actual local check output in the session. No TeX compiler is installed here, so visual PDF verification remains open. Teammates can compile the report with named pending boxes and replace them with Joey's real PNGs as captured. Next unblocked: Joey runs the persistent demo and captures Postman/database screenshots using the guide; only then can U/A/N-EVID-01 advance.

## 2026-10-20 - One image per evidence category

Joey supplied a Postman Runner view showing all six Users requests in one image and asked to reduce the report evidence slots to one image per category. Replaced the 36 per-request LaTeX slots with 10 folder/database category slots in `report/joey-evidence.tex` and revised `report/JOEY-SCREENSHOT-GUIDE.md`, `report/README.md` and the screenshot-folder README. The three previously saved individual Users PNGs were preserved without alteration; the new whole-folder Users image has its own filename. No image was created from the chat attachment or represented as a saved report screenshot.

Checks: matched all 10 manifest paths to guide filenames and existing destination folders; verified TeX braces/input and `git diff --check`. A TeX compiler is unavailable locally, so PDF layout remains unverified. Teammates can use the concise category capture plan. Next unblocked: save the Users Runner image at its named path, run the remaining folders with Postman's Keep variable values setting, capture populated database categories, then run Cleanup.

## 2026-10-20 - Detailed evidence naming and literal service URLs

At Joey's request, restored one LaTeX slot per Postman request (27) and five numbered database slots in `report/joey-evidence.tex`. The first Users request is `11-Register-employee.png`; remaining files follow the same section/request numbering. Updated `report/JOEY-SCREENSHOT-GUIDE.md`, both report READMEs and report statements about available screenshots. Copied five existing real database PNGs unchanged to their new numbered paths. Existing whole-folder Runner screenshots remain supplementary. Updated `postman/generate.py` and regenerated Joey's exported collection/environment so all three service base URLs are literal. The collection still keeps dynamic IDs and credential variables for repeatable runs without committing secrets; its executed request details show resolved values.

Checks: manifest has 32 unique paths, every path is documented in the guide, and five database paths exist. The exported collection has 27 requests and all 27 URLs begin with a literal localhost service URL. Focused Joey tests passed: 7 passed. A nine-service Newman attempt failed with 22 assertions because ports 8001-8003 were already occupied by the persistent screenshot demo services, so the runner contacted those existing processes rather than its disposable database; registration returned 201 but bootstrap-admin login returned 401. The existing demo servers were left running and their database was not reset by the runner. No successful Newman rerun or PDF build is claimed here. Teammates can use the numbered manifest and retain the existing folder-run results. Remaining: Joey captures 27 individual executed-request images with actual responses, reviews a compiled report, and completes team Git/CREATES evidence. Next unblocked: capture request details from the saved successful Postman run with response persistence enabled; later rerun Newman when ports 8001-8009 are free.

## 2026-10-20 - Report merge resolution

Resolved four merge conflicts in `docs/CONTRIBUTIONS.md`, `report/README.md`, `report/joey-evidence.tex` and `report/main.tex`. Retained the incoming redesigned report, shared API contracts, workflows and Karl's staged work while keeping Joey's 27 per-request slots and five numbered database slots. The five numbered PNGs are byte-identical to Joey's original real database captures. Updated captions and appendix wording to distinguish record views from table schemas and queued events from delivered audit records. The guide still maps all 32 slot paths. Full merged suite: `python -m pytest tests -q` passed 71 tests, 42 dependency deprecation warnings, in 111.79 seconds. `git diff --check` and a no-conflict-marker check passed. XeLaTeX/Tectonic remains unavailable locally, so no compiled PDF or visual review is claimed. Teammates can continue editing the merged report and Karl's integrated service updates. Remaining: 27 detailed Joey Postman screenshots, schema evidence, report compilation/review, final Git evidence. Next unblocked: capture Joey's executed request/response views using the guide.

The upstream AUB cover-logo commit arrived before the merge could be pushed. Its image and title-page placement were incorporated, and the report README now notes that the portable ZIP must be rebuilt. No PDF or ZIP was regenerated.
