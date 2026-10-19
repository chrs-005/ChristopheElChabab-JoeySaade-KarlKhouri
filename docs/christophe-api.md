# Christophe ElChabab API and evidence guide

Owner: Christophe ElChabab. Services: Threat Intelligence, Vulnerability Management and Incident Management. Every business route below begins with `/api/Christophe-ElChabab`. Permissions incorporate the professor's clarification supplied by Christophe on 2026-10-19; this guide is not a completed student report or execution evidence.

## Run and authenticate

Use the existing README setup and private secrets. Run these from the repository root, using the same virtual environment and `DATABASE_PATH` as Joey/Karl:

```text
python -m uvicorn christophe.threats:app --port 8004
python -m uvicorn christophe.vulnerabilities:app --port 8005
python -m uvicorn christophe.incidents:app --port 8006
```

Joey's users service (8001) authenticates callers. Assets (8002), notifications (8003), Karl's logging (8007) and reports (8009) support the integrated demo. Playbooks (8008) are exercised in the full smoke check. Authenticate with `POST /api/Joey-Saade/users/login`, supplying `username_or_email` and `password`; send the returned `access_token` as `Authorization: Bearer <token>`. Existing one-hour tokens and live account status checks are reused. Credentials are not stored in the Postman template.

Required configuration: `AUTH_SECRET`, `SERVICE_AUTH_SECRET`, `AUDIT_SERVICE_AUTH_SECRET`, `DATABASE_PATH`, `AUDIT_SERVICE_URL`, `NOTIFICATION_SERVICE_URL`. The three keys must be separately generated and kept private. The three report-source URLs use the new Christophe prefix in `.env.example`; update any existing private overrides.

## Common responses and permissions

Create returns HTTP 201 and the created object; reads/searches/updates return 200 with an object or list; delete returns 200 with a message. An empty valid search is `[]`. Unknown object IDs return 404. No generated response is presented as a live result.

Errors follow the existing contract:

```json
{"status": "error", "message": "..."}
```

422 validation responses can also contain `errors` with field/message entries. Missing/invalid/expired tokens or unavailable accounts return 401; forbidden roles or another user's incident return 403; missing records return 404; duplicate threat indicators or invalid lifecycle changes return 409; invalid inputs, references or assignees return 422. Unknown request fields are rejected. Whitespace-only required text, empty updates and explicit null updates are rejected. Parameterized SQL prevents user input becoming query code; query column names come only from fixed server-side fields.

Role literals retain the team's existing contract: `Security Administrator`, `Security Analyst`, `Security Auditor`, `Regular Employee` (the brief calls the latter two Auditor and Regular Employee/User).

## Threat Intelligence — port 8004

| Method and suffix | Purpose / input | Response | Allowed roles |
|---|---|---|---|
| POST `/threats` | Add `type`, `value`, `description`, `severity`, `source` | Created threat object | Administrator |
| GET `/threats` | List all threats; no body | Threat list | Administrator, Analyst, Auditor |
| GET `/threats/{id}` | Read integer ID | Threat object, or 404 | Administrator, Analyst, Auditor |
| GET `/threats/search` | Optional query: `type`, `value`, `severity`, `source`; combined with AND | Matching threat list | Administrator, Analyst, Auditor |
| PUT `/threats/{id}` | Any nonempty subset of `description`, `severity`, `source` | Updated threat object | Administrator |
| DELETE `/threats/{id}` | Delete integer ID | `{"message":"Threat deleted"}` | Administrator |

Create request example (input template, not execution evidence):

```json
{"type":"Domain","value":"suspicious.example","description":"Indicator investigated by Christophe ElChabab","severity":"High","source":"SOC"}
```

Stored/returned fields: `id`, `type`, `value`, `description`, `severity`, `source`, `created_at`, `updated_at`. IDs are assigned by SQLite; timestamps are server-generated UTC ISO-8601.

Types: `IP Address`, `Domain`, `File Hash`, `Malware Signature`, `Other Indicators`. Severity: Low, Medium, High, Critical. IP threats use valid IPv4/IPv6 and canonical formatting. Domains are lowercased, have their terminal dot removed, require multiple valid DNS labels, and cannot include URL paths or whitespace. File hashes accept hexadecimal MD5/SHA-1/SHA-256 (32/40/64 characters) and are lowercased. Signatures/other indicators are nonblank text. `UNIQUE(type,value)` rejects normalized duplicates with 409. Identity/type cannot be changed through update, matching the brief's listed update fields.

The professor confirmed auditor search access and identified its omission from Service 4's list as an oversight. Auditor search now uses the same validated filters as administrator/analyst search; auditors still cannot create, update or delete threats.

## Vulnerability Management — port 8005

| Method and suffix | Purpose / input | Response | Allowed roles |
|---|---|---|---|
| POST `/vulnerabilities` | Add fields below | Created vulnerability | Administrator |
| GET `/vulnerabilities` | List all; no body | Vulnerability list | Administrator, Analyst, Auditor |
| GET `/vulnerabilities/{id}` | Read integer ID | Vulnerability, or 404 | Administrator, Analyst, Auditor |
| PUT `/vulnerabilities/{id}` | Update `description`, `severity`, `cvss_score`, `status`, `resolution_date` | Updated vulnerability | Administrator, Analyst |
| GET `/vulnerabilities/search` | Query `cve_id`, `severity`, `asset_id`, `status`; AND filtering | Matching vulnerability list | Administrator, Analyst, Auditor |
| DELETE `/vulnerabilities/{id}` | Delete integer ID | `{"message":"Vulnerability deleted"}` | Administrator |

Create input template:

```json
{"title":"Christophe ElChabab gateway finding","description":"Missing security update","cve_id":"CVE-2026-12345","cvss_score":8.1,"severity":"High","asset_id":1,"source":"Scanner"}
```

All fields shown are required. The CVE is validated for `CVE-YYYY-NNNN...` syntax (not verified against an external registry); CVSS must be a finite number in 0–10. Severity is stored explicitly from the validated request, rather than inferred from CVSS. The affected asset must exist. This test input does not assert that its example CVE is a real vulnerability.

Response fields: `id`, `title`, `description`, `cve_id`, `cvss_score`, `severity`, `asset_id`, `source`, `status`, `created_at`, `updated_at`, `resolution_date`.

New records start Open. Allowed lifecycle:

`Open → Under Investigation → In Progress → Resolved → Closed`

Skipped or backward transitions return 409. Repeating the current state is idempotent. A write lock keeps read/check/update together. Resolution date is set automatically at Resolved and retained through Closed. A supplied resolution datetime must include a timezone, be between creation and now, and apply only to a Resolved/Closed record.

## Incident Management — port 8006

| Method and suffix | Purpose / input | Response | Allowed roles |
|---|---|---|---|
| POST `/incidents` | Add fields below | New Open incident, `notes: []` | Administrator, Employee |
| GET `/incidents` | List records; no body | All for Administrator/Auditor, assigned for Analyst, submitted for Employee | All, with scope |
| GET `/incidents/{id}` | Read integer ID | Incident with notes (staff) | Administrator/Auditor, assigned Analyst, original Employee |
| PUT `/incidents/{id}/assign` | `{"analyst_id":2}` | Assigned incident | Administrator |
| PUT `/incidents/{id}/status` | `{"status":"Under Investigation"}` | Updated incident | Administrator, assigned Analyst |
| POST `/incidents/{id}/notes` | `{"content":"Christophe ElChabab reviewed gateway logs"}` | Created note | Administrator, assigned Analyst |

Create input template:

```json
{"title":"Christophe ElChabab phishing incident","description":"Suspicious message reported","category":"Phishing","severity":"High","reporter_id":4,"asset_id":1}
```

All fields shown are required. Category is nonblank text; the brief's examples are not treated as an exhaustive enum. Severity must be Low/Medium/High/Critical; the asset and active reporter must exist. Employees cannot choose another reporter's identity. Administrators may report on behalf of an existing active user.

Incident response fields: `id`, `title`, `description`, `category`, `severity`, `reporter_id`, `asset_id`, `assigned_to`, `status`, `created_at`, `updated_at`, `resolution_date`; detail includes `notes`. List responses contain incident fields without nested notes. Employees receive an empty notes list rather than staff investigation content. Analysts cannot access unassigned or another analyst's incidents. Other employees cannot view incidents they did not submit.

Assignment requires an existing Active Security Analyst. Assignment is audited and creates an Incident Assignment notification. New incidents begin Open, and the server assigns creation/resolution timestamps. Allowed lifecycle:

`Open → Under Investigation → Mitigated → Resolved → Closed`

Skipped/backward transitions return 409. Resolution is timestamped at Resolved. Updates use a write lock. Notes store `id`, `incident_id`, authenticated `analyst_id`, `content`, `created_at`; clients cannot forge the note author/timestamp. Administrators can add notes under their own actor ID because the service-specific authorization list permits this. No incident delete endpoint is requested or added.

The professor confirmed the scoped incident-list policy. The backend derives the SQL restriction from the authenticated user's current ID and role. Parameters such as `reporter_id`, `assigned_to`, `user_id` or `role` cannot expand or replace that scope: employees still get only their reports, analysts only their assignments, and administrator/auditor lists remain unrestricted.

## Database relationships and service communication

`christophe/schema.sql` adds four tables and is applied after Joey's schema, idempotently on startup. Vulnerabilities and incidents reference `assets.id` with deletion restricted. Incidents reference reporter/assigned users; notes reference the incident and authenticated author. User references are restricted on deletion. Threats have a normalized composite unique key. Severity, lifecycle and CVSS constraints supplement request validation.

Each mutation stores an audit event transactionally using `joey.common.queue_audit`. Christophe’s `delivery.py` consumes the existing outbox through Karl’s `/api/Karl-Khouri/logs` and Joey’s `/api/Joey-Saade/notifications`, using their existing separate service keys. It coalesces concurrent delivery requests to one worker per process, reuses one HTTP client, skips already-delivered entries, drains notification-generated audits, and preserves failed entries for retry. Permission denials are queued by the shared handler and trigger automatic delivery through Christophe’s middleware. Assigned analysts receive assignment notices; active administrators receive security/threat/vulnerability alerts. Existing event-ID deduplication prevents duplicate records; `python -m joey.outbox` remains a compatible manual retry.

Karl's reports use actual list APIs with the caller's bearer token. Responses retain the expected `created_at`, `type`, `severity`, `status`, `assigned_to` and `cvss_score` fields. Shared user/asset reference checks use the existing common SQLite database, while event delivery and report aggregation use HTTP APIs.

## Postman and required real evidence

Import `postman/christophe.collection.json` and `postman/christophe.environment.template.json`. Fill `adminUsername`, `adminPassword`, and `newUserPassword` privately (the new password must satisfy Joey's 12–128 characters, letters and digits). Select the environment. Start required servers first and run folders in numeric order. Setup registers distinct accounts using a run timestamp, promotes an analyst/auditor via Joey's existing administrator API, obtains tokens and creates an asset. None of these is a new Christophe endpoint.

The remaining folders cover all 18 endpoints, multiple records/searches, unauthorized calls, malformed inputs, invalid IDs, both complete lifecycles, notes, peer notifications/audit/reports, and authorized deletion. Capture records and screenshots before Cleanup; Cleanup deletes test threats/vulnerabilities only. Incidents are retained because the brief supplies no delete operation. An interrupted earlier run may leave the fixed IP indicator `198.51.100.42`; delete it as administrator or use a clean disposable demo database before rerunning the collection. Imported integer ID variables are quoted in JSON and validated/coerced by Pydantic. Tokens expire after an hour; rerun Setup/logins when necessary.

Screenshots must show actual request inputs and outputs, with captions such as `Christophe ElChabab — Assign Incident — administrator assigns an incident to a Security Analyst`. Required evidence includes:

- Threats: multiple indicators/types/severities; stored records; all reads/search criteria; before/after update; duplicate/format rejection; authorized/unauthorized deletion.
- Vulnerabilities: multiple records/severities/statuses; stored data; all reads/search criteria; before/after update; full valid lifecycle and invalid transition; CVSS/CVE/asset errors; authorized/unauthorized deletion.
- Incidents: multiple severities with written justification; database records; all reads including invalid IDs; assignment/unauthorized assignment; each status transition; stored/retrieved notes; own/other-user access.
- Shared security: valid/invalid authentication; same API with correct/insufficient permission; validation errors; audit entries and assignment/alert notifications.
- Database: actual schema, PK/FKs, stored records, before/after changes, relationship explanation.

Prepare your named implementation/report sections, disclose AI assistance, and explain at least three APIs in the common report. Automated tests and captured text logs are real checks but do not replace Postman/database screenshots. No screenshots, saved response examples, student commits or completed report are claimed by this implementation.

## Actual verification status

The full Python suite passed 43 tests (31 new, 12 teammate tests). The exported collection also passed 86 requests and 86 assertions through Newman against all nine running services. See `docs/evidence/` for actual captured text output. `python tests/live_smoke_christophe.py --postman` repeats both live workflow and collection checks using a disposable database; Node.js/npm is needed only for the optional Newman step. The team still needs real screenshot evidence and the common report. No code was committed or pushed during this development session.

## Reviewed implementation (2026-10-18)

Current full name: **Christophe ElChabab**. Current prefix: `/api/Christophe-ElChabab`. Endpoint suffixes and methods remain exactly the 18 listed above. Old names in historical test transcripts are actual earlier executions, not active routes.

The strict review fixed malformed multi-dot domains, non-ASCII CVE digits, boolean IDs/CVSS inputs, missing automatic delivery after permission denials, response/authentication OpenAPI documentation, and overlapping outbox delivery work. Validated transactions protect reference checks and note authorization against concurrent writes. Positive/negative collection assertions check real response contents and this run's notification/audit events, with a bounded pre-request wait for asynchronous delivery.

Latest verification: **60 pytest tests passed**; **92 collection items and 214 assertions passed** against nine actual servers (96 HTTP requests including four event probes). The final run needed one successful probe per event check. See [review and limitations](christophe-review.md) and [actual evidence index](evidence/README.md). The 18 endpoints use bearer-auth security definitions, typed success schemas, standard error schemas, descriptions and summaries. Input samples and schemas remain documentation, not fabricated evidence.

All required screenshots and the common report remain pending. The professor's resolution of auditor searching and scoped incident lists is recorded in permissions.md; earlier verification counts above are historical.
