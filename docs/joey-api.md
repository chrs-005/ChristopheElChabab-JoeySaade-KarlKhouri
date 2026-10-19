# Joey Saade API reference

Three independent FastAPI processes serve routes under `/api/Joey-Saade`. OpenAPI is available at each process's `/docs`. Data is stored in the SQLite file named by `DATABASE_PATH`. Run commands are in [README](../README.md). The services share the same token secret and database; notification creation uses a separate service credential.

## Authentication and errors

`POST /users/login` accepts `username_or_email` and `password` and returns `{access_token, token_type, expires_in}`. All protected routes take `Authorization: Bearer <token>`. Tokens expire after one hour; each request reloads the user and rejects Inactive, Suspended or deleted accounts. The first administrator is created locally with `python -m joey.bootstrap_admin` and the five `BOOTSTRAP_ADMIN_*` environment variables. Public registration always creates a Regular Employee and rejects privileged role requests.

Errors use `{status: "error", message: "..."}`; request-shape errors additionally include `errors`. Main codes are 401 missing/invalid token, 403 forbidden, 404 absent record, 409 duplicate/referenced record, and 422 invalid input. Only known input keys are accepted. Database writes use parameter binding and constraints.

## Users and Identity (port 8001)

| Method and suffix | Access | Body / behavior |
|---|---|---|
| `POST /users/register` | Public | `full_name`, `username`, `email`, `password`, `department`, `role` (employee only); 201, no password hash |
| `POST /users/login` | Public | `username_or_email`, `password`; 200 token or 401/403 |
| `PUT /users/{id}` | Administrator or self | Any of `full_name`, `email`, `department`; role/status rejected |
| `DELETE /users/{id}` | Administrator | 409 if referenced by assets/notifications; self-delete blocked |
| `GET /users` | Administrator, Auditor | List without hashes |
| `GET /users/{username}` | Administrator, Auditor, self | Detail without hash |
| `PATCH /users/{id}/admin` | Administrator | Explicit role/status change; extra route for behavior mentioned outside brief's endpoint list |

Username permits 3–50 letters, digits, underscore, period and hyphen. Email must have a basic local/domain format. Password needs 12–128 characters containing letters and digits. Username and email are unique case-insensitively. PBKDF2-SHA256 uses a random salt and 260,000 iterations. A status change takes effect on the next authenticated request. Password hashes are never returned.

## Assets (port 8002)

| Method and suffix | Access | Body / behavior |
|---|---|---|
| `POST /assets` | Administrator | `name`, `type`, `ip_address`, `department`, `owner_id`, `location`, `criticality`; optional `operating_system`, `status` |
| `PUT /assets/{id}` | Administrator | Partial update of the same fields |
| `DELETE /assets/{id}` | Administrator | 409 on referencing FKs; deletion records history |
| `GET /assets` | Administrator, Auditor | All assets |
| `GET /assets/{id}` | Administrator, Analyst, Auditor | One asset |
| `GET /assets/search` | Administrator, Analyst, Auditor | Filters: `name` (substring), `type`, `ip_address`, `department`, `criticality` |
| `GET /assets/{id}/history` | Administrator, Auditor | Create/update/delete snapshots, even after deletion; extra route |

Allowed types: Server, Workstation, Database, Application, Network Device, Cloud Resource. IP accepts IPv4 or IPv6. Criticality: Low, Medium, High, Critical. Status: Active, Inactive, Under Maintenance. Employees have no asset access.

## Notifications (port 8003)

| Method and suffix | Access | Body / behavior |
|---|---|---|
| `POST /notifications` | Administrator or service key | `user_id`, `title`, `message`, `type`, `severity`; service calls require `event_id` and `X-Service-Key` |
| `GET /notifications/user/{user_id}` | Self, Administrator, Auditor | Recipient's list; Analyst can view own only |
| `GET /notifications/{id}` | Recipient, Administrator, Auditor | One item |
| `PUT /notifications/{id}/read` | Recipient or Administrator | Idempotent read timestamp update; Auditor cannot modify |
| `GET /notifications/search` | Administrator, Auditor, Analyst | `user_id`, `type`, `severity`, `status`; Analyst is restricted to own records |
| `DELETE /notifications/{id}` | Administrator | Delete item |

Types: Incident Assignment, Security Alert, System Notification, Threat Alert, Vulnerability Alert. Severity: Low, Medium, High, Critical. Status: Unread or Read. Duplicate `event_id` calls return the original notification. Registration queues a real welcome notification; a background task attempts delivery and `python -m joey.outbox` retries pending events.

## Integration and limitations

The audit outbox stores successful/failed login, user creation/update/delete, role/status change, asset changes, notification changes and forbidden access events. Current integration update: configure `AUDIT_SERVICE_URL` and `AUDIT_SERVICE_AUTH_SECRET` for Karl's implemented `POST /api/Karl-Khouri/logs`. Pending events can be retried with `python -m joey.outbox`. Christophe ElChabab's implemented incident, threat and vulnerability services now produce notifications using Joey's existing API and the shared outbox; the nine-service check verifies those calls. A scheduled outbox worker and separate production secret management are needed for long-running deployment.

User IDs are allocated monotonically and retained after account deletion. Registration welcome outbox IDs (`welcome-user-{id}`) therefore remain unique; a later account cannot inherit an old bearer token subject. On first startup with an older database, Joey's initialization seeds issued IDs from current users and historical welcome/audit events.
