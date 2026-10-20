# Karl Khouri API reference

Karl Khouri owns Security Audit Logging, Security Playbook and Response Automation, and Security Reports. Each runs as its own FastAPI process under `/api/Karl-Khouri`; OpenAPI is at each process's `/docs`. Code is in [`karl/`](../karl/), tables in [`karl/schema.sql`](../karl/schema.sql). The services use the team's bearer tokens and error format from [`joey/common.py`](../joey/common.py) and the same SQLite file (`DATABASE_PATH`) so foreign keys to `users(id)` hold. Run commands are in the [README](../README.md).

Errors use `{status: "error", message: "..."}` like the other services. 401 missing/invalid token or service key, 403 forbidden role or object, 404 absent record, 409 conflict or invalid workflow transition, 422 invalid input, 502/503 upstream failure (reports only). Unknown body fields are rejected. Dates in filters accept `YYYY-MM-DD` or ISO-8601 datetimes; a bare `end_date` covers the whole day.

## Security Audit Logging (port 8007)

| Method and suffix | Access | Body / behavior |
|---|---|---|
| `POST /logs` | Service key, or Administrator | Service: `event_id`, `action`, `related_service` required; optional `actor_user_id`, `actor_label`, `description`, `occurred_at`, `severity`, `subject_id`. Administrator: actor and time come from the token and clock; sending actor/time fields is rejected (422). 201 created; 200 with the original entry for a repeated `event_id` |
| `GET /logs` | Administrator, Auditor | All entries, newest first |
| `GET /logs/{id}` | Administrator, Analyst, Auditor | One entry |
| `GET /logs/search` | Administrator, Analyst, Auditor | `actor_user_id`, `action`, `severity`, `related_service`, `subject_id`, `start_date`, `end_date` (AND-combined) |
| `DELETE /logs/{id}` | Administrator | Removes the entry and writes a permanent `audit_log_deleted` entry naming it; deletion entries cannot be deleted (409) |
| `GET /logs/user/{user_id}` | Administrator, Auditor | Entries by that actor, including after the user account is deleted; an empty list when the user has no logs. No self-access exception: analysts and employees get 403 even for their own ID |

Event schema matches the outbox payload already produced by the users, assets and notifications services: `{event_id, actor_user_id|null, actor_label, action, description, occurred_at, severity, related_service, subject_id}`. `action` is lowercase (`login_failed`, `user_created`, `role_changed`, `asset_updated`, `unauthorized_access`, ...). Severity: Information, Warning, Error, Critical. `source` records how the entry arrived: `service`, `user` or `audit`.

Integrity rules:

- Service calls send `X-Service-Key: <AUDIT_SERVICE_AUTH_SECRET>`. This secret must differ from `SERVICE_AUTH_SECRET`, so a notification credential cannot write audit records.
- A failed login has no authenticated actor: `actor_user_id` is null and `actor_label` holds the attempted username.
- IDs use AUTOINCREMENT, so a deleted entry's ID is never reused (the same applies to playbooks and response actions; older databases are migrated on startup).
- A database trigger rejects any UPDATE of an entry. The only allowed change is the foreign key nulling `actor_user_id` when a user is deleted; `original_actor_user_id` and `actor_label` keep the history.
- An event for a user deleted before delivery is stored with the original ID only, instead of failing.
- No recursion: this service's own denials and deletions are written straight to its table, never through HTTP or the outbox. Other services queue events in the `outbox` table, so audit downtime never blocks their requests; `python -m joey.outbox` retries pending events, and concurrent retries of the same `event_id` keep only the first copy.

## Security Playbook and Response Automation (port 8008)

| Method and suffix | Access | Body / behavior |
|---|---|---|
| `POST /playbooks` | Administrator | `name` (unique, case-insensitive), `description`, `category`, `severity`, optional ordered `steps` (`title`, `description`, `assigned_to`, optional `step_order`). Creator and timestamps come from the server |
| `GET /playbooks` | Administrator, Analyst, Auditor | Optional `category`, `severity` filters; each playbook includes its actions and progress |
| `GET /playbooks/{id}` | Administrator, Analyst, Auditor | Playbook, ordered `actions`, `execution_status` (Not Started, In Progress, Completed), `completed_steps`, `total_steps` |
| `POST /playbooks/{id}/actions` | Administrator, Analyst | Required: `description`, `step_order` (must be the next number). Optional: `title` (defaults to the description), `assigned_to` |
| `PUT /actions/{id}/status` | Administrator, Analyst | Any of `status`, `assigned_to`, `completion_date` (only with `status: Completed`), optional `note` |
| `DELETE /playbooks/{id}` | Administrator | Deletes the playbook and its actions; 409 while an action is In Progress. Execution history is kept |
| `GET /playbooks/{id}/history` | Administrator, Analyst, Auditor | Every creation and status change with who and when; extra route, still available after deletion |

Categories: Malware, Phishing, Ransomware, Unauthorized Access, Data Breach, Denial of Service, Insider Threat, Vulnerability Remediation, Other. Severity: Low, Medium, High, Critical.

Response workflow:

1. Steps are numbered 1, 2, 3 ... with no gaps or duplicates. A gap returns 422, an existing number returns 409. The database also enforces `UNIQUE(playbook_id, step_order)`.
2. An assignee is optional when the step is created; when given (at creation or later through the status route) it must be an active Security Analyst or Security Administrator. An unassigned step cannot change status.
3. Status moves only Pending → In Progress → Completed. Skipping or going back returns 409.
4. A step cannot start until every earlier step is Completed (409 names the blocking step).
5. Start and completion times, the completing user, and an `action_history` row are recorded for each change.
6. Assigning a step queues a notification to the assignee (event ID `playbook-action-{id}-assigned` at creation, a unique ID for later assignments). Playbook and action changes queue audit events.

## Security Reports (port 8009)

| Suffix | Source API | Content |
|---|---|---|
| `GET /reports/summary` | Users plus all five below | Each section's figures, `complete`, and `unavailable` (source, status, message) for any source that failed. A failed section is `null`, never zero |
| `GET /reports/incidents` | Incidents list | `total`, `by_status`, `by_severity`, `open` (not Resolved/Closed), `unassigned` |
| `GET /reports/assets` | Assets list | `total`, `by_type`, `by_criticality`, `by_status`, `by_department`, `active_high_or_critical` |
| `GET /reports/threats` | Threats list | `total`, `by_type`, `by_severity` |
| `GET /reports/vulnerabilities` | Vulnerabilities list | `total`, `by_severity`, `by_status`, `open`, `average_cvss` (null without scores) |
| `GET /reports/activity` | Audit logs list | `total_events`, `by_action`, `by_severity`, `by_service`, `failed_logins`, `unauthorized_access`, `top_actors`, first/last event time |

Only administrators and auditors can generate reports. Every report accepts `start_date` and `end_date`, applied to each record's `created_at` (`occurred_at` for activity); records without a readable timestamp are left out of a filtered period. Each report records a `report_generated` audit event.

Aggregation rules: reports never read another service's tables. They call each service's list API with the caller's own token, so the upstream's permissions still apply (an upstream 401/403 is returned as is). An unreachable or unconfigured upstream gives 503; a non-200 reply or a body that is not a list of objects (or `{items: [...]}`) gives 502. Upstream list URLs are set by `ASSET_REPORT_SOURCE`, `INCIDENT_REPORT_SOURCE`, `THREAT_REPORT_SOURCE`, `VULNERABILITY_REPORT_SOURCE` and `AUDIT_REPORT_SOURCE` (see [.env.example](../.env.example)); `REPORT_UPSTREAM_TIMEOUT` defaults to 5 seconds. Upstream owners need to return the fields named above for their groupings to be filled; missing values are grouped as `Unspecified`.

## Integration status

- The users, assets and notifications services' queued audit events are delivered to `POST /api/Karl-Khouri/logs` when `AUDIT_SERVICE_URL` and `AUDIT_SERVICE_AUTH_SECRET` are set; verified by [tests](../tests/test_karl.py) and the [live HTTP check](evidence/karl-live-http-2026-10-18.txt).
- Asset and activity reports reconcile with stored records in the same checks.
- Threats, vulnerabilities and incidents services are not running yet, so their reports currently return 503. Their owners can call `POST /logs` with the audit service key (or queue events in `outbox`) to log their data changes.
