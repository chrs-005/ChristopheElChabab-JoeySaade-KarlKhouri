"""Start the users/assets/notifications services plus Karl Khouri's audit, playbook and report services, then exercise them over real HTTP."""
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import httpx

from live_smoke import wait_ready

PORTS = {"users": 18001, "assets": 18002, "notifications": 18003, "audit_logs": 18007, "playbooks": 18008, "reports": 18009}
JOEY = "/api/Joey-Saade"
KARL = "/api/Karl-Khouri"
PASSWORD = "SecurePassword123"


def url(service, path):
    prefix = KARL if service in ("audit_logs", "playbooks", "reports") else JOEY
    return f"http://127.0.0.1:{PORTS[service]}{prefix}{path}"


def check(response, status, label):
    assert response.status_code == status, f"{label}: expected {status}, got {response.status_code} {response.text}"
    print(f"  {label}: HTTP {status}")
    return response.json()


def main():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:  # Windows can hold a closed log briefly
        env = dict(os.environ)
        env.update({
            "DATABASE_PATH": str(Path(temp) / "smoke.db"), "AUTH_SECRET": "smoke-auth-secret-with-at-least-32-characters",
            "SERVICE_AUTH_SECRET": "smoke-service-secret-with-at-least-32-characters", "AUDIT_SERVICE_AUTH_SECRET": "smoke-audit-secret-with-at-least-32-characters",
            "NOTIFICATION_SERVICE_URL": "http://127.0.0.1:18003", "AUDIT_SERVICE_URL": "http://127.0.0.1:18007",
            "ASSET_REPORT_SOURCE": url("assets", "/assets"), "AUDIT_REPORT_SOURCE": url("audit_logs", "/logs"),
            "INCIDENT_REPORT_SOURCE": "http://127.0.0.1:18006/api/Christophe-El-Chabab/incidents",
            "THREAT_REPORT_SOURCE": "http://127.0.0.1:18004/api/Christophe-El-Chabab/threats",
            "VULNERABILITY_REPORT_SOURCE": "http://127.0.0.1:18005/api/Christophe-El-Chabab/vulnerabilities",
            "BOOTSTRAP_ADMIN_NAME": "Smoke Admin", "BOOTSTRAP_ADMIN_USERNAME": "smoke_admin", "BOOTSTRAP_ADMIN_EMAIL": "admin@example.test",
            "BOOTSTRAP_ADMIN_PASSWORD": PASSWORD, "BOOTSTRAP_ADMIN_DEPARTMENT": "Security",
        })
        subprocess.run([sys.executable, "-m", "joey.bootstrap_admin"], env=env, check=True)
        processes, log_files = [], []
        try:
            for name, port in PORTS.items():
                package = "karl" if name in ("audit_logs", "playbooks", "reports") else "joey"
                log_files.append(open(Path(temp) / f"{name}.log", "w"))
                processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", f"{package}.{name}:app", "--host", "127.0.0.1", "--port", str(port)], env=env, stdout=subprocess.DEVNULL, stderr=log_files[-1], text=True))
            for port in PORTS.values():
                wait_ready(port)
            print("six services started")
            login = lambda user: {"Authorization": "Bearer " + check(httpx.post(url("users", "/users/login"), json={"username_or_email": user, "password": PASSWORD}, timeout=8), 200, f"login {user}")["access_token"]}
            admin = login("smoke_admin")
            analyst = check(httpx.post(url("users", "/users/register"), json={"full_name": "Smoke Analyst", "username": "smoke_analyst", "email": "analyst@example.test", "password": PASSWORD, "department": "SOC", "role": "Regular Employee"}, timeout=8), 201, "register analyst")
            check(httpx.patch(url("users", f"/users/{analyst['id']}/admin"), json={"role": "Security Analyst"}, headers=admin, timeout=8), 200, "promote analyst")
            analyst_h = login("smoke_analyst")
            check(httpx.post(url("users", "/users/login"), json={"username_or_email": "nobody", "password": "WrongPassword1"}, timeout=8), 401, "failed login")
            check(httpx.post(url("assets", "/assets"), json={"name": "Mail gateway", "type": "Server", "ip_address": "10.0.0.25", "department": "IT", "owner_id": analyst["id"], "location": "DC1", "criticality": "High"}, headers=admin, timeout=8), 201, "create asset")

            print("audit logging")
            subprocess.run([sys.executable, "-m", "joey.outbox"], env=env, check=True)
            logs = check(httpx.get(url("audit_logs", "/logs"), headers=admin, timeout=8), 200, "list logs")
            actions = {x["action"] for x in logs}
            assert {"user_created", "login_success", "login_failed", "role_changed", "asset_created"} <= actions, actions
            failed = check(httpx.get(url("audit_logs", "/logs/search"), params={"action": "login_failed"}, headers=admin, timeout=8), 200, "search failed logins")
            assert failed[0]["actor_user_id"] is None and failed[0]["actor_label"] == "nobody"
            check(httpx.get(url("audit_logs", "/logs"), headers=analyst_h, timeout=8), 403, "analyst denied log list")
            check(httpx.get(url("audit_logs", f"/logs/user/{analyst['id']}"), headers=analyst_h, timeout=8), 200, "analyst reads own activity")

            print("playbooks")
            playbook = check(httpx.post(url("playbooks", "/playbooks"), json={"name": "Phishing containment", "description": "Contain a reported phishing email", "category": "Phishing", "severity": "High", "steps": [
                {"title": "Block sender", "description": "Block the sender domain at the gateway", "assigned_to": analyst["id"]},
                {"title": "Purge messages", "description": "Remove delivered copies", "assigned_to": analyst["id"]}]}, headers=analyst_h, timeout=8), 201, "create playbook with two steps")
            first, second = (a["id"] for a in playbook["actions"])
            check(httpx.post(url("playbooks", f"/playbooks/{playbook['id']}/actions"), json={"step_order": 4, "title": "Report", "description": "Write report", "assigned_to": analyst["id"]}, headers=admin, timeout=8), 422, "reject out-of-order step")
            check(httpx.put(url("playbooks", f"/actions/{second}/status"), json={"status": "In Progress"}, headers=analyst_h, timeout=8), 409, "reject starting step 2 first")
            for action in (first, second):
                for state in ("In Progress", "Completed"):
                    check(httpx.put(url("playbooks", f"/actions/{action}/status"), json={"status": state}, headers=analyst_h, timeout=8), 200, f"action {action} -> {state}")
            detail = check(httpx.get(url("playbooks", f"/playbooks/{playbook['id']}"), headers=admin, timeout=8), 200, "playbook detail")
            assert detail["execution_status"] == "Completed", detail
            check(httpx.get(url("notifications", f"/notifications/user/{analyst['id']}"), headers=analyst_h, timeout=8), 200, "analyst notifications")

            print("reports")
            subprocess.run([sys.executable, "-m", "joey.outbox"], env=env, check=True)
            asset_report = check(httpx.get(url("reports", "/reports/assets"), headers=admin, timeout=8), 200, "asset report")
            assert asset_report["total"] == len(httpx.get(url("assets", "/assets"), headers=admin, timeout=8).json()) == 1
            # Report events keep arriving in the background, so the total must fall between two direct reads.
            before = len(httpx.get(url("audit_logs", "/logs"), headers=admin, timeout=8).json())
            activity = check(httpx.get(url("reports", "/reports/activity"), headers=admin, timeout=8), 200, "activity report")
            after = len(httpx.get(url("audit_logs", "/logs"), headers=admin, timeout=8).json())
            assert before <= activity["total_events"] <= after, (before, activity["total_events"], after)
            print(f"  activity total {activity['total_events']} reconciles with stored logs ({before}..{after})")
            assert activity["failed_logins"] == 1
            check(httpx.get(url("reports", "/reports/incidents"), headers=admin, timeout=8), 503, "incident report reports unavailable upstream")
            summary = check(httpx.get(url("reports", "/reports/summary"), headers=admin, timeout=8), 200, "summary report")
            assert summary["complete"] is False and summary["incidents"] is None and summary["assets"]["total"] == 1
            check(httpx.get(url("reports", "/reports/summary"), headers=analyst_h, timeout=8), 403, "analyst denied reports")
            with closing(sqlite3.connect(env["DATABASE_PATH"])) as conn:
                stored = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
                pending = conn.execute("SELECT COUNT(*) FROM outbox WHERE destination='audit' AND delivered_at IS NULL").fetchone()[0]
            print(f"database: {stored} audit log rows, {pending} audit events still queued (report events queued after the last delivery)")
            for log in log_files:
                log.flush()
            errors = [name for name in PORTS if "Traceback" in (Path(temp) / f"{name}.log").read_text(encoding="utf-8", errors="replace")]
            assert not errors, f"server errors logged by {errors}"
            print("live HTTP: audit logging, playbook execution and reports passed; no server tracebacks logged")
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            for log in log_files:
                log.close()


if __name__ == "__main__":
    main()
