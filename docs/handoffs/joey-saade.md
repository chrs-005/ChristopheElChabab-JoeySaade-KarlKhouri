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
