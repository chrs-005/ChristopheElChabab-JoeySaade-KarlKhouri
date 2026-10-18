# API contracts (draft, not implemented)

Every actual route must use `/api/<Confirmed-Full-Student-Name>` followed by the exact brief suffix. Confirmed prefixes: `/api/Joey-Saade`, `/api/Karl-Khoury`, and `/api/Christophe-El-Chabab`. Karl's implemented services use `/api/Karl-Khouri` at his request; the team should settle one spelling. Do not expose required APIs only as unprefixed routes.

| Owner | Brief suffixes |
|---|---|
| Joey: users | `POST /users/register`, `POST /users/login`, `PUT /users/{id}`, `DELETE /users/{id}`, `GET /users`, `GET /users/{username}` |
| Joey: assets | `POST /assets`, `PUT /assets/{id}`, `DELETE /assets/{id}`, `GET /assets`, `GET /assets/{id}`, `GET /assets/search` |
| Joey: notifications | `POST /notifications`, `GET /notifications/user/{user_id}`, `GET /notifications/{id}`, `PUT /notifications/{id}/read`, `GET /notifications/search`, `DELETE /notifications/{id}` |
| Karl: threats | `POST /threats`, `GET /threats`, `GET /threats/{id}`, `GET /threats/search`, `PUT /threats/{id}`, `DELETE /threats/{id}` |
| Karl: vulnerabilities | `POST /vulnerabilities`, `GET /vulnerabilities`, `GET /vulnerabilities/{id}`, `PUT /vulnerabilities/{id}`, `GET /vulnerabilities/search`, `DELETE /vulnerabilities/{id}` |
| Karl: incidents | `POST /incidents`, `GET /incidents`, `GET /incidents/{id}`, `PUT /incidents/{id}/assign`, `PUT /incidents/{id}/status`, `POST /incidents/{id}/notes` |
| Karl Khouri: logs (implemented) | `POST /logs`, `GET /logs`, `GET /logs/{id}`, `GET /logs/search`, `DELETE /logs/{id}`, `GET /logs/user/{user_id}` |
| Karl Khouri: reports (implemented) | `GET /reports/summary`, `GET /reports/incidents`, `GET /reports/assets`, `GET /reports/threats`, `GET /reports/vulnerabilities`, `GET /reports/activity` |
| Karl Khouri: playbooks (implemented) | `POST /playbooks`, `GET /playbooks`, `GET /playbooks/{id}`, `POST /playbooks/{id}/actions`, `PUT /actions/{id}/status`, `DELETE /playbooks/{id}` |

Joey's implemented conventions: signed bearer token with one-hour expiry and live status recheck; separate service credential for notification creation; JSON request/response; errors `{ "status": "error", "message": "..." }` with optional validation details; 401 missing/invalid authentication, 403 forbidden, 404 absent resource, 409 duplicate/conflict, 422 invalid input. Integer IDs and UTC ISO-8601 timestamps. Search routes are registered before dynamic IDs. See [Joey's API reference](joey-api.md) for request fields and success responses. Other owners must agree on token verification, pagination and dependency status conventions before implementing dependent services.

Joey's current queued audit payload is `{event_id, actor_user_id|null, actor_label, action, description, occurred_at, severity, related_service, subject_id}`. Karl Khouri's `POST /api/Karl-Khouri/logs` accepts exactly this payload with `X-Service-Key` set to `AUDIT_SERVICE_AUTH_SECRET` and deduplicates on `event_id`; see [Karl's API reference](karl-api.md). Reports call peers' list APIs with the caller's token and need `created_at`, `status` and `severity` fields. Notification creation accepts `{event_id, user_id, title, message, type, severity}`. Authenticated service calls need `X-Service-Key`; clients cannot set trusted audit actors. Notification events deduplicate on `event_id`. Karl can use the notification API for assignment, threat and vulnerability triggers once his services exist.
