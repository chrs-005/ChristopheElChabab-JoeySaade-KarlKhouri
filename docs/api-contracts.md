# API contracts (draft, not implemented)

Every actual route must use `/api/<Confirmed-Full-Student-Name>` followed by the exact brief suffix. Confirmed prefixes: `/api/Joey-Saade`, `/api/Karl-Khoury`, and `/api/Christophe-El-Chabab`. Do not expose required APIs only as unprefixed routes.

| Owner | Brief suffixes |
|---|---|
| Joey: users | `POST /users/register`, `POST /users/login`, `PUT /users/{id}`, `DELETE /users/{id}`, `GET /users`, `GET /users/{username}` |
| Joey: assets | `POST /assets`, `PUT /assets/{id}`, `DELETE /assets/{id}`, `GET /assets`, `GET /assets/{id}`, `GET /assets/search` |
| Joey: notifications | `POST /notifications`, `GET /notifications/user/{user_id}`, `GET /notifications/{id}`, `PUT /notifications/{id}/read`, `GET /notifications/search`, `DELETE /notifications/{id}` |
| Karl: threats | `POST /threats`, `GET /threats`, `GET /threats/{id}`, `GET /threats/search`, `PUT /threats/{id}`, `DELETE /threats/{id}` |
| Karl: vulnerabilities | `POST /vulnerabilities`, `GET /vulnerabilities`, `GET /vulnerabilities/{id}`, `PUT /vulnerabilities/{id}`, `GET /vulnerabilities/search`, `DELETE /vulnerabilities/{id}` |
| Karl: incidents | `POST /incidents`, `GET /incidents`, `GET /incidents/{id}`, `PUT /incidents/{id}/assign`, `PUT /incidents/{id}/status`, `POST /incidents/{id}/notes` |
| Christophe: logs | `POST /logs`, `GET /logs`, `GET /logs/{id}`, `GET /logs/search`, `DELETE /logs/{id}`, `GET /logs/user/{user_id}` |
| Christophe: reports | `GET /reports/summary`, `GET /reports/incidents`, `GET /reports/assets`, `GET /reports/threats`, `GET /reports/vulnerabilities`, `GET /reports/activity` |
| Christophe: playbooks | `POST /playbooks`, `GET /playbooks`, `GET /playbooks/{id}`, `POST /playbooks/{id}/actions`, `PUT /actions/{id}/status`, `DELETE /playbooks/{id}` |

Joey's implemented conventions: signed bearer token with one-hour expiry and live status recheck; separate service credential for notification creation; JSON request/response; errors `{ "status": "error", "message": "..." }` with optional validation details; 401 missing/invalid authentication, 403 forbidden, 404 absent resource, 409 duplicate/conflict, 422 invalid input. Integer IDs and UTC ISO-8601 timestamps. Search routes are registered before dynamic IDs. See [Joey's API reference](joey-api.md) for request fields and success responses. Other owners must agree on token verification, pagination and dependency status conventions before implementing dependent services.

Joey's current queued audit payload is `{event_id, actor_user_id|null, actor_label, action, description, occurred_at, severity, related_service, subject_id}`. Christophe should confirm the final `POST /logs` fields before enabling delivery. Notification creation accepts `{event_id, user_id, title, message, type, severity}`. Authenticated service calls need `X-Service-Key`; clients cannot set trusted audit actors. Notification events deduplicate on `event_id`. Karl can use the notification API for assignment, threat and vulnerability triggers once his services exist.
