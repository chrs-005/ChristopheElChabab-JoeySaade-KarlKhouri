# Permissions and unresolved brief conflicts

Role names in the brief: Security Administrator, Security Analyst, Security Auditor, Regular Employee. All protected calls require authentication, plus object-level checks. Employees may access only their own profiles/incidents/notifications where allowed; analysts need assignment checks on incidents; notification recipients are isolated. Read-only auditors may generate reports because that operation reads data. Avoid expanding access from broad role descriptions when an endpoint gives a narrower list.

Pending instructor/team clarification: analyst log-search access; auditor threat-search access; registration's role field versus public privilege escalation (provisional: public registration creates Regular Employee only); who may invoke role management and its exact route (provisional: administrator only); asset history route/representation; immutable audit records versus explicitly authorized administrator deletion; which actors can create notifications manually. Document the resolved matrix before implementing these cases.

Unauthorized access must be auditable without trusting client-supplied actor fields or causing recursive audit calls.
