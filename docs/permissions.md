# Permissions and unresolved brief conflicts

## Instructor clarification supplied by Christophe on 2026-10-19

The professor confirmed that auditors may search threats; the missing entry in Service 4's endpoint-specific list was an oversight. `GET /threats/search` permits Administrator, Analyst and Auditor. The professor also confirmed `GET /incidents` for all four roles: Administrator/Auditor receive all incidents, Analyst only incidents assigned to the authenticated user, and Employee only incidents reported by the authenticated user. Server-side filtering uses the verified identity; query parameters cannot override role, reporter or assignee scope. These two questions are resolved and supersede earlier historical notes. Other teammate-service policy questions below were not part of this clarification.

Role names in the brief: Security Administrator, Security Analyst, Security Auditor, Regular Employee. All protected calls require authentication, plus object-level checks. Employees may access only their own profiles/incidents/notifications where allowed; analysts need assignment checks on incidents; notification recipients are isolated. Read-only auditors may generate reports because that operation reads data. Avoid expanding access from broad role descriptions when an endpoint gives a narrower list.

Joey's implemented choices: public registration requires `role` to be Regular Employee; only administrators change role/status through `PATCH /users/{id}/admin`; asset history is read-only for administrators and auditors; administrators create notifications manually and an authenticated service credential may create notifications automatically. Analysts may only view/search their own notifications. Auditors may read notifications but cannot mark them read. These choices should be reviewed when Karl and Christophe integrate.

Still requiring team decisions (analyst log-search access is now settled by the handout and implemented): immutable audit records versus explicitly authorized administrator deletion; access to other users' notifications for analysts/auditors. Joey currently permits auditors to read all notifications based on the brief's endpoint list, while analysts are limited to their own records. Do not silently broaden other services' permissions.

Unauthorized access must be auditable without trusting client-supplied actor fields or causing recursive audit calls.

Karl Khouri's implemented choices (updated 2026-10-20 to match the handout): audit logs are read and searched by administrators, analysts and auditors; any user may read their own entries via `GET /logs/user/{own id}`; only administrators delete, and each deletion leaves a permanent record. Playbooks are created only by administrators (the handout lists creation for administrators only); administrators and analysts add response actions; analysts and auditors read them; administrators delete them; only the assigned user or an administrator moves an action's status. Reports are limited to administrators and auditors, and each upstream API re-checks the caller's own token.

## Christophe ElChabab's implemented scope

Threats: administrators create/update/delete; administrators, analysts and auditors list/read/search. Auditor searching follows the professor's explicit clarification above. Employees have no threat access.

Vulnerabilities: administrators create/delete; administrators/analysts update; administrators/analysts/auditors read/search. Employees have no access.

Incidents: administrators and employees report; employees must use their own reporter ID. Administrators may report for an existing active user. `GET /incidents` gives administrators/auditors all records, analysts only their assigned records, and employees only their own reports. The professor confirmed this policy. The SQL predicate is determined by the authenticated user ID and live role, never client query parameters. No extra list route was added.

Only administrators assign an active Security Analyst. Administrators and assigned analysts change status/add notes, following the service authorization list. Employees cannot see investigation-note content; an employee's detail response has an empty `notes` list. Auditors cannot mutate. Actor IDs on notes/audit events come from the verified token, not client-chosen fields.

Notifications target the assigned analyst on incident assignment and active administrators for newly reported incidents, threats and vulnerabilities (and escalation to High/Critical). These recipient choices implement alert-generation requirements whose full recipient policy is unspecified in the brief.
