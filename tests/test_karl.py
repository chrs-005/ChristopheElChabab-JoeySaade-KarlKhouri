"""Karl Khouri: Security Audit Logging, Playbooks and Reports."""
import os
import sqlite3

import httpx
import pytest
from fastapi.testclient import TestClient

from joey import assets, users
from joey.common import PREFIX as USER_PREFIX, db
from joey.outbox import deliver_pending as real_deliver_pending
from karl import audit_logs, playbooks, reports
from karl.common import PREFIX

AUDIT_KEY = "test-audit-secret-with-at-least-32-characters"


@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("AUTH_SECRET", "test-auth-secret-with-at-least-32-characters")
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "test-service-secret-with-at-least-32-characters")
    monkeypatch.setenv("AUDIT_SERVICE_AUTH_SECRET", AUDIT_KEY)
    monkeypatch.setattr("joey.outbox.deliver_pending", lambda: None)
    with TestClient(users.app) as u, TestClient(assets.app) as a, TestClient(audit_logs.app) as l, TestClient(playbooks.app) as p, TestClient(reports.app) as r:
        yield {"users": u, "assets": a, "logs": l, "playbooks": p, "reports": r}


def register(c, username):
    response = c["users"].post(f"{USER_PREFIX}/users/register", json={"full_name": username.title(), "username": username, "email": f"{username}@example.com", "password": "SecurePassword123", "department": "IT", "role": "Regular Employee"})
    assert response.status_code == 201, response.text
    return response.json()


def login(c, username):
    response = c["users"].post(f"{USER_PREFIX}/users/login", json={"username_or_email": username, "password": "SecurePassword123"})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def make(c, username, role="Regular Employee"):
    user = register(c, username)
    with db() as conn:
        conn.execute("UPDATE users SET role=? WHERE id=?", (role, user["id"]))
    return user, login(c, username)


def log_count(action=None):
    with db() as conn:
        if action:
            return conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action=?", (action,)).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]


def test_outbox_events_reach_audit_service_with_attribution(clients, monkeypatch):
    c = clients
    admin, admin_h = make(c, "admin", "Security Administrator")
    c["users"].post(f"{USER_PREFIX}/users/login", json={"username_or_email": "ghost", "password": "wrong-password1"})
    monkeypatch.setenv("AUDIT_SERVICE_URL", "http://audit.test")
    monkeypatch.setattr("joey.outbox.httpx.post", lambda url, json, headers, timeout: c["logs"].post(url.replace("http://audit.test", ""), json=json, headers=headers) if "audit.test" in url else httpx.Response(503, request=httpx.Request("POST", url)))
    real_deliver_pending()
    with db() as conn:
        pending = conn.execute("SELECT COUNT(*) FROM outbox WHERE destination='audit' AND delivered_at IS NULL").fetchone()[0]
    assert pending == 0
    failed = c["logs"].get(f"{PREFIX}/logs/search?action=login_failed", headers=admin_h).json()
    assert len(failed) == 1 and failed[0]["actor_user_id"] is None and failed[0]["actor_label"] == "ghost"
    assert failed[0]["source"] == "service"
    mine = c["logs"].get(f"{PREFIX}/logs/user/{admin['id']}", headers=admin_h).json()
    assert {"user_created", "login_success"} <= {x["action"] for x in mine}
    before = log_count()
    real_deliver_pending()  # Already delivered events are not sent twice.
    assert log_count() == before


def test_log_creation_rules_and_deduplication(clients):
    c = clients
    _, admin_h = make(c, "admin", "Security Administrator")
    _, analyst_h = make(c, "analyst", "Security Analyst")
    service = {"X-Service-Key": AUDIT_KEY}
    event = {"event_id": "evt-1", "actor_user_id": None, "actor_label": "someone", "action": "login_failed", "description": "Bad password", "severity": "Warning", "related_service": "users"}
    first = c["logs"].post(f"{PREFIX}/logs", json=event, headers=service)
    assert first.status_code == 201, first.text
    again = c["logs"].post(f"{PREFIX}/logs", json=event, headers=service)
    assert again.status_code == 200 and again.json()["id"] == first.json()["id"]
    assert c["logs"].post(f"{PREFIX}/logs", json=event, headers={"X-Service-Key": os.environ["SERVICE_AUTH_SECRET"]}).status_code == 401
    assert c["logs"].post(f"{PREFIX}/logs", json={**event, "event_id": None}, headers=service).status_code == 422
    assert c["logs"].post(f"{PREFIX}/logs", json={**event, "event_id": "evt-2", "severity": "Loud"}, headers=service).status_code == 422
    assert c["logs"].post(f"{PREFIX}/logs", json={**event, "event_id": "evt-3", "occurred_at": "2999-01-01T00:00:00Z"}, headers=service).status_code == 422
    assert c["logs"].post(f"{PREFIX}/logs", json={"action": "Bad Action"}, headers=admin_h).status_code == 422
    # Users cannot choose who an entry is attributed to.
    assert c["logs"].post(f"{PREFIX}/logs", json={"action": "manual_note", "actor_label": "someone_else"}, headers=admin_h).status_code == 422
    manual = c["logs"].post(f"{PREFIX}/logs", json={"action": "manual_note", "description": "Reviewed firewall"}, headers=admin_h)
    assert manual.status_code == 201 and manual.json()["actor_label"] == "admin" and manual.json()["source"] == "user"
    assert c["logs"].post(f"{PREFIX}/logs", json={"action": "manual_note"}, headers=analyst_h).status_code == 403
    assert c["logs"].post(f"{PREFIX}/logs", json={"action": "manual_note"}).status_code == 401


def test_log_reading_permissions_search_and_deletion(clients):
    c = clients
    admin, admin_h = make(c, "admin", "Security Administrator")
    _, auditor_h = make(c, "auditor", "Security Auditor")
    employee, employee_h = make(c, "employee")
    service = {"X-Service-Key": AUDIT_KEY}
    for i, (action, sev) in enumerate([("asset_created", "Information"), ("login_failed", "Warning"), ("login_success", "Information")]):
        r = c["logs"].post(f"{PREFIX}/logs", json={"event_id": f"e{i}", "actor_user_id": employee["id"], "actor_label": "employee", "action": action, "severity": sev, "related_service": "assets" if i == 0 else "users", "occurred_at": f"2026-10-0{i + 1}T12:00:00Z"}, headers=service)
        assert r.status_code == 201, r.text
    assert len(c["logs"].get(f"{PREFIX}/logs", headers=auditor_h).json()) == 3
    assert c["logs"].get(f"{PREFIX}/logs", headers=employee_h).status_code == 403
    assert log_count("unauthorized_access") == 1  # Written directly, not looped back over HTTP.
    assert [x["action"] for x in c["logs"].get(f"{PREFIX}/logs/search?severity=Warning&related_service=users", headers=admin_h).json()] == ["login_failed"]
    assert len(c["logs"].get(f"{PREFIX}/logs/search?related_service=users&start_date=2026-10-03", headers=admin_h).json()) == 1
    assert len(c["logs"].get(f"{PREFIX}/logs/search?start_date=2026-10-01&end_date=2026-10-02", headers=admin_h).json()) == 2
    assert c["logs"].get(f"{PREFIX}/logs/search?start_date=2026-10-05&end_date=2026-10-01", headers=admin_h).status_code == 422
    assert c["logs"].get(f"{PREFIX}/logs/search?start_date=yesterday", headers=admin_h).status_code == 422
    assert c["logs"].get(f"{PREFIX}/logs/search?severity=Loud", headers=admin_h).status_code == 422
    assert len(c["logs"].get(f"{PREFIX}/logs/user/{employee['id']}", headers=employee_h).json()) == 4  # includes the denial
    assert c["logs"].get(f"{PREFIX}/logs/user/{admin['id']}", headers=employee_h).status_code == 403
    assert c["logs"].get(f"{PREFIX}/logs/user/999999", headers=admin_h).status_code == 404
    target = c["logs"].get(f"{PREFIX}/logs/search?action=asset_created", headers=admin_h).json()[0]["id"]
    assert c["logs"].get(f"{PREFIX}/logs/{target}", headers=auditor_h).status_code == 200
    assert c["logs"].get(f"{PREFIX}/logs/999999", headers=auditor_h).status_code == 404
    assert c["logs"].delete(f"{PREFIX}/logs/{target}", headers=auditor_h).status_code == 403
    assert c["logs"].delete(f"{PREFIX}/logs/{target}", headers=admin_h).status_code == 200
    assert c["logs"].get(f"{PREFIX}/logs/{target}", headers=admin_h).status_code == 404
    deletion = c["logs"].get(f"{PREFIX}/logs/search?action=audit_log_deleted", headers=admin_h).json()
    assert len(deletion) == 1 and deletion[0]["subject_id"] == str(target)
    assert c["logs"].delete(f"{PREFIX}/logs/{deletion[0]['id']}", headers=admin_h).status_code == 409


def test_logs_are_immutable_and_survive_user_deletion(clients):
    c = clients
    _, admin_h = make(c, "admin", "Security Administrator")
    employee = register(c, "employee")
    c["logs"].post(f"{PREFIX}/logs", json={"event_id": "keep", "actor_user_id": employee["id"], "action": "login_success", "related_service": "users"}, headers={"X-Service-Key": AUDIT_KEY})
    with db() as conn:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE audit_logs SET action='tampered' WHERE event_id='keep'")
    assert c["users"].delete(f"{USER_PREFIX}/users/{employee['id']}", headers=admin_h).status_code == 200
    kept = c["logs"].get(f"{PREFIX}/logs/user/{employee['id']}", headers=admin_h).json()
    assert len(kept) == 1 and kept[0]["actor_user_id"] is None and kept[0]["original_actor_user_id"] == employee["id"] and kept[0]["actor_label"] == "employee"


def test_playbook_ordering_transitions_and_history(clients):
    c = clients
    _, admin_h = make(c, "admin", "Security Administrator")
    analyst, analyst_h = make(c, "analyst", "Security Analyst")
    other, other_h = make(c, "other", "Security Analyst")
    employee, employee_h = make(c, "employee")
    _, auditor_h = make(c, "auditor", "Security Auditor")
    body = {"name": "Phishing response", "description": "Contain a phishing campaign", "category": "Phishing", "severity": "High", "steps": [
        {"title": "Block sender", "description": "Block sender domain", "assigned_to": analyst["id"]},
        {"title": "Purge mail", "description": "Remove messages", "assigned_to": analyst["id"]}]}
    assert c["playbooks"].post(f"{PREFIX}/playbooks", json=body, headers=employee_h).status_code == 403
    assert c["playbooks"].post(f"{PREFIX}/playbooks", json={**body, "category": "Weather"}, headers=admin_h).status_code == 422
    assert c["playbooks"].post(f"{PREFIX}/playbooks", json={**body, "severity": "Huge"}, headers=admin_h).status_code == 422
    assert c["playbooks"].post(f"{PREFIX}/playbooks", json={**body, "steps": [{**body["steps"][0], "step_order": 2}]}, headers=admin_h).status_code == 422
    assert c["playbooks"].post(f"{PREFIX}/playbooks", json={**body, "steps": [{**body["steps"][0], "assigned_to": employee["id"]}]}, headers=admin_h).status_code == 422
    assert c["playbooks"].post(f"{PREFIX}/playbooks", json={**body, "steps": [{**body["steps"][0], "assigned_to": 999999}]}, headers=admin_h).status_code == 422
    assert c["playbooks"].get(f"{PREFIX}/playbooks", headers=admin_h).json() == []  # Rejected creations left nothing behind.
    created = c["playbooks"].post(f"{PREFIX}/playbooks", json=body, headers=analyst_h)
    assert created.status_code == 201, created.text
    playbook = created.json()
    assert playbook["created_by"] == analyst["id"] and playbook["total_steps"] == 2 and playbook["execution_status"] == "Not Started"
    assert c["playbooks"].post(f"{PREFIX}/playbooks", json={**body, "name": "phishing RESPONSE"}, headers=admin_h).status_code == 409
    pid = playbook["id"]
    first, second = (a["id"] for a in playbook["actions"])
    step = {"title": "Notify users", "description": "Warn staff", "assigned_to": other["id"]}
    assert c["playbooks"].post(f"{PREFIX}/playbooks/{pid}/actions", json={**step, "step_order": 2}, headers=admin_h).status_code == 409
    assert c["playbooks"].post(f"{PREFIX}/playbooks/{pid}/actions", json={**step, "step_order": 5}, headers=admin_h).status_code == 422
    assert c["playbooks"].post(f"{PREFIX}/playbooks/999999/actions", json=step, headers=admin_h).status_code == 404
    third = c["playbooks"].post(f"{PREFIX}/playbooks/{pid}/actions", json=step, headers=admin_h)
    assert third.status_code == 201 and third.json()["step_order"] == 3
    status = lambda action, value, headers: c["playbooks"].put(f"{PREFIX}/actions/{action}/status", json={"status": value}, headers=headers)
    assert status(second, "In Progress", analyst_h).status_code == 409  # Step 1 is not completed yet.
    assert status(first, "Completed", analyst_h).status_code == 409  # Cannot skip In Progress.
    assert status(first, "In Progress", other_h).status_code == 403  # Not the assignee.
    assert status(first, "In Progress", auditor_h).status_code == 403
    assert status(first, "Done", analyst_h).status_code == 422
    assert status(999999, "In Progress", admin_h).status_code == 404
    assert status(first, "In Progress", analyst_h).json()["started_at"] is not None
    assert c["playbooks"].delete(f"{PREFIX}/playbooks/{pid}", headers=admin_h).status_code == 409  # Action in progress.
    assert status(first, "Completed", analyst_h).json()["completed_by"] == analyst["id"]
    assert status(first, "In Progress", analyst_h).status_code == 409  # No going back.
    assert status(second, "In Progress", admin_h).status_code == 200
    assert status(second, "Completed", admin_h).status_code == 200
    assert c["playbooks"].get(f"{PREFIX}/playbooks/{pid}", headers=auditor_h).json()["execution_status"] == "In Progress"
    status(third.json()["id"], "In Progress", other_h); status(third.json()["id"], "Completed", other_h)
    detail = c["playbooks"].get(f"{PREFIX}/playbooks/{pid}", headers=auditor_h).json()
    assert detail["execution_status"] == "Completed" and detail["completed_steps"] == 3
    assert c["playbooks"].get(f"{PREFIX}/playbooks/{pid}", headers=employee_h).status_code == 403
    assert len(c["playbooks"].get(f"{PREFIX}/playbooks?category=Phishing", headers=auditor_h).json()) == 1
    assert c["playbooks"].get(f"{PREFIX}/playbooks?category=Malware", headers=auditor_h).json() == []
    assert c["playbooks"].get(f"{PREFIX}/playbooks/999999", headers=admin_h).status_code == 404
    assert c["playbooks"].delete(f"{PREFIX}/playbooks/{pid}", headers=analyst_h).status_code == 403
    assert c["playbooks"].delete(f"{PREFIX}/playbooks/{pid}", headers=admin_h).status_code == 200
    assert c["playbooks"].get(f"{PREFIX}/playbooks/{pid}", headers=admin_h).status_code == 404
    history = c["playbooks"].get(f"{PREFIX}/playbooks/{pid}/history", headers=admin_h).json()
    assert len(history) == 9 and all(h["action_id"] is None for h in history)  # 3 created + 6 transitions, kept after deletion
    with db() as conn:
        assigned = conn.execute("SELECT COUNT(*) FROM outbox WHERE destination='notification' AND event_id LIKE 'playbook-action-%'").fetchone()[0]
        audited = conn.execute("SELECT COUNT(*) FROM outbox WHERE destination='audit' AND payload_json LIKE '%response_action_status_changed%'").fetchone()[0]
    assert assigned == 3 and audited == 6


def route_reports(c, monkeypatch, down=()):
    def fake_get(url, headers):
        if any(name in url for name in down):
            raise httpx.ConnectError("refused")
        for base, client in (("http://127.0.0.1:8002", c["assets"]), ("http://127.0.0.1:8007", c["logs"])):
            if url.startswith(base):
                return client.get(url[len(base):], headers=headers)
        raise httpx.ConnectError("not running")
    monkeypatch.setattr(reports, "http_get", fake_get)


def test_reports_reconcile_with_stored_data_and_fail_honestly(clients, monkeypatch):
    c = clients
    admin, admin_h = make(c, "admin", "Security Administrator")
    _, auditor_h = make(c, "auditor", "Security Auditor")
    _, analyst_h = make(c, "analyst", "Security Analyst")
    route_reports(c, monkeypatch)
    for name, crit, status in (("Web", "High", "Active"), ("DB", "Critical", "Active"), ("Laptop", "Low", "Inactive")):
        r = c["assets"].post(f"{USER_PREFIX}/assets", json={"name": name, "type": "Server", "ip_address": "10.0.0.1", "department": "IT", "owner_id": admin["id"], "location": "Lab", "criticality": crit, "status": status}, headers=admin_h)
        assert r.status_code == 201
    c["logs"].post(f"{PREFIX}/logs", json={"event_id": "f1", "actor_label": "ghost", "action": "login_failed", "severity": "Warning", "related_service": "users"}, headers={"X-Service-Key": AUDIT_KEY})
    assert c["reports"].get(f"{PREFIX}/reports/assets", headers=analyst_h).status_code == 403
    assert c["reports"].get(f"{PREFIX}/reports/assets").status_code == 401
    asset_report = c["reports"].get(f"{PREFIX}/reports/assets", headers=auditor_h).json()
    stored = c["assets"].get(f"{USER_PREFIX}/assets", headers=admin_h).json()
    assert asset_report["total"] == len(stored) == 3
    assert asset_report["by_criticality"] == {"Critical": 1, "High": 1, "Low": 1}
    assert asset_report["by_status"] == {"Active": 2, "Inactive": 1} and asset_report["active_high_or_critical"] == 2
    future = c["reports"].get(f"{PREFIX}/reports/assets?start_date=2999-01-01", headers=admin_h).json()
    assert future["total"] == 0
    assert c["reports"].get(f"{PREFIX}/reports/assets?start_date=2026-12-01&end_date=2026-01-01", headers=admin_h).status_code == 422
    activity = c["reports"].get(f"{PREFIX}/reports/activity", headers=admin_h).json()
    assert activity["total_events"] == len(c["logs"].get(f"{PREFIX}/logs", headers=admin_h).json())
    assert activity["failed_logins"] == 1
    with db() as conn:  # The analyst's denied report request is queued for the audit service.
        assert conn.execute("SELECT COUNT(*) FROM outbox WHERE destination='audit' AND payload_json LIKE '%unauthorized_access%Security Reports%'").fetchone()[0] == 1
    # Threat/vulnerability/incident services are not running: explicit failure, never zero.
    missing = c["reports"].get(f"{PREFIX}/reports/incidents", headers=admin_h)
    assert missing.status_code == 503 and "incidents" in missing.json()["message"]
    assert c["reports"].get(f"{PREFIX}/reports/threats", headers=admin_h).status_code == 503
    assert c["reports"].get(f"{PREFIX}/reports/vulnerabilities", headers=admin_h).status_code == 503
    summary = c["reports"].get(f"{PREFIX}/reports/summary", headers=auditor_h).json()
    assert summary["complete"] is False and summary["incidents"] is None and summary["assets"]["total"] == 3
    assert {x["source"] for x in summary["unavailable"]} == {"incidents", "threats", "vulnerabilities"}
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM outbox WHERE payload_json LIKE '%report_generated%'").fetchone()[0] >= 4


def test_reports_use_upstream_records_for_peer_services(clients, monkeypatch):
    c = clients
    _, admin_h = make(c, "admin", "Security Administrator")
    incidents = [{"id": 1, "status": "Open", "severity": "High", "assigned_to": None, "created_at": "2026-10-01T10:00:00+00:00"},
                 {"id": 2, "status": "Closed", "severity": "Low", "assigned_to": 4, "created_at": "2026-10-10T10:00:00+00:00"}]
    vulnerabilities = {"items": [{"id": 1, "severity": "Critical", "status": "Open", "cvss_score": 9.8, "created_at": "2026-10-02T00:00:00Z"}, {"id": 2, "severity": "Medium", "status": "Resolved", "cvss_score": 5.0, "created_at": "2026-10-03T00:00:00Z"}]}

    def fake_get(url, headers):
        request = httpx.Request("GET", url)
        if "incidents" in url:
            return httpx.Response(200, json=incidents, request=request)
        if "vulnerabilities" in url:
            return httpx.Response(200, json=vulnerabilities, request=request)
        if "threats" in url:
            return httpx.Response(500, request=request)
        return httpx.Response(200, text="not json", request=request)
    monkeypatch.setattr(reports, "http_get", fake_get)
    report = c["reports"].get(f"{PREFIX}/reports/incidents", headers=admin_h).json()
    assert report["total"] == 2 and report["open"] == 1 and report["unassigned"] == 1 and report["by_severity"] == {"High": 1, "Low": 1}
    assert c["reports"].get(f"{PREFIX}/reports/incidents?end_date=2026-10-05", headers=admin_h).json()["total"] == 1
    vulns = c["reports"].get(f"{PREFIX}/reports/vulnerabilities", headers=admin_h).json()
    assert vulns["average_cvss"] == 7.4 and vulns["open"] == 1
    assert c["reports"].get(f"{PREFIX}/reports/threats", headers=admin_h).status_code == 502
    assert c["reports"].get(f"{PREFIX}/reports/assets", headers=admin_h).status_code == 502
