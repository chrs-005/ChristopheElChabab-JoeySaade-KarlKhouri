"""One-time administrator creation from local environment; never exposes a public admin route."""
import os

from .common import db, hash_password, init_db, now, valid_email, valid_password


def main():
    required = ("BOOTSTRAP_ADMIN_NAME", "BOOTSTRAP_ADMIN_USERNAME", "BOOTSTRAP_ADMIN_EMAIL", "BOOTSTRAP_ADMIN_PASSWORD", "BOOTSTRAP_ADMIN_DEPARTMENT")
    values = {key: os.getenv(key, "") for key in required}
    if not all(values.values()) or not valid_email(values["BOOTSTRAP_ADMIN_EMAIL"]) or not valid_password(values["BOOTSTRAP_ADMIN_PASSWORD"]):
        raise SystemExit("Set all BOOTSTRAP_ADMIN_* values with a valid email and 12+ character letter/digit password")
    init_db()
    with db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE role='Security Administrator'").fetchone():
            raise SystemExit("An administrator already exists")
        conn.execute("INSERT INTO users(full_name,username,email,password_hash,department,role,status,created_at) VALUES(?,?,?,?,?,?,?,?)", (values["BOOTSTRAP_ADMIN_NAME"], values["BOOTSTRAP_ADMIN_USERNAME"], values["BOOTSTRAP_ADMIN_EMAIL"], hash_password(values["BOOTSTRAP_ADMIN_PASSWORD"]), values["BOOTSTRAP_ADMIN_DEPARTMENT"], "Security Administrator", "Active", now()))
    print("Administrator created")


if __name__ == "__main__":
    main()
