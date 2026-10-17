"""Start Joey's three servers and verify a real HTTP registration-to-notification flow."""
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

import httpx


def wait_ready(port):
    for _ in range(60):
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/openapi.json", timeout=1)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Server on {port} did not start")


def main():
    with tempfile.TemporaryDirectory() as temp:
        env = dict(os.environ)
        env.update({"DATABASE_PATH": str(Path(temp) / "smoke.db"), "AUTH_SECRET": "smoke-auth-secret-with-at-least-32-characters", "SERVICE_AUTH_SECRET": "smoke-service-secret-with-at-least-32-characters", "NOTIFICATION_SERVICE_URL": "http://127.0.0.1:18003"})
        processes = []
        try:
            for name, port in (("users", 18001), ("assets", 18002), ("notifications", 18003)):
                processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", f"joey.{name}:app", "--host", "127.0.0.1", "--port", str(port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True))
            for port in (18001, 18002, 18003):
                wait_ready(port)
            prefix = "/api/Joey-Saade"
            created = httpx.post(f"http://127.0.0.1:18001{prefix}/users/register", json={"full_name": "Live User", "username": "live_user", "email": "live@example.test", "password": "SecurePassword123", "department": "IT", "role": "Regular Employee"}, timeout=8)
            assert created.status_code == 201, created.text
            login = httpx.post(f"http://127.0.0.1:18001{prefix}/users/login", json={"username_or_email": "live_user", "password": "SecurePassword123"}, timeout=8)
            assert login.status_code == 200, login.text
            headers = {"Authorization": "Bearer " + login.json()["access_token"]}
            notifications = httpx.get(f"http://127.0.0.1:18003{prefix}/notifications/user/{created.json()['id']}", headers=headers, timeout=8)
            assert notifications.status_code == 200, notifications.text
            assert any(x["title"] == "Welcome" for x in notifications.json()), notifications.text
            with closing(sqlite3.connect(env["DATABASE_PATH"])) as conn:
                assert conn.execute("SELECT COUNT(*) FROM outbox WHERE destination='notification' AND delivered_at IS NOT NULL").fetchone()[0] == 1
            print("live HTTP: registration, login, automatic notification and outbox delivery passed")
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()


if __name__ == "__main__":
    main()
