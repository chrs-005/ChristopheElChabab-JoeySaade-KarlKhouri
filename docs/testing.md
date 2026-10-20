# Testing and Postman plan

## LaTeX compile and teammate integration verified, 2026-10-20

Actual owned commits: 2c8a917 (confirmed permissions and tests) and 380e048 (LaTeX/evidence documentation). Integrated Joey's newer 395e4c7 using a normal merge; shared documents merged cleanly. Verified no difference from origin/main in Joey's service files or tests/test_joey.py. The combined existing suite passed 69 tests, 43 dependency deprecation warnings, in 62.07 seconds using disposable test databases. Before merge, 67 tests passed. No live screenshot database was reset or replayed.

Compiled report/main.tex with portable official Tectonic 0.17.0. The revised PDF has 103 pages including 94 unchanged screenshot pages, a contents page, named sections, architecture and owned-schema diagrams. Rendered all pages; inspected layout previews and detailed narrative/diagram/table/example pages. Fixed a crossing schema arrow, kept diagrams with their text, added a repeated API-table header and corrected the evidence count. Rotation-aware bounds checks reported no out-of-page text. One underfull text warning and a duplicate page-anchor warning remain non-fatal; no missing image, undefined reference or overfull box was reported. The report is explicitly a draft with teammate sections, final Git contribution captures, complete team schema and genuine CREATES feedback pending.

The local deliverables are Sprint1-Report-Draft.pdf and Sprint1-LaTeX.zip alongside the repository. The ZIP is for Overleaf and includes source plus all 94 real images; it is not committed. Source files remain in report/ on Git; screenshots, private credentials and generated PDF/ZIP remain outside Git. User authorized a normal non-force push after checking teammate safety. No contribution dates or history are fabricated.

## Professor clarification verification, 2026-10-19

Authority: the professor's answer supplied by Christophe in chat. Auditors may search threats, and `GET /incidents` must use authenticated-user scoping for analysts/employees while administrators/auditors see all records. Before the change, the new auditor search test failed with 403 and all six identity-scope cases passed. After the minimal allowlist change and matrix update, the complete suite passed **67 tests** (43 pinned-dependency warnings). Tests include two analysts, two employee reporters and unassigned incidents; each role is checked with five normal/forged query parameter combinations, comparing exact returned record IDs.

The updated exported collection passed **97 items, 229 assertions, zero failures**, with four asynchronous-event probes making **101 actual HTTP requests**, against nine real disposable servers. Its new requests explicitly show auditor threat search, auditor visibility across reporters, and attempted query-based scope overrides for employee/analyst. No saved responses or screenshots were fabricated. See [actual pytest output](evidence/christophe-professor-permissions-pytest-2026-10-19.txt) and [actual live output](evidence/christophe-professor-permissions-live-2026-10-19.txt).

The running screenshot services now load the corrected contract. Existing screenshot records were not reset: the persistent database still contains only its bootstrap administrator and no incident records. Import the latest tracked collection and private `.venv/christophe.local.environment.json`; start with only `01 Setup` (13 requests). No new business endpoints or unrelated fixes were added. These two permission questions are resolved; earlier dated ambiguity statements below are historical. The shared registration-after-user-deletion defect remains separate and unchanged. Do not run Cleanup before capturing required before/after, lifecycle and database evidence.

## Readiness recheck, 2026-10-19

Revision checked: `75ca31b` after a safe fast-forward pull. Full pytest suite: **60 passed**, 43 pinned-dependency deprecation warnings. The actual nine-service integration path passed, including valid/invalid lifecycles, notes, assignment notifications, audit records, complete reports and database integrity. The unchanged collection runs on the same temporary database produced:

| Collection | Result |
|---|---|
| Christophe | 92 items, 96 actual HTTP requests including four probes, 214 assertions, zero failures |
| Joey | 27 requests, 29 assertions, zero failures |
| Karl, immediately after Joey cleanup | Registration HTTP 500; nine assertion failures cascaded from the missing analyst account |
| Karl, separately on a fresh temporary database | 37 requests, 51 assertions, zero failures; no server tracebacks |

The [combined raw transcript](evidence/team-postman-recheck-2026-10-19.txt) records actual failures and is not a screenshot or submission-ready result. An [isolated diagnostic](evidence/registration-reuse-diagnostic-2026-10-19.txt) confirmed the cause through actual register/delete/register handlers. `users.id` is `INTEGER PRIMARY KEY` without a non-reuse guarantee; deleting the highest ID lets SQLite reuse it. Registration queues `welcome-user-{id}`, while cleanup retains that old outbox event. The next new account therefore raises `sqlite3.IntegrityError: UNIQUE constraint failed: outbox.event_id` and rolls back. The collection's later analyst login and action requests fail as a consequence. No teammate service code was changed to conceal or work around this defect.

Joey should correct user/event identity reuse and add a regression for this exact sequence; the shared database run must then pass. The old collection ordering/header defects are fixed, but the full team is not yet cleared for an uninterrupted serial screenshot session. Christophe's own APIs pass on the tested fresh setup. His 18 required method/path combinations retain `/api/Christophe-ElChabab` and remain covered by contract/role/validation checks.

Interactive prerequisites remain: configure the ignored private `.env` with three distinct secrets, correct report sources and an administrator, then start all nine services on ports 8001-8009. Tests used disposable data and stopped all temporary servers. Capture real request/response screenshots and database records before Cleanup, including before/after updates and each incident status transition, with captions `Christophe ElChabab - API title - purpose`. The professor's auditor-threat-search/scoped-incident-list ambiguities remain unresolved. None of these checks substitutes for actual evidence, the report.

## Whole-team readiness check, 2026-10-18

At Christophe's request, all 60 regression tests were rerun and passed (43 pinned-dependency deprecation warnings). Nine actual servers were started against a disposable SQLite database; authentication, assignments, notes, both lifecycles, notifications, audit logging, playbooks, report reconciliation and database integrity passed. All spawned servers were stopped afterward.

All three exported collections were then executed unchanged through Newman against those same real services, using valid temporary administrator/service credentials and an existing active analyst. The raw [readiness transcript](evidence/team-postman-readiness-2026-10-18.txt) includes the intentionally nonzero overall result; it is not screenshot evidence.

| Collection | Requests / assertions | Actual result |
|---|---|---|
| Christophe | 92 items, 96 HTTP requests, 214 assertions | All assertions passed |
| Joey | 26 requests, 27 assertions | Two assertions failed: Delete user returned 409 while welcome notifications still referenced it; Get asset returned 404 because Delete asset ran first |
| Karl | 31 items, 34 assertion attempts | Two requests could not be sent because JavaScript test text was placed in header objects; three assertion failures also occurred, including a lifecycle check returning 404 after the playbook/action was deleted |

Backend integration is runnable, but the unchanged full-team Postman workflow is **not ready**. Joey must arrange dependent reads/updates before deletion, remove referencing notifications before a successful user deletion, retain administrator authentication, and use fresh sample values on repeat runs. Karl must pass `headers=[]` and `tests=status(...)` by keyword for both missing-token requests and test invalid transitions before deleting the action/playbook. Karl's report assertions currently accept 502/503; a final integrated run should require actual complete reports, not merely tolerate unavailable upstream services. These are review findings, not changes to teammate-owned collection files or service logic.

This local checkout has no private `.env`, and no demo services were left running on ports 8001-8009. Before interactive Postman, configure the three distinct secrets, bootstrap administrator, database and corrected report URLs using README, then start all nine services. Real API/database screenshots, the common report and permission clarification remain outstanding. Successful automated integration is not a claim of complete compliance or submission readiness.

Joey's [pytest suite](../tests/test_joey.py) exercises registration/login, duplicate and privilege escalation rejection, profile access, assets/history, notification access and deduplication, account status, database constraints, and an isolated outbox delivery test with an HTTP test double. Run `python -m pytest tests/test_joey.py -q`. The [Postman collection](../postman/joey.collection.json) and [environment template](../postman/joey.environment.template.json) contain Joey's actual routes, sample bodies and success assertions; fill credentials locally. Karl and Christophe must add their own folders. Additional negative tests and real Postman screenshots remain pending.

Run `python tests/live_smoke.py` for an actual three-process HTTP check of registration, login and automatic notification delivery. Its [recorded result](evidence/joey-live-http-2026-10-17.txt) passed on 2026-10-17. It does not verify teammate services.

End-to-end path after services run: authenticate; create/select an asset; report incident; assign analyst; check assignment notification; progress valid incident states; add notes; check audit events; exercise response actions; generate reports and reconcile statistics against records. Record actual commands, results and screenshots in [evidence](evidence/README.md).

Karl Khouri's [pytest suite](../tests/test_karl.py) covers audit delivery from the outbox, deduplication, forged keys, actor spoofing, immutability, user-deletion durability, search filters and permissions; playbook validation, ordering, transitions, assignee checks, history and deletion; and report reconciliation, filters, permissions and upstream failure. Run `python -m pytest tests/test_karl.py -q` and `python tests/live_smoke_karl.py`. Report tests replace the HTTP call with routing to the real test apps, or with labeled fake incident/vulnerability responses since those services do not exist yet. Regenerate Karl's Postman files with `python postman/generate_karl.py`.

## Christophe ElChabab

Run `python -m pytest tests/test_christophe.py -q`: 31 checks passed on 2026-10-18. These cover the three services' CRUD/search, normalized duplicates, input validation, missing/expired/forged tokens, live account status, four-role restrictions, incident ownership and assignment, lifecycle transitions, notes and resolution dates. An isolated integration check routes HTTP calls to the actual peer test handlers; it does not claim real network deployment.

Run `python tests/live_smoke_christophe.py` for nine actual HTTP server processes and a disposable database. It verifies audit/notification delivery, permissions, invalid transitions, completed workflows, playbook action progression, reports using actual records, and DB integrity. It stops all spawned processes afterward. Historical peer smoke checks still use their own explicit source URLs and expect unavailable services when they do not start them.

Regenerate Christophe's collection/environment with `python postman/generate_christophe.py`. This does not create response examples or screenshots. The collection has documented requests and assertions; run its ordered folders in Postman, capture inputs/results and database records, and embed real evidence in the report. The template contains no tokens, passwords or service keys. See [Christophe API guide](christophe-api.md).

Optional collection verification: `python tests/live_smoke_christophe.py --postman` uses Node.js/npm's Newman 6.2.1 runner against the same nine actual servers. All 86 requests and 86 assertions passed on 2026-10-18. Node/npm is needed only for this optional test, not the Python runtime. The environment template remains blank for credentials. The collection's execution does not create report screenshots. On this Windows machine, npm needed `NODE_OPTIONS=--use-system-ca` for the installed system certificate trust store; TLS verification stayed enabled. Full regression: 43 passed, with one dependency deprecation warning. [Recorded outputs](evidence/README.md).

### Latest strict review

Run `python -m pytest tests -q`: final result **60 passed**, including 17 review checks and all 12 pre-existing teammate tests. The independent contract test checks the exact set of 18 method/path pairs with `/api/Christophe-ElChabab`; the role matrix exercises 72 role/endpoint cases plus 18 missing-token requests. Additional checks cover boolean numeric input, forged note authors, inactive assignees, actual persisted records/FKs, OpenAPI contracts, and draining/retrying the outbox.

Run `python tests/live_smoke_christophe.py --postman`: final result **92 collection items, 214 assertions, zero failures** across all nine processes; 96 actual HTTP requests include four bounded event probes. Assertions require this run's own notification and audit subjects, not merely HTTP 200 or any older log. Earlier runs failed the stronger checks and led to the delivery-worker correction. See [review](christophe-review.md) and the current [evidence index](evidence/README.md). Dependency deprecation warnings remain in the pinned environment; no test failed in the final run.

### Karl Khouri collection follow-up, 2026-10-18

All three findings above for Karl's collection were confirmed and fixed in [the generator](../postman/generate_karl.py) and the exported collection. The missing-token requests now pass `headers=[]` and `tests=status(...)` by keyword, so they send no header or body. "Reject skipping In Progress" and a new "Reject starting step 2 before step 1" run while the actions are still Pending, before deletion. Reports now require HTTP 200, and the summary must report `complete: true` with no unavailable sources. Setup now creates, promotes and logs in its own analyst, and the assigned analyst performs the status changes. Only the administrator's `username`, `userPassword` and `auditServiceKey` need filling in.

Run `NODE_OPTIONS=--use-system-ca python tests/postman_karl.py` to start all nine real services on a disposable database and run the exported collection with Newman 6.2.1. Result: **37 requests, 51 assertions, 0 failures**, no server tracebacks ([output](evidence/karl-postman-newman-2026-10-18.txt)). The full regression suite still passes: `python -m pytest tests -q` → 60 passed. This is not screenshot evidence.

### Joey Saade collection follow-up, 2026-10-19

Regenerate Joey's exported files with `python postman/generate.py`. Run `python tests/postman_joey.py` (on this Windows setup, set `NODE_OPTIONS=--use-system-ca`) to boot all nine services on a disposable database and execute the ordered collection through Newman. The first local attempt exposed a runner credential mismatch and failed; after correcting the bootstrap username, the actual [final run](evidence/joey-postman-newman-2026-10-19.txt) passed **27 requests, 29 assertions, zero failures**, with no server tracebacks. Registration generates fresh sample identifiers. The collection reads the asset before deletion and deletes both sample notifications before deleting the sample user. Cleanup runs last. Full [regression output](evidence/joey-final-pytest-2026-10-19.txt): **60 passed**, 42 pinned dependency deprecation warnings. These CLI outputs are not Postman GUI or database screenshots.

### Joey Saade deleted user ID regression, 2026-10-19

`tests/test_joey.py` covers register -> delete -> register, unique historical welcome outbox keys, a higher replacement ID, rejection of the deleted user's token, and one-time seeding of a legacy database after the allocation table is absent. Final focused result: [7 passed](evidence/joey-id-reuse-pytest-2026-10-19.txt). A full verbose run passed 62 tests with 42 dependency deprecation warnings before the final test-only token assertion was added; the application code was unchanged after that run. The [nine-service Newman rerun](evidence/joey-postman-newman-2026-10-19-after-id-fix.txt) passed 27 requests and 29 assertions after the ID allocation change. No GUI or database screenshots were captured.

### Karl Khouri update, 2026-10-20

Karl's collection now has 46 requests (auditor setup plus screenshot-oriented checks). `python tests/postman_karl.py` → 46 requests, 62 assertions, 0 failures ([output](evidence/karl-postman-newman-2026-10-20.txt)). New regression tests `test_deleted_ids_are_never_reused` and `test_existing_database_is_upgraded_without_losing_rows` cover the playbook/action/audit ID-reuse defect found during screenshot capture. Full suite: 71 passed.

### Karl Khouri permission update, 2026-10-20

Following the handout, analysts can retrieve/search audit logs and only administrators create playbooks. Collection: 48 requests, 65 assertions, 0 failures ([output](evidence/karl-postman-newman-2026-10-20.txt)). Full suite: 71 passed.
