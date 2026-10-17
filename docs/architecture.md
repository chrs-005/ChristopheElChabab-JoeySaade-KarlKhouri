# Architecture decisions and open questions

The brief requires nine independent backend services communicating by APIs, plus database PK/FK relationships. No stack or implementation exists yet. **Decision pending:** choose a service boundary and database topology before schemas are created. Options include independently deployed services with separate databases (references validated by API, no cross-database FKs) or independently deployed services sharing a database (physical FKs possible, but table ownership and access must stay strict). The team must reconcile the brief's FK requirement with independence; nine route modules in one tightly coupled app alone do not demonstrate independent services.

Provisional rules: each owner controls their service tables and API; service URLs and secrets come from environment variables; cross-service requests have timeouts, authenticated service identity, explicit dependency failures, and idempotency or deduplication for retryable side effects. Reports consume service APIs, not peers' tables. No service gets general administrator credentials for integration.

## Decisions required before implementation

1. Stack, process layout, database topology, migration ownership, local startup commands.
2. Student names were confirmed by Joey: Joey Saade, Karl Khoury, Christophe El Chabab. Route prefixes are `/api/Joey-Saade`, `/api/Karl-Khoury`, and `/api/Christophe-El-Chabab`.
3. Token claims, signing/verification, expiry and revocation; narrowly scoped service credentials.
4. ID format, UTC timestamp representation, enum serialization, pagination and error format.
5. Audit delivery on failures and failed login, avoiding loops; notification delivery and retry deduplication.
6. Resolve permission contradictions in [permissions](permissions.md) with the instructor where needed.

## Integration order

Joey starts authentication/roles and assets. Karl can build against documented contracts before services run and integrate once auth/assets are usable. Christophe can define audit events immediately, then build playbooks when user/workflow contracts exist. Reports use real data from the other APIs and come last. Tests with doubles must be labeled as such.
