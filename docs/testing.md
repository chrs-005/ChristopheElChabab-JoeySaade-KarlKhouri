# Testing and Postman plan

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
