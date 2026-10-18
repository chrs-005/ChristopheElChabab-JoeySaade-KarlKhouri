import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, Header, HTTPException

def load_local_env():
    file = Path(".env")
    if not file.exists():
        return
    for line in file.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_local_env()
PREFIX = "/api/Joey-Saade"
ROLES = ("Security Administrator", "Security Analyst", "Security Auditor", "Regular Employee")
DB_PATH = Path(os.getenv("DATABASE_PATH", "joey.db"))


def now():
    return datetime.now(timezone.utc).isoformat()


def error(status, message):
    raise HTTPException(status_code=status, detail=message)


@contextmanager
def db():
    conn = sqlite3.connect(os.getenv("DATABASE_PATH", str(DB_PATH)), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript((Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))


def row_dict(row, *excluded):
    return {key: row[key] for key in row.keys() if key not in excluded}


def queue_audit(conn, action, actor_user_id=None, actor_label=None, related_service="users", subject_id=None, severity="Information", description=None):
    event_id = str(uuid.uuid4())
    payload = {"event_id": event_id, "actor_user_id": actor_user_id, "actor_label": actor_label, "action": action, "description": description or action, "occurred_at": now(), "severity": severity, "related_service": related_service, "subject_id": str(subject_id) if subject_id is not None else None}
    conn.execute("INSERT INTO outbox(event_id,destination,payload_json,created_at) VALUES(?,?,?,?)", (event_id, "audit", json.dumps(payload), now()))


def hash_password(password):
    salt = secrets.token_bytes(16)
    rounds = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        algorithm, rounds, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def token_secret():
    value = os.getenv("AUTH_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("AUTH_SECRET must contain at least 32 characters")
    return value.encode()


def service_secret():
    value = os.getenv("SERVICE_AUTH_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("SERVICE_AUTH_SECRET must contain at least 32 characters")
    return value


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def create_token(user_id, ttl=3600):
    payload = {"sub": user_id, "exp": int(time.time()) + ttl, "nonce": secrets.token_hex(8)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(token_secret(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def decode_token(token):
    try:
        body, signature = token.split(".")
        expected = _b64(hmac.new(token_secret(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            error(401, "Invalid token")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if not isinstance(payload.get("sub"), int) or payload.get("exp", 0) <= time.time():
            error(401, "Expired or invalid token")
        return payload
    except (ValueError, KeyError, json.JSONDecodeError, binascii.Error, UnicodeDecodeError):
        error(401, "Invalid token")


def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        error(401, "Missing bearer token")
    payload = decode_token(authorization[7:])
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (payload["sub"],)).fetchone()
    if not user or user["status"] != "Active":
        error(401, "Account unavailable")
    return row_dict(user, "password_hash")


def require_role(user, *roles):
    if user["role"] not in roles:
        error(403, "User does not have permission to perform this operation")


def require_service(x_service_key: str | None = Header(default=None)):
    if not x_service_key or not hmac.compare_digest(x_service_key, service_secret()):
        error(401, "Invalid service credential")
    return True


def valid_password(password):
    return len(password) >= 12 and len(password) <= 128 and bool(re.search(r"[A-Za-z]", password)) and bool(re.search(r"\d", password))


def valid_email(email):
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email))


def api_error_handler(app, record_denial=None):
    # The audit service passes a direct writer so its own denials are not sent back to itself over HTTP.
    record_denial = record_denial or queue_audit
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        if exc.status_code == 403:
            try:
                header = request.headers.get("authorization", "")
                actor_id = decode_token(header[7:])["sub"] if header.startswith("Bearer ") else None
                with db() as conn:
                    record_denial(conn, "unauthorized_access", actor_id, related_service=app.title, description=f"Forbidden {request.method} {request.url.path}", severity="Warning")
            except Exception:
                pass  # Denial must not become a server error when audit storage is unavailable.
        return JSONResponse(status_code=exc.status_code, content={"status": "error", "message": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"status": "error", "message": "Invalid request", "errors": [{"field": ".".join(map(str, x["loc"])), "message": x["msg"]} for x in exc.errors()]})
