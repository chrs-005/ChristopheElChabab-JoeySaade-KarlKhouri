# Joey Saade: implementation and demonstration plan

This plan now accompanies runnable Joey code in `joey/`. Joey owns Users and Identity, Asset Management, and Notification and Alert Management. All 18 required routes are implemented, while screenshots and Karl/Christophe dependent integrations remain pending. Do not mark an API DONE from this document alone.

## Sequence

1. Agree with Karl and Christophe on the stack, independent service boundaries, database topology, IDs/timestamps, token verification and audit/notification contracts. Record the decision in `architecture.md` and `api-contracts.md`.
2. Build the Users schema and registration/login first. Use a unique username constraint, password hashes, four roles, and Active/Inactive/Suspended status. Decide what happens to references when an account is deleted. A public registration must never grant an administrator, analyst or auditor role.
3. Protect user APIs with role and object checks. Employee update/read targets must match the authenticated identity. Administrators may manage users; auditors may list/read; the brief gives analysts no user-management access. Resolve administrator role changes as an explicit restricted operation. Register `/users/register` and `/users/login` before the username route.
4. Build Assets using an owner reference to Users. Keep the required name, type, IP, operating system where applicable, department, owner, location, criticality and status. Validate addresses and enum values. Before deletion, decide what happens if incidents or vulnerabilities refer to the asset. Keep a usable asset history contract.
5. Build Notifications using a recipient reference to Users, type/severity/status, creation/read timestamps, and authenticated internal creation. Read and mark-read calls must check the recipient, not just the role. Provide deduplication for retries. Agree with Karl on incident-assignment, threat and vulnerability trigger payloads.
6. Integrate audit calls after Christophe publishes the event contract. Handle delivery failure explicitly and avoid sending privileged service credentials in user-facing responses.

## Endpoint ownership and evidence

| Service | Required suffixes | Minimum real evidence |
|---|---|---|
| Users | `POST /users/register`; `POST /users/login`; `PUT /users/{id}`; `DELETE /users/{id}`; `GET /users`; `GET /users/{username}` | Registration/database record; duplicate username; successful and failed login; authorized and forbidden update/delete; existing and missing username |
| Assets | `POST /assets`; `PUT /assets/{id}`; `DELETE /assets/{id}`; `GET /assets`; `GET /assets/{id}`; `GET /assets/search` | Multiple created records; before/after update; authorized and forbidden delete; existing/missing detail; searches by name, type, IP, department and criticality |
| Notifications | `POST /notifications`; `GET /notifications/user/{user_id}`; `GET /notifications/{id}`; `PUT /notifications/{id}/read`; `GET /notifications/search`; `DELETE /notifications/{id}` | Stored records; recipient and empty list; existing/missing detail; before/after read; filters for user, type, severity and status; authorized/forbidden delete; automatic trigger |

Each route starts with `/api/Joey-Saade`. For every endpoint, document request fields, response, statuses and errors; add Postman assertions; test missing/invalid fields, missing/invalid/expired token, role and cross-user access. Capture actual execution and database output. Caption screenshots `Joey Saade — API call title — what it demonstrates.`

## Open decisions to settle before code

- Stack and migration tool; one shared database with service-owned tables versus separate databases and API-validated references.
- Exact user role-management route and asset-history representation, since the brief mentions behavior without a fixed endpoint.
- Registration's required `role` field versus safe public registration: proposed employee-only public registration and admin-only privileged creation.
- Notification permissions: the brief lists analyst/auditor user retrieval but does not clearly define whether they may access other recipients. Proposed default is own notifications unless an explicitly scoped administrative need is approved.
- Token type, expiry, revocation, service authentication, request IDs, timeouts and retry deduplication.

Do not infer that a blank Postman collection or example response is execution evidence. After each coding session, update the task board, this plan if decisions change, the Joey handoff, contribution record and actual test results.
