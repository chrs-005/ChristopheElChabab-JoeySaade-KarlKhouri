# Security Incident Detection and Response Management System Backend

Sprint I backend for nine API services. The course brief (`Final Project Fall 2026-2027-Sprint 1.docx`, supplied separately) is authoritative. Joey's three services are runnable; the other six remain pending.

| Owner | Services |
|---|---|
| Joey Saade | Users and Identity Management; Asset Management; Notification and Alert Management |
| Karl Khoury | Threat Intelligence; Vulnerability Management; Incident Management |
| Christophe El Chabab | Security Audit Logging; Security Playbook and Response Automation; Security Reports |

## Run Joey's services

Use Python 3.12. Install with `python -m pip install -r requirements.txt`. Copy [.env.example](.env.example) to a local `.env`, fill `AUTH_SECRET` and `SERVICE_AUTH_SECRET` with different random values of at least 32 characters, and fill the five `BOOTSTRAP_ADMIN_*` values. Run `python -m joey.bootstrap_admin` once. The database schema is created automatically on startup. `.env` is ignored by Git.

Open three terminals from the repository root:

```text
python -m uvicorn joey.users:app --port 8001
python -m uvicorn joey.assets:app --port 8002
python -m uvicorn joey.notifications:app --port 8003
```

Run `python -m pytest tests/test_joey.py -q` and `python tests/live_smoke.py`. The smoke script starts all three services on ports 18001–18003 with a temporary database. Import [Joey's Postman collection](postman/joey.collection.json) and [environment template](postman/joey.environment.template.json); fill in credentials locally, then select the environment. Retry queued notifications and audit events with `python -m joey.outbox`. See [Joey API details](docs/joey-api.md) and [architecture](docs/architecture.md).

## Progress and handoffs

- [Canonical task board](docs/TASKS.md)
- [Joey handoff](docs/handoffs/joey-saade.md), [Karl handoff](docs/handoffs/karl-khoury.md), [Christophe handoff](docs/handoffs/christophe-el-chabab.md)
- [Joey implementation and evidence plan](docs/joey-implementation-plan.md)
- [Permissions](docs/permissions.md), [database](docs/database.md), [testing and Postman](docs/testing.md), [evidence](docs/evidence/README.md)
- [Contribution record](docs/CONTRIBUTIONS.md), [submission checklist](docs/submission-checklist.md)

Postman and test execution are documented in [testing](docs/testing.md). Real screenshots and integration evidence remain tracked in the [task board](docs/TASKS.md).
