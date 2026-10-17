# Architecture decisions and open questions

The brief requires nine independent backend services communicating by APIs, plus database PK/FK relationships. Joey's implementation runs three separate FastAPI processes with a shared SQLite database so local FK constraints work. Each process exposes only its owned routes. This is a provisional local topology; the team must choose a production database and table ownership plan before Karl and Christophe add schemas. SQLite is suitable for the local Sprint I demo, but concurrent multi-process writes may require migration to PostgreSQL.

Joey's apps use shared signed bearer tokens, checked against current user status on each request. A separate secret authenticates calls to notification creation. Users writes a welcome event to a transactional outbox; the notification service deduplicates by event ID. Audit events are queued for Christophe's future API and remain pending until its URL and separate credential are configured. Cross-service calls have a three-second timeout. Reports must consume service APIs, not peers' tables. No service gets general administrator credentials for integration.

## Decisions required before implementation

1. Confirm whether to retain Joey's FastAPI/SQLite local stack for team integration, and choose the longer-term database, migration ownership and deployment layout.
2. Student names were confirmed by Joey: Joey Saade, Karl Khoury, Christophe El Chabab. Route prefixes are `/api/Joey-Saade`, `/api/Karl-Khoury`, and `/api/Christophe-El-Chabab`.
3. Token claims, signing/verification, expiry and revocation; narrowly scoped service credentials.
4. ID format, UTC timestamp representation, enum serialization, pagination and error format.
5. Audit delivery on failures and failed login, avoiding loops; notification delivery and retry deduplication.
6. Resolve permission contradictions in [permissions](permissions.md) with the instructor where needed.

## Integration order

Joey starts authentication/roles and assets. Karl can build against documented contracts before services run and integrate once auth/assets are usable. Christophe can define audit events immediately, then build playbooks when user/workflow contracts exist. Reports use real data from the other APIs and come last. Tests with doubles must be labeled as such.
