import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from joey import assets, notifications, users
from joey.common import PREFIX, db, init_db
from joey.outbox import deliver_pending as real_deliver_pending


@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("AUTH_SECRET", "test-auth-secret-with-at-least-32-characters")
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "test-service-secret-with-at-least-32-characters")
    monkeypatch.setattr("joey.outbox.deliver_pending", lambda: None)
    with TestClient(users.app) as u, TestClient(assets.app) as a, TestClient(notifications.app) as n:
        yield u, a, n


def register(client, username="employee", role="Regular Employee"):
    return client.post(f"{PREFIX}/users/register", json={"full_name": username.title(), "username": username, "email": f"{username}@example.com", "password": "SecurePassword123", "department": "IT", "role": role})


def login(client, username):
    result = client.post(f"{PREFIX}/users/login", json={"username_or_email": username, "password": "SecurePassword123"})
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def promote(user_id, role):
    with db() as conn:
        conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))


def test_registration_login_and_permissions(clients):
    u, a, n = clients
    user = register(u)
    assert user.status_code == 201
    assert "password_hash" not in user.json()
    assert register(u).status_code == 409
    assert register(u, "intruder", "Security Administrator").status_code == 403
    assert u.post(f"{PREFIX}/users/login", json={"username_or_email": "employee", "password": "wrong"}).status_code == 401
    headers = login(u, "employee")
    assert u.get(f"{PREFIX}/users", headers=headers).status_code == 403
    assert u.get(f"{PREFIX}/users/employee", headers=headers).status_code == 200
    other = register(u, "other").json()
    assert u.get(f"{PREFIX}/users/other", headers=headers).status_code == 403
    assert u.put(f"{PREFIX}/users/{other['id']}", headers=headers, json={"department": "HR"}).status_code == 403
    assert u.put(f"{PREFIX}/users/{user.json()['id']}", headers=headers, json={"role": "Security Administrator"}).status_code == 422
    promote(user.json()["id"], "Security Administrator")
    admin = login(u, "employee")
    assert len(u.get(f"{PREFIX}/users", headers=admin).json()) == 2
    assert u.patch(f"{PREFIX}/users/{other['id']}/admin", headers=admin, json={"status": "Suspended"}).status_code == 200
    assert u.post(f"{PREFIX}/users/login", json={"username_or_email": "other", "password": "SecurePassword123"}).status_code == 403
    assert u.delete(f"{PREFIX}/users/{other['id']}", headers=admin).status_code == 200


def test_register_delete_register_keeps_user_and_welcome_event_ids_unique(clients):
    u, _, _ = clients
    admin_user = register(u, "admin").json()
    promote(admin_user["id"], "Security Administrator")
    admin = login(u, "admin")
    first = register(u, "first")
    assert first.status_code == 201
    first_id = first.json()["id"]
    first_token = login(u, "first")
    assert u.delete(f"{PREFIX}/users/{first_id}", headers=admin).status_code == 200

    second = register(u, "second")
    assert second.status_code == 201, second.text
    second_id = second.json()["id"]
    assert second_id > first_id
    assert u.get(f"{PREFIX}/users/second", headers=first_token).status_code == 401
    with db() as conn:
        events = {row["event_id"] for row in conn.execute("SELECT event_id FROM outbox WHERE destination='notification'")}
        assert f"welcome-user-{first_id}" in events
        assert f"welcome-user-{second_id}" in events
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_existing_database_seeds_deleted_user_ids_from_welcome_events(clients):
    u, _, _ = clients
    admin_user = register(u, "admin").json()
    promote(admin_user["id"], "Security Administrator")
    admin = login(u, "admin")
    deleted_id = register(u, "legacy").json()["id"]
    assert u.delete(f"{PREFIX}/users/{deleted_id}", headers=admin).status_code == 200
    with db() as conn:
        conn.execute("DROP TABLE user_id_allocations")
    init_db()

    replacement = register(u, "replacement")
    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["id"] > deleted_id


def test_assets_history_and_notification_scope(clients):
    u, a, n = clients
    admin_user = register(u, "admin").json()
    employee = register(u, "employee").json()
    promote(admin_user["id"], "Security Administrator")
    admin = login(u, "admin")
    emp = login(u, "employee")
    data = {"name": "Server One", "type": "Server", "ip_address": "10.0.0.1", "department": "IT", "owner_id": employee["id"], "location": "Lab", "criticality": "High"}
    assert a.post(f"{PREFIX}/assets", json=data, headers=emp).status_code == 403
    assert a.post(f"{PREFIX}/assets", json={**data, "ip_address": "bad"}, headers=admin).status_code == 422
    created = a.post(f"{PREFIX}/assets", json=data, headers=admin)
    assert created.status_code == 201, created.text
    asset_id = created.json()["id"]
    assert len(a.get(f"{PREFIX}/assets/search?name=Server", headers=admin).json()) == 1
    assert a.put(f"{PREFIX}/assets/{asset_id}", json={"status": "Under Maintenance"}, headers=admin).status_code == 200
    assert len(a.get(f"{PREFIX}/assets/{asset_id}/history", headers=admin).json()) == 2
    assert a.get(f"{PREFIX}/assets/{asset_id}", headers=emp).status_code == 403
    assert a.delete(f"{PREFIX}/assets/{asset_id}", headers=admin).status_code == 200
    assert len(a.get(f"{PREFIX}/assets/{asset_id}/history", headers=admin).json()) == 3

    payload = {"user_id": employee["id"], "title": "Assigned", "message": "Incident assigned", "type": "Incident Assignment", "severity": "High", "event_id": "incident-1"}
    assert n.post(f"{PREFIX}/notifications", json=payload, headers=emp).status_code == 403
    service = {"X-Service-Key": os.environ["SERVICE_AUTH_SECRET"]}
    item = n.post(f"{PREFIX}/notifications", json=payload, headers=service)
    assert item.status_code == 201, item.text
    assert n.post(f"{PREFIX}/notifications", json=payload, headers=service).json()["id"] == item.json()["id"]
    item_id = item.json()["id"]
    assert n.get(f"{PREFIX}/notifications/{item_id}", headers=admin).status_code == 200
    assert n.get(f"{PREFIX}/notifications/user/{employee['id']}", headers=emp).status_code == 200
    assert n.put(f"{PREFIX}/notifications/{item_id}/read", headers=emp).json()["status"] == "Read"
    assert n.delete(f"{PREFIX}/notifications/{item_id}", headers=emp).status_code == 403
    assert n.delete(f"{PREFIX}/notifications/{item_id}", headers=admin).status_code == 200


def test_database_constraints_and_token_recheck(clients):
    u, a, n = clients
    user = register(u).json()
    token = login(u, "employee")
    with db() as conn:
        conn.execute("UPDATE users SET status='Inactive' WHERE id=?", (user["id"],))
    assert u.get(f"{PREFIX}/users/employee", headers=token).status_code == 401
    assert u.get(f"{PREFIX}/users/employee", headers={"Authorization": "Bearer malformed"}).status_code == 401
    assert u.get(f"{PREFIX}/users/employee").status_code == 401
    with db() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO users(full_name,username,email,password_hash,department,role,status,created_at) VALUES(?,?,?,?,?,?,?,?)", ("X", "x", "x@example.com", "hash", "IT", "Bad Role", "Active", "now"))


def test_notification_cross_user_and_analyst_search(clients):
    u, a, n = clients
    first = register(u, "first").json()
    second = register(u, "second").json()
    first_token = login(u, "first")
    second_token = login(u, "second")
    payload = {"user_id": first["id"], "title": "Alert", "message": "Check event", "type": "Security Alert", "severity": "Medium", "event_id": "alert-1"}
    created = n.post(f"{PREFIX}/notifications", json=payload, headers={"X-Service-Key": os.environ["SERVICE_AUTH_SECRET"]})
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert n.get(f"{PREFIX}/notifications/{item_id}", headers=second_token).status_code == 403
    assert n.get(f"{PREFIX}/notifications/user/{first['id']}", headers=second_token).status_code == 403
    assert n.put(f"{PREFIX}/notifications/{item_id}/read", headers=second_token).status_code == 403
    promote(second["id"], "Security Analyst")
    analyst = login(u, "second")
    assert n.get(f"{PREFIX}/notifications/search", headers=analyst).json() == []
    assert n.get(f"{PREFIX}/notifications/search?user_id={first['id']}", headers=analyst).status_code == 403
    assert n.get(f"{PREFIX}/notifications/{item_id}", headers=first_token).status_code == 200


def test_registration_outbox_delivers_once(clients, monkeypatch):
    u, a, n = clients
    user = register(u, "outboxuser").json()
    from joey import outbox

    def fake_post(url, json, headers, timeout):
        response = n.post(f"{PREFIX}/notifications", json=json, headers=headers)
        return response

    monkeypatch.setattr(outbox.httpx, "post", fake_post)
    real_deliver_pending()
    with db() as conn:
        event = conn.execute("SELECT * FROM outbox WHERE event_id=?", (f"welcome-user-{user['id']}",)).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=?", (user["id"],)).fetchone()[0]
    assert event["delivered_at"] is not None, event["last_error"]
    assert count == 1
    real_deliver_pending()
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=?", (user["id"],)).fetchone()[0] == 1
