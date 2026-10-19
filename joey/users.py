import json
import sqlite3
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from .common import PREFIX, ROLES, api_error_handler, create_token, current_user, db, error, hash_password, init_db, now, queue_audit, require_role, row_dict, service_secret, token_secret, valid_email, valid_password, verify_password


@asynccontextmanager
async def lifespan(_: FastAPI):
    token_secret(); service_secret(); init_db()
    yield


app = FastAPI(title="Joey Saade — Users and Identity", lifespan=lifespan)
api_error_handler(app)


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=1, max_length=200)
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]{3,50}$")
    email: str
    password: str
    department: str = Field(min_length=1, max_length=100)
    role: str = "Regular Employee"


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username_or_email: str
    password: str


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = None
    department: str | None = Field(default=None, min_length=1, max_length=100)


class AdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str | None = None
    status: str | None = None


@app.post(f"{PREFIX}/users/register", status_code=201)
def register(data: Registration, background_tasks: BackgroundTasks):
    if data.role != "Regular Employee":
        error(403, "Public registration cannot assign privileged roles")
    if not valid_email(data.email) or not valid_password(data.password):
        error(422, "Invalid email or password; password needs 12-128 characters with letters and digits")
    with db() as conn:
        try:
            user_id = conn.execute("INSERT INTO user_id_allocations DEFAULT VALUES").lastrowid
            cur = conn.execute("INSERT INTO users(id,full_name,username,email,password_hash,department,role,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (user_id, data.full_name.strip(), data.username.strip(), data.email.lower().strip(), hash_password(data.password), data.department.strip(), data.role, "Active", now()))
        except sqlite3.IntegrityError:
            error(409, "Username or email already exists")
        user = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
        event_id = f"welcome-user-{cur.lastrowid}"
        payload = {"event_id": event_id, "user_id": cur.lastrowid, "title": "Welcome", "message": "Your account is ready", "type": "System Notification", "severity": "Low"}
        conn.execute("INSERT INTO outbox(event_id,destination,payload_json,created_at) VALUES(?,?,?,?)", (event_id, "notification", json.dumps(payload), now()))
        queue_audit(conn, "user_created", cur.lastrowid, data.username, subject_id=cur.lastrowid)
        result = row_dict(user, "password_hash")
    from .outbox import deliver_pending
    background_tasks.add_task(deliver_pending)
    return result


@app.post(f"{PREFIX}/users/login")
def login(data: Login):
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=? OR email=?", (data.username_or_email, data.username_or_email)).fetchone()
        if not user or not verify_password(data.password, user["password_hash"]):
            queue_audit(conn, "login_failed", user["id"] if user else None, data.username_or_email, severity="Warning")
            failure = (401, "Invalid credentials")
        elif user["status"] != "Active":
            queue_audit(conn, "login_failed", user["id"], user["username"], severity="Warning")
            failure = (403, "Account is not active")
        else:
            failure = None
        if failure is None:
            conn.execute("UPDATE users SET last_login_at=? WHERE id=?", (now(), user["id"]))
            queue_audit(conn, "login_success", user["id"], user["username"])
            result = {"access_token": create_token(user["id"]), "token_type": "bearer", "expires_in": 3600}
    if failure:
        error(*failure)
    return result


@app.get(f"{PREFIX}/users")
def list_users(actor=Depends(current_user)):
    require_role(actor, "Security Administrator", "Security Auditor")
    with db() as conn:
        return [row_dict(x, "password_hash") for x in conn.execute("SELECT * FROM users ORDER BY id")]


@app.put(f"{PREFIX}/users/{{id}}")
def update_user(id: int, data: ProfileUpdate, actor=Depends(current_user)):
    if actor["role"] != "Security Administrator" and actor["id"] != id:
        error(403, "Users may update only their own profile")
    changes = data.model_dump(exclude_unset=True)
    if not changes or any(v is None for v in changes.values()):
        error(422, "Provide at least one non-null profile field")
    if "email" in changes and not valid_email(changes["email"]):
        error(422, "Invalid email")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (id,)).fetchone():
            error(404, "User not found")
        try:
            conn.execute("UPDATE users SET " + ", ".join(f"{k}=?" for k in changes) + " WHERE id=?", (*changes.values(), id))
        except sqlite3.IntegrityError:
            error(409, "Email already exists")
        queue_audit(conn, "user_updated", actor["id"], actor["username"], subject_id=id)
        return row_dict(conn.execute("SELECT * FROM users WHERE id=?", (id,)).fetchone(), "password_hash")


@app.patch(f"{PREFIX}/users/{{id}}/admin")
def admin_update(id: int, data: AdminUpdate, actor=Depends(current_user)):
    require_role(actor, "Security Administrator")
    changes = data.model_dump(exclude_unset=True)
    if not changes or any(v is None for v in changes.values()):
        error(422, "Provide role or status")
    if "role" in changes and changes["role"] not in ROLES:
        error(422, "Invalid role")
    if "status" in changes and changes["status"] not in ("Active", "Inactive", "Suspended"):
        error(422, "Invalid status")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (id,)).fetchone():
            error(404, "User not found")
        conn.execute("UPDATE users SET " + ", ".join(f"{k}=?" for k in changes) + " WHERE id=?", (*changes.values(), id))
        queue_audit(conn, "role_changed" if "role" in changes else "user_status_changed", actor["id"], actor["username"], subject_id=id)
        return row_dict(conn.execute("SELECT * FROM users WHERE id=?", (id,)).fetchone(), "password_hash")


@app.delete(f"{PREFIX}/users/{{id}}")
def delete_user(id: int, actor=Depends(current_user)):
    require_role(actor, "Security Administrator")
    if actor["id"] == id:
        error(409, "Administrator cannot delete own account")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (id,)).fetchone():
            error(404, "User not found")
        try:
            conn.execute("DELETE FROM users WHERE id=?", (id,))
        except sqlite3.IntegrityError:
            error(409, "User is referenced by assets or notifications")
        queue_audit(conn, "user_deleted", actor["id"], actor["username"], subject_id=id)
    return {"message": "User deleted"}


@app.get(f"{PREFIX}/users/{{username}}")
def get_user(username: str, actor=Depends(current_user)):
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        error(404, "User not found")
    if actor["role"] not in ("Security Administrator", "Security Auditor") and actor["id"] != user["id"]:
        error(403, "Users may view only their own profile")
    return row_dict(user, "password_hash")
