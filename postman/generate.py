"""Generate Joey Saade's ordered Postman collection and credential-free environment."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
AUTH = [{"key": "Authorization", "value": "Bearer {{token}}"}]
SERVICE = [{"key": "X-Service-Key", "value": "{{serviceKey}}"}]


def request(name, method, path, body=None, headers=None, tests=None, prerequest=None):
    header = list(AUTH if headers is None else headers)
    if body is not None:
        header.append({"key": "Content-Type", "value": "application/json"})
    base_url = "http://127.0.0.1:8001" if path.startswith("/users") else "http://127.0.0.1:8002" if path.startswith("/assets") else "http://127.0.0.1:8003"
    req = {"method": method, "header": header, "url": base_url + "/api/Joey-Saade" + path,
           "description": f"Joey Saade — {name}. Run folders in order and inspect the actual response."}
    if body is not None:
        req["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2), "options": {"raw": {"language": "json"}}}
    events = []
    if prerequest:
        events.append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": prerequest}})
    events.append({"listen": "test", "script": {"type": "text/javascript", "exec": tests or ["pm.test('Successful response', () => pm.expect(pm.response.code).to.be.oneOf([200, 201]));"]}})
    return {"name": name, "request": req, "event": events}


users = [
    request("Register employee", "POST", "/users/register",
            {"full_name": "Example Employee", "username": "{{employeeUsername}}", "email": "{{employeeEmail}}", "password": "{{userPassword}}", "department": "IT", "role": "Regular Employee"},
            headers=[], tests=["pm.test('Created', () => pm.response.to.have.status(201));", "pm.test('No hash in response', () => pm.expect(pm.response.json()).to.not.have.property('password_hash'));", "if (pm.response.code === 201) pm.environment.set('userId', pm.response.json().id);"],
            prerequest=["const suffix = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);", "pm.environment.set('employeeUsername', 'joey_employee_' + suffix);", "pm.environment.set('employeeEmail', 'joey_employee_' + suffix + '@example.test');", "pm.environment.set('eventId', 'joey-event-' + suffix);"]),
    request("Login", "POST", "/users/login", {"username_or_email": "{{username}}", "password": "{{userPassword}}"}, headers=[], tests=["pm.test('Authenticated', () => pm.response.to.have.status(200));", "if (pm.response.code === 200) pm.environment.set('token', pm.response.json().access_token);"]),
    request("Update profile", "PUT", "/users/{{userId}}", {"department": "Security"}),
    request("List users", "GET", "/users"),
    request("Get user by username", "GET", "/users/{{employeeUsername}}"),
    request("Admin role/status update", "PATCH", "/users/{{userId}}/admin", {"role": "Security Analyst"}),
]

asset_body = {"name": "Server One", "type": "Server", "ip_address": "10.0.0.1", "department": "IT", "owner_id": "{{userId}}", "location": "Lab", "criticality": "High", "status": "Active"}
assets = [
    request("Create asset", "POST", "/assets", asset_body, tests=["pm.test('Created', () => pm.response.to.have.status(201));", "if (pm.response.code === 201) pm.environment.set('assetId', pm.response.json().id);"]),
    request("Update asset", "PUT", "/assets/{{assetId}}", {"status": "Under Maintenance"}),
    request("List assets", "GET", "/assets"),
    request("Get asset", "GET", "/assets/{{assetId}}"),
    request("Search assets", "GET", "/assets/search?name=Server"),
    request("Asset history", "GET", "/assets/{{assetId}}/history"),
]

notification_body = {"user_id": "{{userId}}", "title": "Assigned", "message": "Incident assigned", "type": "Incident Assignment", "severity": "High", "event_id": "{{eventId}}"}
notifications = [
    request("Create notification as service", "POST", "/notifications", notification_body, headers=SERVICE, tests=["pm.test('Created', () => pm.response.to.have.status(201));", "if (pm.response.code === 201) pm.environment.set('notificationId', pm.response.json().id);"]),
    request("List user notifications", "GET", "/notifications/user/{{userId}}", tests=["pm.test('Listed', () => pm.response.to.have.status(200));", "if (pm.response.code === 200) {", "  const welcome = pm.response.json().filter(n => n.title === 'Welcome');", "  pm.test('One welcome notification for this user', () => pm.expect(welcome).to.have.lengthOf(1));", "  if (welcome.length === 1) pm.environment.set('welcomeNotificationId', welcome[0].id);", "}"]),
    request("Get notification", "GET", "/notifications/{{notificationId}}"),
    request("Mark notification read", "PUT", "/notifications/{{notificationId}}/read"),
    request("Search notifications", "GET", "/notifications/search?status=Unread"),
]

negative = [
    request("Reject invalid registration email", "POST", "/users/register", {"full_name": "Bad", "username": "badmail", "email": "invalid", "password": "SecurePassword123", "department": "IT", "role": "Regular Employee"}, headers=[], tests=["pm.test('Validation rejected', () => pm.response.to.have.status(422));"]),
    request("Reject privileged public registration", "POST", "/users/register", {"full_name": "Bad", "username": "badadmin", "email": "badadmin@example.test", "password": "SecurePassword123", "department": "IT", "role": "Security Administrator"}, headers=[], tests=["pm.test('Privilege escalation rejected', () => pm.response.to.have.status(403));"]),
    request("Reject unauthenticated users listing", "GET", "/users", headers=[], tests=["pm.test('Authentication required', () => pm.response.to.have.status(401));"]),
    request("Reject invalid asset IP", "POST", "/assets", {**asset_body, "ip_address": "not-an-ip"}, tests=["pm.test('Validation rejected', () => pm.response.to.have.status(422));"]),
    request("Reject missing asset", "GET", "/assets/999999999", tests=["pm.test('Missing resource', () => pm.response.to.have.status(404));"]),
    request("Reject notification without auth", "POST", "/notifications", notification_body, headers=[], tests=["pm.test('Authentication required', () => pm.response.to.have.status(401));"]),
]

cleanup = [
    request("Delete asset", "DELETE", "/assets/{{assetId}}"),
    request("Delete created notification", "DELETE", "/notifications/{{notificationId}}"),
    request("Delete welcome notification", "DELETE", "/notifications/{{welcomeNotificationId}}"),
    request("Delete user", "DELETE", "/users/{{userId}}"),
]

folders = [("Users and Identity", users), ("Asset Management", assets), ("Notification and Alert Management", notifications), ("Negative checks", negative), ("Cleanup", cleanup)]
collection = {"info": {"name": "Sprint I — Joey Saade services", "description": "Run ordered folders against the backend, with Cleanup last. Capture actual results and database evidence.", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": [{"name": f"{label} — Joey Saade", "item": items} for label, items in folders]}
variables = [("username", ""), ("userPassword", ""), ("token", ""), ("serviceKey", ""), ("userId", ""), ("employeeUsername", ""), ("employeeEmail", ""), ("assetId", ""), ("notificationId", ""), ("welcomeNotificationId", ""), ("eventId", "")]
environment = {"name": "Joey local template", "values": [{"key": key, "value": value, "enabled": True, "type": "default"} for key, value in variables], "_postman_variable_scope": "environment"}

(ROOT / "joey.collection.json").write_text(json.dumps(collection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(ROOT / "joey.environment.template.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
