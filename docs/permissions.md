# Permissions and unresolved brief conflicts

Role names in the brief: Security Administrator, Security Analyst, Security Auditor, Regular Employee. All protected calls require authentication, plus object-level checks. Employees may access only their own profiles/incidents/notifications where allowed; analysts need assignment checks on incidents; notification recipients are isolated. Read-only auditors may generate reports because that operation reads data. Avoid expanding access from broad role descriptions when an endpoint gives a narrower list.

Joey's implemented choices: public registration requires `role` to be Regular Employee; only administrators change role/status through `PATCH /users/{id}/admin`; asset history is read-only for administrators and auditors; administrators create notifications manually and an authenticated service credential may create notifications automatically. Analysts may only view/search their own notifications. Auditors may read notifications but cannot mark them read. These choices should be reviewed when Karl and Christophe integrate.

Still requiring team decisions: analyst log-search access; auditor threat-search access; immutable audit records versus explicitly authorized administrator deletion; access to other users' notifications for analysts/auditors. Joey currently permits auditors to read all notifications based on the brief's endpoint list, while analysts are limited to their own records. Do not silently broaden other services' permissions.

Unauthorized access must be auditable without trusting client-supplied actor fields or causing recursive audit calls.
