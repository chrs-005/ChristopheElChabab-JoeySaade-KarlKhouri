# API contracts

Professor clarification supplied by Christophe on 2026-10-19: `GET /api/Christophe-ElChabab/threats/search` allows Administrator, Analyst and Auditor. `GET /api/Christophe-ElChabab/incidents` returns all records for Administrator/Auditor, assigned-only for Analyst, and submitted-only for Employee. Incident access predicates are derived from the authenticated identity and cannot be overridden through query parameters. No method/path pairs were added.

Every actual route must use `/api/<Confirmed-Full-Student-Name>` followed by the exact brief suffix. Implemented prefixes: `/api/Joey-Saade`, `/api/Karl-Khouri`, and `/api/Christophe-ElChabab`. Christophe explicitly confirmed his route name on 2026-10-18. Do not expose required APIs only as unprefixed routes.

| Owner | Brief suffixes |
|---|---|
| Joey: users | `POST /users/register`, `POST /users/login`, `PUT /users/{id}`, `DELETE /users/{id}`, `GET /users`, `GET /users/{username}` |
| Joey: assets | `POST /assets`, `PUT /assets/{id}`, `DELETE /assets/{id}`, `GET /assets`, `GET /assets/{id}`, `GET /assets/search` |
| Joey: notifications | `POST /notifications`, `GET /notifications/user/{user_id}`, `GET /notifications/{id}`, `PUT /notifications/{id}/read`, `GET /notifications/search`, `DELETE /notifications/{id}` |
| Christophe ElChabab: threats | `POST /threats`, `GET /threats`, `GET /threats/{id}`, `GET /threats/search`, `PUT /threats/{id}`, `DELETE /threats/{id}` |
| Christophe ElChabab: vulnerabilities | `POST /vulnerabilities`, `GET /vulnerabilities`, `GET /vulnerabilities/{id}`, `PUT /vulnerabilities/{id}`, `GET /vulnerabilities/search`, `DELETE /vulnerabilities/{id}` |
| Christophe ElChabab: incidents | `POST /incidents`, `GET /incidents`, `GET /incidents/{id}`, `PUT /incidents/{id}/assign`, `PUT /incidents/{id}/status`, `POST /incidents/{id}/notes` |
| Karl Khouri: logs (implemented) | `POST /logs`, `GET /logs`, `GET /logs/{id}`, `GET /logs/search`, `DELETE /logs/{id}`, `GET /logs/user/{user_id}` |
| Karl Khouri: reports (implemented) | `GET /reports/summary`, `GET /reports/incidents`, `GET /reports/assets`, `GET /reports/threats`, `GET /reports/vulnerabilities`, `GET /reports/activity` |
| Karl Khouri: playbooks (implemented) | `POST /playbooks`, `GET /playbooks`, `GET /playbooks/{id}`, `POST /playbooks/{id}/actions`, `PUT /actions/{id}/status`, `DELETE /playbooks/{id}` |

Joey's implemented conventions: signed bearer token with one-hour expiry and live status recheck; separate service credential for notification creation; JSON request/response; errors `{ "status": "error", "message": "..." }` with optional validation details; 401 missing/invalid authentication, 403 forbidden, 404 absent resource, 409 duplicate/conflict, 422 invalid input. Integer IDs and UTC ISO-8601 timestamps. Search routes are registered before dynamic IDs. See [Joey's API reference](joey-api.md) for request fields and success responses. Other owners must agree on token verification, pagination and dependency status conventions before implementing dependent services.

Joey's current queued audit payload is `{event_id, actor_user_id|null, actor_label, action, description, occurred_at, severity, related_service, subject_id}`. Karl Khouri's `POST /api/Karl-Khouri/logs` accepts exactly this payload with `X-Service-Key` set to `AUDIT_SERVICE_AUTH_SECRET` and deduplicates on `event_id`; see [Karl's API reference](karl-api.md). Reports call peers' list APIs with the caller's token and need `created_at`, `status` and `severity` fields. Notification creation accepts `{event_id, user_id, title, message, type, severity}`. Authenticated service calls need `X-Service-Key`; clients cannot set trusted audit actors. Notification events deduplicate on `event_id`. Christophe uses the existing outbox to call this notification API for incident assignment, security alerts, threat alerts and vulnerability alerts.

Christophe implements exactly six required endpoints per owned service. Responses use `id`, `created_at`, `severity`, `type` (threats), `assigned_to` (incidents), and `cvss_score`/`status` (vulnerabilities), as expected by Karl’s reports. See [API details](christophe-api.md) for fields, validation and professor-confirmed access restrictions.

Christophe's reviewed implementation now declares bearer authentication, typed success responses and standard error schemas directly in OpenAPI, with the same 18 suffixes. His delivery worker consumes the existing shared outbox using a persistent HTTP client and serialized delivery per process; failed events remain pending. Denials trigger delivery automatically. Current identity is `Christophe ElChabab` and prefix `/api/Christophe-ElChabab`; historical prefixes are not exposed as aliases.
