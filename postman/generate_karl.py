"""Generate Karl Khouri's collection (audit logging, playbooks, reports) and a credential-free environment template."""
import json
from pathlib import Path

root = Path(__file__).parent
auth = [{"key": "Authorization", "value": "Bearer {{token}}"}]
service = [{"key": "X-Service-Key", "value": "{{auditServiceKey}}"}]
ok = ["pm.test('Successful response', function () { pm.expect(pm.response.code).to.be.oneOf([200, 201]); });"]


def status(code, label):
    return [f"pm.test('{label}', () => pm.response.to.have.status({code}));"]


def request(name, method, base, path, body=None, headers=None, tests=None, prefix="/api/Karl-Khouri"):
    header = list(auth if headers is None else headers)
    if body is not None:
        header.append({"key": "Content-Type", "value": "application/json"})
    req = {"method": method, "header": header, "url": "{{" + base + "}}" + prefix + path, "description": f"Karl Khouri — {name}. Run against your own backend and inspect the actual response."}
    if body is not None:
        req["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2), "options": {"raw": {"language": "json"}}}
    return {"name": name, "request": req, "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": tests or ok}}]}


setup = [
    request("Login (users service)", "POST", "userUrl", "/users/login", {"username_or_email": "{{username}}", "password": "{{userPassword}}"}, [], status(200, "Authenticated") + ["if (pm.response.code === 200) pm.environment.set('token', pm.response.json().access_token);"], prefix="/api/Joey-Saade"),
]
log_event = {"event_id": "{{eventId}}", "actor_user_id": None, "actor_label": "unknown_user", "action": "login_failed", "description": "Failed login attempt", "severity": "Warning", "related_service": "users"}
logs = [
    request("Create log as service", "POST", "auditUrl", "/logs", log_event, service, ["pm.test('Stored or deduplicated', () => pm.expect(pm.response.code).to.be.oneOf([200, 201]));", "if (pm.response.code < 300) pm.environment.set('logId', pm.response.json().id);"]),
    request("Create manual log as administrator", "POST", "auditUrl", "/logs", {"action": "manual_review", "description": "Reviewed firewall changes", "severity": "Information"}, tests=status(201, "Created") + ["pm.test('Actor comes from token', () => pm.expect(pm.response.json().source).to.eql('user'));"]),
    request("List logs", "GET", "auditUrl", "/logs", tests=status(200, "Listed")),
    request("Get log", "GET", "auditUrl", "/logs/{{logId}}", tests=status(200, "Found")),
    request("Search logs", "GET", "auditUrl", "/logs/search?action=login_failed&severity=Warning", tests=status(200, "Searched") + ["pm.test('Only matching entries', () => pm.response.json().forEach(x => pm.expect(x.action).to.eql('login_failed')));"]),
    request("Logs for user", "GET", "auditUrl", "/logs/user/{{userId}}", tests=status(200, "Listed")),
    request("Delete log", "DELETE", "auditUrl", "/logs/{{logId}}", tests=status(200, "Deleted")),
]
playbook_body = {"name": "Phishing containment {{$timestamp}}", "description": "Contain a reported phishing email", "category": "Phishing", "severity": "High", "steps": [
    {"title": "Block sender", "description": "Block the sender domain", "assigned_to": "{{analystId}}"},
    {"title": "Purge messages", "description": "Remove delivered copies", "assigned_to": "{{analystId}}"}]}
playbooks = [
    request("Create playbook", "POST", "playbookUrl", "/playbooks", playbook_body, tests=status(201, "Created") + ["if (pm.response.code === 201) { pm.environment.set('playbookId', pm.response.json().id); pm.environment.set('actionId', pm.response.json().actions[0].id); }"]),
    request("List playbooks", "GET", "playbookUrl", "/playbooks", tests=status(200, "Listed")),
    request("Get playbook", "GET", "playbookUrl", "/playbooks/{{playbookId}}", tests=status(200, "Found") + ["pm.test('Steps ordered', () => { const s = pm.response.json().actions.map(a => a.step_order); pm.expect(s).to.eql([...s].sort((a, b) => a - b)); });"]),
    request("Add response action", "POST", "playbookUrl", "/playbooks/{{playbookId}}/actions", {"title": "Notify staff", "description": "Warn affected users", "assigned_to": "{{analystId}}"}, tests=status(201, "Created")),
    request("Start action", "PUT", "playbookUrl", "/actions/{{actionId}}/status", {"status": "In Progress", "note": "Started"}, tests=status(200, "Updated")),
    request("Complete action", "PUT", "playbookUrl", "/actions/{{actionId}}/status", {"status": "Completed", "note": "Done"}, tests=status(200, "Updated")),
    request("Playbook execution history", "GET", "playbookUrl", "/playbooks/{{playbookId}}/history", tests=status(200, "Listed")),
    request("Delete playbook", "DELETE", "playbookUrl", "/playbooks/{{playbookId}}", tests=status(200, "Deleted")),
]
reports = [request(f"{name.title()} report", "GET", "reportUrl", f"/reports/{name}", tests=["pm.test('Report or explicit upstream failure', () => pm.expect(pm.response.code).to.be.oneOf([200, 502, 503]));"]) for name in ("summary", "incidents", "assets", "threats", "vulnerabilities", "activity")]
negative = [
    request("Reject forged audit service key", "POST", "auditUrl", "/logs", log_event, [{"key": "X-Service-Key", "value": "wrong-key"}], status(401, "Rejected")),
    request("Reject user-chosen log actor", "POST", "auditUrl", "/logs", {"action": "manual_review", "actor_label": "someone_else"}, tests=status(422, "Rejected")),
    request("Reject invalid log date filter", "GET", "auditUrl", "/logs/search?start_date=yesterday", tests=status(422, "Rejected")),
    request("Reject logs without token", "GET", "auditUrl", "/logs", [], status(401, "Authentication required")),
    request("Reject playbook with gap in steps", "POST", "playbookUrl", "/playbooks", {**playbook_body, "steps": [{**playbook_body["steps"][0], "step_order": 2}]}, tests=status(422, "Rejected")),
    request("Reject invalid playbook category", "POST", "playbookUrl", "/playbooks", {**playbook_body, "category": "Weather"}, tests=status(422, "Rejected")),
    request("Reject skipping In Progress", "PUT", "playbookUrl", "/actions/{{actionId}}/status", {"status": "Completed"}, tests=["pm.test('Transition rejected', () => pm.expect(pm.response.code).to.be.oneOf([409]));"]),
    request("Reject missing playbook", "GET", "playbookUrl", "/playbooks/999999999", tests=status(404, "Missing resource")),
    request("Reject reports without token", "GET", "reportUrl", "/reports/summary", [], status(401, "Authentication required")),
]
collection = {"info": {"name": "Sprint I — Karl Khouri services", "description": "Security Audit Logging, Security Playbook and Response Automation, and Security Reports by Karl Khouri. Log in first; use an administrator token for most requests and an analyst token to update assigned actions.", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": [{"name": label, "item": items} for label, items in [("Setup — Karl Khouri", setup), ("Security Audit Logging — Karl Khouri", logs), ("Security Playbook and Response Automation — Karl Khouri", playbooks), ("Security Reports — Karl Khouri", reports), ("Negative checks — Karl Khouri", negative)]]}
environment = {"name": "Karl Khouri local template", "values": [{"key": key, "value": value, "enabled": True, "type": "default"} for key, value in [("userUrl", "http://127.0.0.1:8001"), ("auditUrl", "http://127.0.0.1:8007"), ("playbookUrl", "http://127.0.0.1:8008"), ("reportUrl", "http://127.0.0.1:8009"), ("username", ""), ("userPassword", ""), ("token", ""), ("auditServiceKey", ""), ("userId", ""), ("analystId", ""), ("logId", ""), ("playbookId", ""), ("actionId", ""), ("eventId", "example-audit-event-1")]], "_postman_variable_scope": "environment"}
(root / "karl.collection.json").write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
(root / "karl.environment.template.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
