"""Generate the Joey collection and credential-free environment template."""
import json
from pathlib import Path

root = Path(__file__).parent
auth = [{"key": "Authorization", "value": "Bearer {{token}}"}]
service = [{"key": "X-Service-Key", "value": "{{serviceKey}}"}]


def request(name, method, path, body=None, headers=None, tests=None):
    header = list(auth if headers is None else headers)
    if body is not None:
        header.append({"key": "Content-Type", "value": "application/json"})
    url_key = "userUrl" if path.startswith("/users") else "assetUrl" if path.startswith("/assets") else "notificationUrl"
    req = {"method": method, "header": header, "url": "{{" + url_key + "}}/api/Joey-Saade" + path, "description": f"Joey Saade — {name}. Replace variables and inspect the actual response."}
    if body is not None:
        req["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2), "options": {"raw": {"language": "json"}}}
    script = tests or ["pm.test('Successful response', function () { pm.expect(pm.response.code).to.be.oneOf([200, 201]); });"]
    return {"name": name, "request": req, "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": script}}]}


users = [
    request("Register employee", "POST", "/users/register", {"full_name": "Example Employee", "username": "example_employee", "email": "example@example.test", "password": "{{userPassword}}", "department": "IT", "role": "Regular Employee"}, [], ["pm.test('Created', () => pm.response.to.have.status(201));", "pm.test('No hash in response', () => pm.expect(pm.response.json()).to.not.have.property('password_hash'));", "if (pm.response.code === 201) pm.environment.set('userId', pm.response.json().id);"]),
    request("Login", "POST", "/users/login", {"username_or_email": "{{username}}", "password": "{{userPassword}}"}, [], ["pm.test('Authenticated', () => pm.response.to.have.status(200));", "if (pm.response.code === 200) pm.environment.set('token', pm.response.json().access_token);"]),
    request("Update profile", "PUT", "/users/{{userId}}", {"department": "Security"}),
    request("Delete user", "DELETE", "/users/{{userId}}"),
    request("List users", "GET", "/users"),
    request("Get user by username", "GET", "/users/{{username}}"),
    request("Admin role/status update", "PATCH", "/users/{{userId}}/admin", {"role": "Security Analyst"}),
]
asset_body = {"name": "Server One", "type": "Server", "ip_address": "10.0.0.1", "department": "IT", "owner_id": "{{userId}}", "location": "Lab", "criticality": "High", "status": "Active"}
assets = [
    request("Create asset", "POST", "/assets", asset_body, tests=["pm.test('Created', () => pm.response.to.have.status(201));", "if (pm.response.code === 201) pm.environment.set('assetId', pm.response.json().id);"]),
    request("Update asset", "PUT", "/assets/{{assetId}}", {"status": "Under Maintenance"}),
    request("Delete asset", "DELETE", "/assets/{{assetId}}"),
    request("List assets", "GET", "/assets"),
    request("Get asset", "GET", "/assets/{{assetId}}"),
    request("Search assets", "GET", "/assets/search?name=Server"),
    request("Asset history", "GET", "/assets/{{assetId}}/history"),
]
notification_body = {"user_id": "{{userId}}", "title": "Assigned", "message": "Incident assigned", "type": "Incident Assignment", "severity": "High", "event_id": "{{eventId}}"}
notifications = [
    request("Create notification as service", "POST", "/notifications", notification_body, service, ["pm.test('Created', () => pm.response.to.have.status(201));", "if (pm.response.code === 201) pm.environment.set('notificationId', pm.response.json().id);"]),
    request("List user notifications", "GET", "/notifications/user/{{userId}}"),
    request("Get notification", "GET", "/notifications/{{notificationId}}"),
    request("Mark notification read", "PUT", "/notifications/{{notificationId}}/read"),
    request("Search notifications", "GET", "/notifications/search?status=Unread"),
    request("Delete notification", "DELETE", "/notifications/{{notificationId}}"),
]
negative = [
    request("Reject invalid registration email", "POST", "/users/register", {"full_name": "Bad", "username": "badmail", "email": "invalid", "password": "SecurePassword123", "department": "IT", "role": "Regular Employee"}, [], ["pm.test('Validation rejected', () => pm.response.to.have.status(422));"]),
    request("Reject privileged public registration", "POST", "/users/register", {"full_name": "Bad", "username": "badadmin", "email": "badadmin@example.test", "password": "SecurePassword123", "department": "IT", "role": "Security Administrator"}, [], ["pm.test('Privilege escalation rejected', () => pm.response.to.have.status(403));"]),
    request("Reject unauthenticated users listing", "GET", "/users", headers=[], tests=["pm.test('Authentication required', () => pm.response.to.have.status(401));"]),
    request("Reject invalid asset IP", "POST", "/assets", {**asset_body, "ip_address": "not-an-ip"}, tests=["pm.test('Validation rejected', () => pm.response.to.have.status(422));"]),
    request("Reject missing asset", "GET", "/assets/999999999", tests=["pm.test('Missing resource', () => pm.response.to.have.status(404));"]),
    request("Reject notification without auth", "POST", "/notifications", notification_body, [], ["pm.test('Authentication required', () => pm.response.to.have.status(401));"]),
]
collection = {"info": {"name": "Sprint I — Joey Saade services", "description": "Real requests for Joey's three services. Run against your own backend and capture actual results.", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": [{"name": label, "item": items} for label, items in [("Users and Identity — Joey Saade", users), ("Asset Management — Joey Saade", assets), ("Notification and Alert Management — Joey Saade", notifications), ("Negative checks — Joey Saade", negative)]]}
environment = {"name": "Joey local template", "values": [{"key": key, "value": value, "enabled": True, "type": "default"} for key, value in [("userUrl", "http://127.0.0.1:8001"), ("assetUrl", "http://127.0.0.1:8002"), ("notificationUrl", "http://127.0.0.1:8003"), ("username", ""), ("userPassword", ""), ("token", ""), ("serviceKey", ""), ("userId", ""), ("assetId", ""), ("notificationId", ""), ("eventId", "example-event-1")]], "_postman_variable_scope": "environment"}
(root / "joey.collection.json").write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
(root / "joey.environment.template.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
