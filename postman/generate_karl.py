"""Generate Karl Khouri's collection (audit logging, playbooks, reports) and a credential-free environment template."""
import json
from pathlib import Path

root = Path(__file__).parent
auth = [{"key": "Authorization", "value": "Bearer {{token}}"}]
service = [{"key": "X-Service-Key", "value": "{{auditServiceKey}}"}]
ok = ["pm.test('Successful response', function () { pm.expect(pm.response.code).to.be.oneOf([200, 201]); });"]


def status(code, label):
    return [f"pm.test('{label}', () => pm.response.to.have.status({code}));"]


def request(name, method, base, path, body=None, headers=None, tests=None, prefix="/api/Karl-Khouri", prerequest=None):
    header = list(auth if headers is None else headers)
    if body is not None:
        header.append({"key": "Content-Type", "value": "application/json"})
    req = {"method": method, "header": header, "url": "{{" + base + "}}" + prefix + path, "description": f"Karl Khouri — {name}. Run against your own backend and inspect the actual response."}
    if body is not None:
        req["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2), "options": {"raw": {"language": "json"}}}
    events = [{"listen": "test", "script": {"type": "text/javascript", "exec": tests or ok}}]
    if prerequest:
        events.insert(0, {"listen": "prerequest", "script": {"type": "text/javascript", "exec": prerequest}})
    return {"name": name, "request": req, "event": events}


users = "/api/Joey-Saade"
analyst_auth = [{"key": "Authorization", "value": "Bearer {{analystToken}}"}]
# Setup creates its own analyst so the collection runs on a fresh database with only the administrator's credentials.
setup = [
    request("Login administrator", "POST", "userUrl", "/users/login", {"username_or_email": "{{username}}", "password": "{{userPassword}}"}, headers=[], tests=status(200, "Authenticated") + ["if (pm.response.code === 200) pm.environment.set('token', pm.response.json().access_token);"], prefix=users),
    request("Get administrator profile", "GET", "userUrl", "/users/{{username}}", tests=status(200, "Found") + ["pm.test('Administrator role', () => pm.expect(pm.response.json().role).to.eql('Security Administrator'));", "if (pm.response.code === 200) pm.environment.set('userId', pm.response.json().id);"], prefix=users),
    request("Register analyst account", "POST", "userUrl", "/users/register", {"full_name": "Karl Khouri Analyst", "username": "{{analystUsername}}", "email": "{{analystUsername}}@example.test", "password": "{{userPassword}}", "department": "SOC", "role": "Regular Employee"}, headers=[], tests=status(201, "Created") + ["if (pm.response.code === 201) pm.environment.set('analystId', pm.response.json().id);"], prefix=users, prerequest=["pm.environment.set('analystUsername', 'karl_analyst_' + Date.now());"]),
    request("Promote to Security Analyst", "PATCH", "userUrl", "/users/{{analystId}}/admin", {"role": "Security Analyst"}, tests=status(200, "Promoted"), prefix=users),
    request("Login analyst", "POST", "userUrl", "/users/login", {"username_or_email": "{{analystUsername}}", "password": "{{userPassword}}"}, headers=[], tests=status(200, "Authenticated") + ["if (pm.response.code === 200) pm.environment.set('analystToken', pm.response.json().access_token);"], prefix=users),
]
log_event = {"event_id": "{{eventId}}", "actor_user_id": None, "actor_label": "unknown_user", "action": "login_failed", "description": "Failed login attempt", "severity": "Warning", "related_service": "users"}
logs = [
    request("Create log as service", "POST", "auditUrl", "/logs", log_event, headers=service, tests=["pm.test('Stored or deduplicated', () => pm.expect(pm.response.code).to.be.oneOf([200, 201]));", "if (pm.response.code < 300) pm.environment.set('logId', pm.response.json().id);"]),
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
transition_rejected = ["pm.test('Transition rejected', () => pm.response.to.have.status(409));"]
playbooks = [
    request("Create playbook", "POST", "playbookUrl", "/playbooks", playbook_body, tests=status(201, "Created") + ["if (pm.response.code === 201) { const p = pm.response.json(); pm.environment.set('playbookId', p.id); pm.environment.set('actionId', p.actions[0].id); pm.environment.set('action2Id', p.actions[1].id); }"]),
    request("List playbooks", "GET", "playbookUrl", "/playbooks", tests=status(200, "Listed")),
    request("Get playbook", "GET", "playbookUrl", "/playbooks/{{playbookId}}", tests=status(200, "Found") + ["pm.test('Steps ordered', () => { const s = pm.response.json().actions.map(a => a.step_order); pm.expect(s).to.eql([...s].sort((a, b) => a - b)); });"]),
    request("Add response action", "POST", "playbookUrl", "/playbooks/{{playbookId}}/actions", {"title": "Notify staff", "description": "Warn affected users", "assigned_to": "{{analystId}}"}, tests=status(201, "Created") + ["pm.test('Appended as next step', () => pm.expect(pm.response.json().step_order).to.eql(3));"]),
    # Invalid transitions run while the actions still exist and are Pending.
    request("Reject skipping In Progress", "PUT", "playbookUrl", "/actions/{{actionId}}/status", {"status": "Completed"}, headers=analyst_auth, tests=transition_rejected),
    request("Reject starting step 2 before step 1", "PUT", "playbookUrl", "/actions/{{action2Id}}/status", {"status": "In Progress"}, headers=analyst_auth, tests=transition_rejected),
    request("Start action as assigned analyst", "PUT", "playbookUrl", "/actions/{{actionId}}/status", {"status": "In Progress", "note": "Started"}, headers=analyst_auth, tests=status(200, "Updated") + ["pm.test('Now In Progress', () => pm.expect(pm.response.json().status).to.eql('In Progress'));"]),
    request("Complete action as assigned analyst", "PUT", "playbookUrl", "/actions/{{actionId}}/status", {"status": "Completed", "note": "Done"}, headers=analyst_auth, tests=status(200, "Updated") + ["pm.test('Now Completed', () => pm.expect(pm.response.json().status).to.eql('Completed'));"]),
    request("Playbook execution history", "GET", "playbookUrl", "/playbooks/{{playbookId}}/history", tests=status(200, "Listed") + ["pm.test('Three creations and two transitions recorded', () => pm.expect(pm.response.json().length).to.eql(5));"]),
    request("Delete playbook", "DELETE", "playbookUrl", "/playbooks/{{playbookId}}", tests=status(200, "Deleted")),
    request("Confirm deleted playbook", "GET", "playbookUrl", "/playbooks/{{playbookId}}", tests=status(404, "Gone")),
]
# The final integrated run needs all nine services: an unavailable upstream must fail here, not pass.
report_ok = status(200, "Report generated")
reports = [
    request("Summary report", "GET", "reportUrl", "/reports/summary", tests=report_ok + ["pm.test('All sources available', () => { const r = pm.response.json(); pm.expect(r.complete).to.eql(true); pm.expect(r.unavailable).to.eql([]); });"]),
    *[request(f"{name.title()} report", "GET", "reportUrl", f"/reports/{name}", tests=report_ok + ["pm.test('Total present', () => pm.expect(pm.response.json().total).to.be.a('number'));"]) for name in ("incidents", "assets", "threats", "vulnerabilities")],
    request("Activity report", "GET", "reportUrl", "/reports/activity", tests=report_ok + ["pm.test('Events counted', () => pm.expect(pm.response.json().total_events).to.be.above(0));"]),
]
negative = [
    request("Reject forged audit service key", "POST", "auditUrl", "/logs", log_event, headers=[{"key": "X-Service-Key", "value": "wrong-key"}], tests=status(401, "Rejected")),
    request("Reject user-chosen log actor", "POST", "auditUrl", "/logs", {"action": "manual_review", "actor_label": "someone_else"}, tests=status(422, "Rejected")),
    request("Reject invalid log date filter", "GET", "auditUrl", "/logs/search?start_date=yesterday", tests=status(422, "Rejected")),
    request("Reject logs without token", "GET", "auditUrl", "/logs", headers=[], tests=status(401, "Authentication required")),
    request("Reject playbook with gap in steps", "POST", "playbookUrl", "/playbooks", {**playbook_body, "steps": [{**playbook_body["steps"][0], "step_order": 2}]}, tests=status(422, "Rejected")),
    request("Reject invalid playbook category", "POST", "playbookUrl", "/playbooks", {**playbook_body, "category": "Weather"}, tests=status(422, "Rejected")),
    request("Reject missing playbook", "GET", "playbookUrl", "/playbooks/999999999", tests=status(404, "Missing resource")),
    request("Reject reports without token", "GET", "reportUrl", "/reports/summary", headers=[], tests=status(401, "Authentication required")),
]
collection = {"info": {"name": "Sprint I — Karl Khouri services", "description": "Security Audit Logging, Security Playbook and Response Automation, and Security Reports by Karl Khouri. Fill username, userPassword (an administrator) and auditServiceKey, start all nine services, then run the folders in order. Setup creates and logs in its own analyst.", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": [{"name": label, "item": items} for label, items in [("Setup — Karl Khouri", setup), ("Security Audit Logging — Karl Khouri", logs), ("Security Playbook and Response Automation — Karl Khouri", playbooks), ("Security Reports — Karl Khouri", reports), ("Negative checks — Karl Khouri", negative)]]}
environment = {"name": "Karl Khouri local template", "values": [{"key": key, "value": value, "enabled": True, "type": "default"} for key, value in [("userUrl", "http://127.0.0.1:8001"), ("auditUrl", "http://127.0.0.1:8007"), ("playbookUrl", "http://127.0.0.1:8008"), ("reportUrl", "http://127.0.0.1:8009"), ("username", ""), ("userPassword", ""), ("token", ""), ("auditServiceKey", ""), ("userId", ""), ("analystUsername", ""), ("analystId", ""), ("analystToken", ""), ("logId", ""), ("playbookId", ""), ("actionId", ""), ("action2Id", ""), ("eventId", "example-audit-event-1")]], "_postman_variable_scope": "environment"}
(root / "karl.collection.json").write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
(root / "karl.environment.template.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
