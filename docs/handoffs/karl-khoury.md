# Karl Khoury handoff

Assigned services: Threat Intelligence, Vulnerability Management, Incident Management. Joey confirmed the full name on 2026-10-17. No Karl implementation, tests or evidence found. Next unblocked: propose S-04 database topology and relationships, organize S-05 Postman structure, and draft threat schema/validation. Integrate incident and vulnerability work after Joey's auth/asset contracts are usable. Update this handoff after Karl's own sessions.

## 2026-10-18 — Karl Khouri: audit logging, playbooks and reports

Changed: following the team's proposed ownership plan, Karl implemented the three services that plan lists for Joey (Security Audit Logging, Security Playbook and Response Automation, Security Reports) under `/api/Karl-Khouri`. Files: `karl/audit_logs.py`, `karl/playbooks.py`, `karl/reports.py`, `karl/common.py`, `karl/schema.sql`, `tests/test_karl.py`, `tests/live_smoke_karl.py`, `postman/generate_karl.py` and generated collection/environment, [API reference](../karl-api.md). Shared code touched: `joey/outbox.py` now delivers audit events to `/api/Karl-Khouri/logs`; `joey/common.py` `api_error_handler` accepts an optional direct denial writer so the audit service never audits itself over HTTP.

Endpoints: all 18 brief routes (`/logs`, `/playbooks`, `/actions/{id}/status`, `/reports/*`) plus `GET /playbooks/{id}/history`. Tables: `audit_logs` (immutable via trigger, durable actor attribution), `playbooks`, `response_actions`, `action_history`.

Checks: `python -m pytest tests -q` → 12 passed (7 Karl, 5 existing). `python tests/live_smoke_karl.py` passed with six real processes: outbox audit delivery, failed-login attribution, playbook ordering/transitions, asset and activity report reconciliation, and explicit 503 for incident data. [pytest output](../evidence/karl-pytest-2026-10-18.txt), [live output](../evidence/karl-live-http-2026-10-18.txt). Existing `tests/live_smoke.py` still passes. Postman collection generated but not yet run in Postman; no screenshots captured.

Fixed during the live check: concurrent outbox retries of the same event raced on the unique `event_id` and returned 500; `POST /logs` now returns the first stored copy.

Remaining: Postman run and screenshots (L/P/R-EVID-01); incident, threat and vulnerability report reconciliation once those services exist. Blockers: team confirmation of the new ownership split, and which name spelling to use (`Khouri` in routes per Karl; earlier docs say `Khoury`). Teammates can integrate now: send audit events with `X-Service-Key: AUDIT_SERVICE_AUTH_SECRET` to `POST /api/Karl-Khouri/logs`, or queue them in `outbox`; expose list APIs with `created_at`, `status`, `severity` (and `type`, `assigned_to`, `cvss_score` where relevant) for reports.

## 2026-10-18 — Karl Khouri: Postman collection fixes after team readiness check

Changed: confirmed and fixed the three findings in Christophe's readiness check ([details](../testing.md#karl-khouri-collection-follow-up-2026-10-18)). Files: `postman/generate_karl.py`, `postman/karl.collection.json`, `postman/karl.environment.template.json`; new runner `tests/postman_karl.py`; `tests/live_smoke_karl.py` now uses Christophe's `/api/Christophe-ElChabab` prefix. No service code changed.

Checks: Newman against nine real services → 37 requests, 51 assertions, 0 failures ([output](../evidence/karl-postman-newman-2026-10-18.txt)); `python -m pytest tests -q` → 60 passed; `python tests/live_smoke_karl.py` and `python tests/live_smoke_christophe.py` passed.

Remaining: L/P/R-EVID-01 screenshots and database records. Joey's collection findings are his to fix and were not changed here.

## 2026-10-20 — Karl Khouri: report sections, screenshots and ID-reuse fix

Changed: added Karl's LaTeX sections (`report/karl-implementation.tex`, `karl-api.tex`, `karl-database.tex`, `karl-evidence.tex`) and wired them into `report/main.tex`. The Postman collection gained an auditor in Setup and nine screenshot-oriented requests: repeated event, auditor/analyst log access, unknown log ID, deletion record and its permanence, and analyst report access. Captured 43 screenshots on a nine-service demo database: 37 Postman requests and 6 database views. They are stored outside Git in `Karl-Khouri-Screenshots/`, next to the repository, as Christophe does.

Bug found while capturing: deleting a playbook let SQLite reuse its step IDs. The next playbook's step notification event ID (`playbook-action-{id}-assigned`) collided with the retained outbox row, and creation returned 500. Execution history and audit deletion records would also have pointed at reused IDs. Fix: `AUTOINCREMENT` on `audit_logs`, `playbooks` and `response_actions`, and a startup migration in `karl/common.py` that rebuilds older tables without losing rows and seeds `sqlite_sequence` past every referenced ID. Two regression tests cover it; both fail on the old code.

Checks: `python -m pytest tests -q` → 71 passed; Newman against nine services → 46 requests, 62 assertions, 0 failures ([output](../evidence/karl-postman-newman-2026-10-20.txt)); `live_smoke_karl.py` and `live_smoke_christophe.py` passed; the report compiles with all 43 images.

Remaining: Karl's AI-use statement in the report References, and a final team review of the compiled PDF.
