"""Run Joey Saade's exported Postman collection with Newman against all nine real services and a disposable database."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from live_smoke import wait_ready
from live_smoke_christophe import PORTS, url

PASSWORD = "SecurePassword123"
PACKAGES = {"users": "joey", "assets": "joey", "notifications": "joey", "threats": "christophe", "vulnerabilities": "christophe", "incidents": "christophe"}


def main():
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        raise SystemExit("Node.js/npm (npx) is required to run Newman")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        env = dict(os.environ)
        env.update(DATABASE_PATH=str(Path(temp) / "postman.db"), AUTH_SECRET="postman-auth-secret-at-least-32-characters",
                   SERVICE_AUTH_SECRET="postman-service-secret-at-least-32-characters", AUDIT_SERVICE_AUTH_SECRET="postman-audit-secret-at-least-32-characters",
                   NOTIFICATION_SERVICE_URL=f"http://127.0.0.1:{PORTS['notifications']}", AUDIT_SERVICE_URL=f"http://127.0.0.1:{PORTS['audit_logs']}",
                   BOOTSTRAP_ADMIN_NAME="Joey Saade", BOOTSTRAP_ADMIN_USERNAME="joey_admin", BOOTSTRAP_ADMIN_EMAIL="joey@example.test",
                   BOOTSTRAP_ADMIN_PASSWORD=PASSWORD, BOOTSTRAP_ADMIN_DEPARTMENT="Security")
        for name, variable in (("assets", "ASSET_REPORT_SOURCE"), ("threats", "THREAT_REPORT_SOURCE"), ("vulnerabilities", "VULNERABILITY_REPORT_SOURCE"), ("incidents", "INCIDENT_REPORT_SOURCE"), ("audit_logs", "AUDIT_REPORT_SOURCE")):
            env[variable] = url(name, "/logs" if name == "audit_logs" else "/" + name)
        subprocess.run([sys.executable, "-c", "from christophe.common import init_db; init_db(); from karl.common import init_db; init_db()"], env=env, check=True)
        subprocess.run([sys.executable, "-m", "joey.bootstrap_admin"], env=env, check=True)
        processes, log_files = [], []
        try:
            for name, port in PORTS.items():
                log_files.append(open(Path(temp) / f"{name}.log", "w"))
                processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", f"{PACKAGES.get(name, 'karl')}.{name}:app", "--host", "127.0.0.1", "--port", str(port)], env=env, stdout=log_files[-1], stderr=subprocess.STDOUT))
            for port in PORTS.values():
                wait_ready(port)
            print("All nine real HTTP services are ready", flush=True)
            args = [npx, "--yes", "newman@6.2.1", "run", "postman/joey.collection.json", "-e", "postman/joey.environment.template.json", "--reporters", "cli", "--reporter-cli-no-banner", "--timeout-request", "30000"]
            values = {"userUrl": f"http://127.0.0.1:{PORTS['users']}", "assetUrl": f"http://127.0.0.1:{PORTS['assets']}", "notificationUrl": f"http://127.0.0.1:{PORTS['notifications']}",
                      "username": "joey_admin", "userPassword": PASSWORD, "serviceKey": env["SERVICE_AUTH_SECRET"]}
            for key, value in values.items():
                args += ["--env-var", f"{key}={value}"]
            result = subprocess.run(args, env=env)
            for log in log_files:
                log.flush()
            tracebacks = [name for name in PORTS if "Traceback" in (Path(temp) / f"{name}.log").read_text(encoding="utf-8", errors="replace")]
            assert not tracebacks, f"server exceptions logged by {tracebacks}"
            if result.returncode:
                raise SystemExit(f"Newman reported failures (exit {result.returncode})")
            print("PASS: Joey Saade's exported Postman collection against nine actual servers; no server tracebacks", flush=True)
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
