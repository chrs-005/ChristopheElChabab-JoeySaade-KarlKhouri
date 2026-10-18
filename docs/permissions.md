# Permissions and unresolved brief conflicts

Role names in the brief: Security Administrator, Security Analyst, Security Auditor, Regular Employee. All protected calls require authentication, plus object-level checks. Employees may access only their own profiles/incidents/notifications where allowed; analysts need assignment checks on incidents; notification recipients are isolated. Read-only auditors may generate reports because that operation reads data. Avoid expanding access from broad role descriptions when an endpoint gives a narrower list.

Joey's implemented choices: public registration requires `role` to be Regular Employee; only administrators change role/status through `PATCH /users/{id}/admin`; asset history is read-only for administrators and auditors; administrators create notifications manually and an authenticated service credential may create notifications automatically. Analysts may only view/search their own notifications. Auditors may read notifications but cannot mark them read. These choices should be reviewed when Karl and Christophe integrate.

Still requiring team decisions: analyst log-search access; auditor threat-search access; immutable audit records versus explicitly authorized administrator deletion; access to other users' notifications for analysts/auditors. Joey currently permits auditors to read all notifications based on the brief's endpoint list, while analysts are limited to their own records. Do not silently broaden other services' permissions.

Unauthorized access must be auditable without trusting client-supplied actor fields or causing recursive audit calls.

Karl Khouri's implemented choices: audit logs are read and searched by administrators and auditors; any user may read their own entries via `GET /logs/user/{own id}`; only administrators delete, and each deletion leaves a permanent record. Analysts have no general log access pending the team decision above. Playbooks are created and extended by administrators and analysts, read by auditors too, and deleted by administrators; only the assigned user or an administrator moves an action's status. Reports are limited to administrators and auditors, and each upstream API re-checks the caller's own token.

## Christophe ElChabab's implemented scope

Threats: administrators create/update/delete; administrators, analysts and auditors list/read. Search is administrators/analysts only, following Service 4's specific authorization list; the broader role summary permits auditor searching, so this discrepancy remains a team/instructor clarification.

Vulnerabilities: administrators create/delete; administrators/analysts update; administrators/analysts/auditors read/search. Employees have no access.

Incidents: administrators and employees report; employees must use their own reporter ID. Administrators may report for an existing active user. Analysts read only assigned incidents, employees read only their own, and administrators/auditors may read all. The existing `GET /incidents` suffix returns scoped lists for analysts/employees to implement the role summary's “view assigned/submitted incidents”; the narrower per-endpoint list names only administrators/auditors. This interpretation is explicit and may need instructor confirmation. No extra list route was added.

Only administrators assign an active Security Analyst. Administrators and assigned analysts change status/add notes, following the service authorization list. Employees cannot see investigation-note content; an employee's detail response has an empty `notes` list. Auditors cannot mutate. Actor IDs on notes/audit events come from the verified token, not client-chosen fields.

Notifications target the assigned analyst on incident assignment and active administrators for newly reported incidents, threats and vulnerabilities (and escalation to High/Critical). These recipient choices implement alert-generation requirements whose full recipient policy is unspecified in the brief.
