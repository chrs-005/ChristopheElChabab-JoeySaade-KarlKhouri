import hmac
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, Response
from pydantic import BaseModel, ConfigDict, Field

from joey.common import api_error_handler, current_user, db, error, require_role, row_dict, token_secret

from .common import PREFIX, audit_secret, date_range, init_db, parse_time, stored_time

LOG_SEVERITIES = ("Information", "Warning", "Error", "Critical")
# The handout lets analysts retrieve and search audit logs; only administrators delete or add manual entries.
READERS = ("Security Administrator", "Security Analyst", "Security Auditor")


@asynccontextmanager
async def lifespan(_: FastAPI):
    token_secret(); audit_secret(); init_db()
    yield


app = FastAPI(title="Karl Khouri — Security Audit Logging", lifespan=lifespan)


def write_log(conn, action, actor_user_id=None, actor_label=None, related_service="audit", subject_id=None, severity="Information", description=None, event_id=None, occurred_at=None, source="audit"):
    """Insert one entry directly. Used for this service's own events, so nothing is sent back over HTTP."""
    known = actor_user_id is not None and conn.execute("SELECT username FROM users WHERE id=?", (actor_user_id,)).fetchone()
    if known and not actor_label:
        actor_label = known["username"]
    stamp = stored_time(datetime.now(timezone.utc))
    # A user deleted before a queued event arrives keeps the historical ID without breaking the FK.
    cur = conn.execute(
        "INSERT INTO audit_logs(event_id,actor_user_id,original_actor_user_id,actor_label,action,description,severity,related_service,subject_id,occurred_at,recorded_at,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (event_id or str(uuid.uuid4()), actor_user_id if known else None, actor_user_id, actor_label, action, description or action, severity, related_service, None if subject_id is None else str(subject_id), occurred_at or stamp, stamp, source),
    )
    return cur.lastrowid


api_error_handler(app, record_denial=write_log)


class LogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str | None = Field(default=None, min_length=1, max_length=200)
    actor_user_id: int | None = None
    actor_label: str | None = Field(default=None, max_length=200)
    action: str = Field(pattern=r"^[a-z][a-z0-9_.-]{1,99}$")
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    occurred_at: str | None = None
    severity: str = "Information"
    related_service: str | None = Field(default=None, min_length=1, max_length=100)
    subject_id: str | None = Field(default=None, max_length=200)


def principal(authorization: str | None = Header(default=None), x_service_key: str | None = Header(default=None)):
    if x_service_key:
        if not hmac.compare_digest(x_service_key, audit_secret()):
            error(401, "Invalid service credential")
        return {"service": True}
    return current_user(authorization)


def get_log(conn, id):
    item = conn.execute("SELECT * FROM audit_logs WHERE id=?", (id,)).fetchone()
    if not item:
        error(404, "Log entry not found")
    return item


@app.post(f"{PREFIX}/logs", status_code=201)
def create_log(data: LogCreate, response: Response, actor=Depends(principal)):
    if data.severity not in LOG_SEVERITIES:
        error(422, "Invalid severity")
    if actor.get("service"):
        if not data.event_id or not data.related_service:
            error(422, "Service events require event_id and related_service")
        occurred = parse_time(data.occurred_at, "occurred_at") if data.occurred_at else datetime.now(timezone.utc)
        if occurred > datetime.now(timezone.utc) + timedelta(minutes=5):
            error(422, "occurred_at cannot be in the future")
        actor_id, label, source = data.actor_user_id, data.actor_label, "service"
    else:
        require_role(actor, "Security Administrator")
        # People cannot attribute entries to someone else or backdate them; both come from the token and the clock.
        if data.actor_user_id is not None or data.actor_label is not None or data.occurred_at is not None:
            error(422, "Actor and time are derived from the authenticated request")
        occurred = datetime.now(timezone.utc)
        actor_id, label, source = actor["id"], actor["username"], "user"
    try:
        with db() as conn:
            log_id = write_log(conn, data.action, actor_id, label, data.related_service or "manual", data.subject_id, data.severity, data.description, data.event_id, stored_time(occurred), source)
            return row_dict(get_log(conn, log_id))
    except sqlite3.IntegrityError:
        # Retried or concurrently delivered event: the first stored copy wins.
        with db() as conn:
            existing = conn.execute("SELECT * FROM audit_logs WHERE event_id=?", (data.event_id,)).fetchone()
        if not existing:
            raise
        response.status_code = 200
        return row_dict(existing)


@app.get(f"{PREFIX}/logs")
def list_logs(actor=Depends(current_user)):
    require_role(actor, *READERS)
    with db() as conn:
        return [row_dict(x) for x in conn.execute("SELECT * FROM audit_logs ORDER BY occurred_at DESC, id DESC")]


@app.get(f"{PREFIX}/logs/search")
def search_logs(actor_user_id: int | None = None, action: str | None = None, severity: str | None = None, related_service: str | None = None, subject_id: str | None = None, start_date: str | None = None, end_date: str | None = None, actor=Depends(current_user)):
    require_role(actor, *READERS)
    if severity is not None and severity not in LOG_SEVERITIES:
        error(422, "Invalid severity")
    start, end = date_range(start_date, end_date)
    clauses, args = [], []
    for column, value in (("original_actor_user_id", actor_user_id), ("action", action), ("severity", severity), ("related_service", related_service), ("subject_id", subject_id)):
        if value is not None:
            clauses.append(f"{column}=?")
            args.append(value)
    if start:
        clauses.append("occurred_at>=?"); args.append(stored_time(start))
    if end:
        clauses.append("occurred_at<=?"); args.append(stored_time(end))
    query = "SELECT * FROM audit_logs" + (" WHERE " + " AND ".join(clauses) if clauses else "")
    with db() as conn:
        return [row_dict(x) for x in conn.execute(query + " ORDER BY occurred_at DESC, id DESC", args)]


@app.get(f"{PREFIX}/logs/user/{{user_id}}")
def logs_for_user(user_id: int, actor=Depends(current_user)):
    if actor["role"] not in READERS and actor["id"] != user_id:
        error(403, "Users may view only their own activity")
    with db() as conn:
        rows = conn.execute("SELECT * FROM audit_logs WHERE original_actor_user_id=? ORDER BY occurred_at DESC, id DESC", (user_id,)).fetchall()
        if not rows and not conn.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
            error(404, "User not found")
    return [row_dict(x) for x in rows]


@app.get(f"{PREFIX}/logs/{{id}}")
def read_log(id: int, actor=Depends(current_user)):
    require_role(actor, *READERS)
    with db() as conn:
        return row_dict(get_log(conn, id))


@app.delete(f"{PREFIX}/logs/{{id}}")
def delete_log(id: int, actor=Depends(current_user)):
    require_role(actor, "Security Administrator")
    with db() as conn:
        item = get_log(conn, id)
        if item["action"] == "audit_log_deleted":
            error(409, "Deletion records are permanent")
        conn.execute("DELETE FROM audit_logs WHERE id=?", (id,))
        write_log(conn, "audit_log_deleted", actor["id"], actor["username"], subject_id=id, severity="Warning", description=f"Deleted log {id} ({item['action']} from {item['related_service']})")
    return {"message": "Log entry deleted"}
