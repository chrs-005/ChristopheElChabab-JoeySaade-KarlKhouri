import hmac
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header
from pydantic import BaseModel, ConfigDict, Field

from .common import PREFIX, api_error_handler, current_user, db, error, init_db, now, queue_audit, require_role, row_dict, service_secret, token_secret

TYPES = ("Incident Assignment", "Security Alert", "System Notification", "Threat Alert", "Vulnerability Alert")
SEVERITIES = ("Low", "Medium", "High", "Critical")


@asynccontextmanager
async def lifespan(_: FastAPI):
    token_secret(); service_secret(); init_db()
    yield


app = FastAPI(title="Joey Saade — Notification and Alert Management", lifespan=lifespan)
api_error_handler(app)


class NotificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    type: str
    severity: str
    event_id: str | None = Field(default=None, max_length=200)


def principal(authorization: str | None = Header(default=None), x_service_key: str | None = Header(default=None)):
    if x_service_key and hmac.compare_digest(x_service_key, service_secret()):
        return {"service": True}
    return current_user(authorization)


def scoped_user(actor, target_id):
    if actor["role"] not in ("Security Administrator", "Security Auditor") and actor["id"] != target_id:
        error(403, "Notifications belong to another user")


@app.post(f"{PREFIX}/notifications", status_code=201)
def create_notification(data: NotificationCreate, actor=Depends(principal)):
    if not actor.get("service"):
        require_role(actor, "Security Administrator")
    if data.type not in TYPES or data.severity not in SEVERITIES:
        error(422, "Invalid notification type or severity")
    if actor.get("service") and not data.event_id:
        error(422, "Service notifications require event_id")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (data.user_id,)).fetchone():
            error(422, "Recipient does not exist")
        if data.event_id:
            existing = conn.execute("SELECT * FROM notifications WHERE event_id=?", (data.event_id,)).fetchone()
            if existing:
                return row_dict(existing)
        try:
            cur = conn.execute("INSERT INTO notifications(user_id,title,message,type,severity,status,created_at,event_id) VALUES(?,?,?,?,?,?,?,?)", (data.user_id, data.title, data.message, data.type, data.severity, "Unread", now(), data.event_id))
        except sqlite3.IntegrityError:
            error(409, "Notification event conflict")
        queue_audit(conn, "notification_created", None if actor.get("service") else actor["id"], "service" if actor.get("service") else actor["username"], related_service="notifications", subject_id=cur.lastrowid)
        return row_dict(conn.execute("SELECT * FROM notifications WHERE id=?", (cur.lastrowid,)).fetchone())


@app.get(f"{PREFIX}/notifications/user/{{user_id}}")
def list_for_user(user_id: int, actor=Depends(current_user)):
    scoped_user(actor, user_id)
    with db() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
            error(404, "User not found")
        return [row_dict(x) for x in conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC", (user_id,))]


@app.get(f"{PREFIX}/notifications/search")
def search_notifications(user_id: int | None = None, type: str | None = None, severity: str | None = None, status: str | None = None, actor=Depends(current_user)):
    if actor["role"] not in ("Security Administrator", "Security Auditor", "Security Analyst"):
        error(403, "Search is not permitted")
    if actor["role"] == "Security Analyst":
        if user_id is not None and user_id != actor["id"]:
            error(403, "Notifications belong to another user")
        user_id = actor["id"]
    filters = {k: v for k, v in {"user_id": user_id, "type": type, "severity": severity, "status": status}.items() if v is not None}
    query = "SELECT * FROM notifications"
    if filters:
        query += " WHERE " + " AND ".join(f"{key}=?" for key in filters)
    with db() as conn:
        return [row_dict(x) for x in conn.execute(query + " ORDER BY id DESC", list(filters.values()))]


@app.get(f"{PREFIX}/notifications/{{id}}")
def get_notification(id: int, actor=Depends(current_user)):
    with db() as conn:
        item = conn.execute("SELECT * FROM notifications WHERE id=?", (id,)).fetchone()
    if not item:
        error(404, "Notification not found")
    scoped_user(actor, item["user_id"])
    return row_dict(item)


@app.put(f"{PREFIX}/notifications/{{id}}/read")
def mark_read(id: int, actor=Depends(current_user)):
    if actor["role"] == "Security Auditor":
        error(403, "Auditor has read-only access")
    with db() as conn:
        item = conn.execute("SELECT * FROM notifications WHERE id=?", (id,)).fetchone()
        if not item:
            error(404, "Notification not found")
        scoped_user(actor, item["user_id"])
        if item["status"] != "Read":
            conn.execute("UPDATE notifications SET status='Read',read_at=? WHERE id=?", (now(), id))
            queue_audit(conn, "notification_read", actor["id"], actor["username"], related_service="notifications", subject_id=id)
        return row_dict(conn.execute("SELECT * FROM notifications WHERE id=?", (id,)).fetchone())


@app.delete(f"{PREFIX}/notifications/{{id}}")
def delete_notification(id: int, actor=Depends(current_user)):
    require_role(actor, "Security Administrator")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM notifications WHERE id=?", (id,)).fetchone():
            error(404, "Notification not found")
        conn.execute("DELETE FROM notifications WHERE id=?", (id,))
        queue_audit(conn, "notification_deleted", actor["id"], actor["username"], related_service="notifications", subject_id=id)
    return {"message": "Notification deleted"}
