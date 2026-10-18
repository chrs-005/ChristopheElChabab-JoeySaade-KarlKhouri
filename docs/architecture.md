# Current Sprint I architecture

The nine services run as independent FastAPI processes. They retain the team's shared local SQLite database for real user, asset and relationship foreign keys. Authentication uses Joey's signed bearer tokens and rechecks account status on each request.

| Owner | Service | Port |
|---|---|---|
| Joey Saade | Users / Assets / Notifications | 8001 / 8002 / 8003 |
| Christophe ElChabab | Threats / Vulnerabilities / Incidents | 8004 / 8005 / 8006 |
| Karl Khouri | Audit logging / Playbooks / Reports | 8007 / 8008 / 8009 |

Christophe's mutations atomically store their data and audit/notification events in the existing transactional outbox. After commit, Christophe’s coalesced delivery worker uses a reusable HTTP client to call Karl’s audit API and Joey’s notification API with their separate service credentials, three-second timeouts and event IDs. Failed deliveries remain queued; `python -m joey.outbox` retries them. Notification creation itself queues audit records, which Christophe’s worker drains in a subsequent batch. Forbidden requests are queued by the shared error handler and automatically dispatched by Christophe’s own middleware.

Reports call the owned list APIs with the actual caller's bearer token. Christophe returns the field names Karl already expects. The report-source defaults and environment template now use `/api/Christophe-ElChabab`; an existing private configuration must be updated if it overrides those defaults.

Local foreign-key/reference validation reads the shared Users and Assets tables; no second copy of their data is maintained. Audit/notification delivery and report aggregation use actual API calls. This preserves the existing topology rather than redesigning teammates' services.

The nine-process check in `tests/live_smoke_christophe.py` verifies registration/login, assets, threats, vulnerabilities, incident assignment/notes/lifecycle, notifications, audit records, a playbook action, and reports against a disposable database. Real Postman/database screenshots and the final report architecture/schema diagrams still need team preparation.

See [permissions](permissions.md) for ambiguities in the brief and [API contracts](api-contracts.md) for current interfaces.
