# Security Incident Detection and Response Management System Backend

Sprint I backend for nine API services. The course brief (`Final Project Fall 2026-2027-Sprint 1.docx`, supplied separately) is authoritative. The submission includes the three owners' source code, database creation scripts, Postman collections and a common report with 180 API/database/Git captures. The repository link is provided in the submission package.

| Owner | Services |
|---|---|
| Joey Saade | Users and Identity Management; Asset Management; Notification and Alert Management |
| Karl Khouri | Security Audit Logging; Security Playbook and Response Automation; Security Reports |
| Christophe ElChabab | Threat Intelligence; Vulnerability Management; Incident Management |

## Run Joey's services

Use Python 3.12. Install with `python -m pip install -r requirements.txt`. Copy [.env.example](.env.example) to a local `.env`, fill `AUTH_SECRET` and `SERVICE_AUTH_SECRET` with different random values of at least 32 characters, and fill the five `BOOTSTRAP_ADMIN_*` values. Run `python -m joey.bootstrap_admin` once. The database schema is created automatically on startup. `.env` is ignored by Git.

Open three terminals from the repository root:

```text
python -m uvicorn joey.users:app --port 8001
python -m uvicorn joey.assets:app --port 8002
python -m uvicorn joey.notifications:app --port 8003
```

Run `python -m pytest tests/test_joey.py -q` and `python tests/live_smoke.py`. The smoke script uses a temporary database and separate test ports. For Postman, start the services on ports 8001--8003, import [Joey's collection](postman/joey.collection.json) and [environment template](postman/joey.environment.template.json), fill in credentials locally and select the environment. The collection uses literal localhost URLs; run its folders in order with Cleanup last. Retry queued notifications and audit events with `python -m joey.outbox`. See [Joey API details](docs/joey-api.md) and [architecture](docs/architecture.md).

## Run Karl Khouri's services

Karl Khouri implemented Security Audit Logging, Security Playbook and Response Automation, and Security Reports (the set listed for Joey in the team's proposed ownership plan) under `/api/Karl-Khouri`. They reuse the setup above; also set `AUDIT_SERVICE_AUTH_SECRET` (a third, different secret) and, if needed, the `*_REPORT_SOURCE` URLs from [.env.example](.env.example). Start the users service as well, since it issues the tokens:

```text
python -m uvicorn karl.audit_logs:app --port 8007
python -m uvicorn karl.playbooks:app --port 8008
python -m uvicorn karl.reports:app --port 8009
```

Run `python -m pytest tests/test_karl.py -q` and `python tests/live_smoke_karl.py` (six real processes on ports 18001–18009 with a temporary database). `python tests/postman_karl.py` runs the exported collection with Newman against all nine services (needs Node.js; on Windows set `NODE_OPTIONS=--use-system-ca`). Import [Karl's Postman collection](postman/karl.collection.json) and [environment template](postman/karl.environment.template.json); fill the administrator's `username`, `userPassword` and `auditServiceKey`, start all nine services, and run the folders in order. See [Karl's API reference](docs/karl-api.md). The ownership table above reflects the implemented split confirmed by Christophe.

## Run Christophe ElChabab's services

Use the same virtual environment, secrets and database as the other services. Start users, assets, notifications and audit logging for authentication and event delivery, plus reports when checking integration. Christophe's tables are created on startup from `christophe/schema.sql`.

```text
python -m uvicorn christophe.threats:app --port 8004
python -m uvicorn christophe.vulnerabilities:app --port 8005
python -m uvicorn christophe.incidents:app --port 8006
```

All 18 required routes use `/api/Christophe-ElChabab`. The three report source defaults and `.env.example` point to that prefix; update an existing private `.env` if it still uses `Christophe-El-Chabab`. No alias endpoints were added.

Run `python -m pytest tests -q` and `python tests/live_smoke_christophe.py`. The latter starts all nine services on ports 18001–18009 with a disposable database and stops them afterward. Import [Christophe's collection](postman/christophe.collection.json) and [environment template](postman/christophe.environment.template.json). Fill administrator credentials and `newUserPassword` locally; run folders in order and capture actual screenshots before Cleanup. See [Christophe API and evidence guide](docs/christophe-api.md) and the [strict review record](docs/christophe-review.md).

## Progress and handoffs

- [Canonical task board](docs/TASKS.md)
- [Joey handoff](docs/handoffs/joey-saade.md), [Karl handoff](docs/handoffs/karl-khoury.md), [Christophe handoff](docs/handoffs/christophe-el-chabab.md)
- [Joey implementation and evidence plan](docs/joey-implementation-plan.md), [Karl API reference](docs/karl-api.md)
- [Permissions](docs/permissions.md), [database](docs/database.md), [testing and Postman](docs/testing.md), [evidence](docs/evidence/README.md)
- [Contribution record](docs/CONTRIBUTIONS.md), [submission checklist](docs/submission-checklist.md)

Postman and test execution are documented in [testing](docs/testing.md). Real screenshots and integration evidence remain tracked in the [task board](docs/TASKS.md).
