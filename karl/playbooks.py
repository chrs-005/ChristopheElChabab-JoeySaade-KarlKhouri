import json
import sqlite3
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from joey.common import api_error_handler, current_user, db, error, now, queue_audit, require_role, row_dict, token_secret

from .common import PREFIX, SEVERITIES, init_db

CATEGORIES = ("Malware", "Phishing", "Ransomware", "Unauthorized Access", "Data Breach", "Denial of Service", "Insider Threat", "Vulnerability Remediation", "Other")
STATUSES = ("Pending", "In Progress", "Completed")
NEXT_STATUS = {"Pending": "In Progress", "In Progress": "Completed"}
EDITORS = ("Security Administrator", "Security Analyst")
READERS = ("Security Administrator", "Security Analyst", "Security Auditor")
ASSIGNABLE = ("Security Administrator", "Security Analyst")


@asynccontextmanager
async def lifespan(_: FastAPI):
    token_secret(); init_db()
    yield


app = FastAPI(title="Karl Khouri — Security Playbook and Response Automation", lifespan=lifespan)
api_error_handler(app)


class StepCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_order: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    assigned_to: int


class PlaybookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    category: str
    severity: str
    steps: list[StepCreate] = Field(default_factory=list, max_length=50)


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    note: str | None = Field(default=None, max_length=2000)


def check_assignee(conn, user_id):
    user = conn.execute("SELECT role, status FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        error(422, f"Assignee {user_id} does not exist")
    if user["role"] not in ASSIGNABLE or user["status"] != "Active":
        error(422, f"Assignee {user_id} must be an active analyst or administrator")


def insert_step(conn, playbook, step, order, actor):
    check_assignee(conn, step.assigned_to)
    cur = conn.execute("INSERT INTO response_actions(playbook_id,step_order,title,description,assigned_to,status,created_at) VALUES(?,?,?,?,?,?,?)", (playbook["id"], order, step.title.strip(), step.description.strip(), step.assigned_to, "Pending", now()))
    conn.execute("INSERT INTO action_history(action_id,original_action_id,playbook_id,original_playbook_id,from_status,to_status,changed_by,changed_by_label,changed_at,note) VALUES(?,?,?,?,?,?,?,?,?,?)", (cur.lastrowid, cur.lastrowid, playbook["id"], playbook["id"], None, "Pending", actor["id"], actor["username"], now(), "Step created"))
    event_id = f"playbook-action-{cur.lastrowid}-assigned"
    payload = {"event_id": event_id, "user_id": step.assigned_to, "title": "Response action assigned", "message": f"Step {order} of playbook '{playbook['name']}': {step.title.strip()}", "type": "Security Alert", "severity": playbook["severity"]}
    conn.execute("INSERT INTO outbox(event_id,destination,payload_json,created_at) VALUES(?,?,?,?)", (event_id, "notification", json.dumps(payload), now()))
    queue_audit(conn, "response_action_created", actor["id"], actor["username"], related_service="playbooks", subject_id=cur.lastrowid)
    return cur.lastrowid


def playbook_detail(conn, playbook_id):
    playbook = conn.execute("SELECT * FROM playbooks WHERE id=?", (playbook_id,)).fetchone()
    if not playbook:
        error(404, "Playbook not found")
    actions = [row_dict(x) for x in conn.execute("SELECT * FROM response_actions WHERE playbook_id=? ORDER BY step_order", (playbook_id,))]
    done = sum(a["status"] == "Completed" for a in actions)
    state = "Completed" if actions and done == len(actions) else "In Progress" if done or any(a["status"] == "In Progress" for a in actions) else "Not Started"
    return {**row_dict(playbook), "execution_status": state, "completed_steps": done, "total_steps": len(actions), "actions": actions}


def deliver_later(background_tasks):
    from joey.outbox import deliver_pending
    background_tasks.add_task(deliver_pending)


@app.post(f"{PREFIX}/playbooks", status_code=201)
def create_playbook(data: PlaybookCreate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, *EDITORS)
    if data.category not in CATEGORIES:
        error(422, "Invalid category")
    if data.severity not in SEVERITIES:
        error(422, "Invalid severity")
    orders = [s.step_order if s.step_order is not None else i for i, s in enumerate(data.steps, 1)]
    if orders != list(range(1, len(orders) + 1)):
        error(422, "Steps must be numbered 1, 2, 3 ... in order without gaps or duplicates")
    with db() as conn:
        stamp = now()
        try:
            cur = conn.execute("INSERT INTO playbooks(name,description,category,severity,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (data.name.strip(), data.description.strip(), data.category, data.severity, actor["id"], stamp, stamp))
        except sqlite3.IntegrityError:
            error(409, "A playbook with this name already exists")
        playbook = conn.execute("SELECT * FROM playbooks WHERE id=?", (cur.lastrowid,)).fetchone()
        queue_audit(conn, "playbook_created", actor["id"], actor["username"], related_service="playbooks", subject_id=cur.lastrowid)
        for order, step in zip(orders, data.steps):
            insert_step(conn, playbook, step, order, actor)
        result = playbook_detail(conn, cur.lastrowid)
    deliver_later(background_tasks)
    return result


@app.get(f"{PREFIX}/playbooks")
def list_playbooks(category: str | None = None, severity: str | None = None, actor=Depends(current_user)):
    require_role(actor, *READERS)
    filters = {k: v for k, v in {"category": category, "severity": severity}.items() if v is not None}
    query = "SELECT id FROM playbooks" + (" WHERE " + " AND ".join(f"{k}=?" for k in filters) if filters else "")
    with db() as conn:
        return [playbook_detail(conn, x["id"]) for x in conn.execute(query + " ORDER BY id", list(filters.values())).fetchall()]


@app.get(f"{PREFIX}/playbooks/{{id}}")
def get_playbook(id: int, actor=Depends(current_user)):
    require_role(actor, *READERS)
    with db() as conn:
        return playbook_detail(conn, id)


@app.get(f"{PREFIX}/playbooks/{{id}}/history")
def get_history(id: int, actor=Depends(current_user)):
    require_role(actor, *READERS)
    with db() as conn:
        rows = conn.execute("SELECT * FROM action_history WHERE original_playbook_id=? ORDER BY id", (id,)).fetchall()
        if not rows and not conn.execute("SELECT 1 FROM playbooks WHERE id=?", (id,)).fetchone():
            error(404, "Playbook not found")
    return [row_dict(x) for x in rows]


@app.post(f"{PREFIX}/playbooks/{{id}}/actions", status_code=201)
def add_action(id: int, data: StepCreate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, *EDITORS)
    with db() as conn:
        playbook = conn.execute("SELECT * FROM playbooks WHERE id=?", (id,)).fetchone()
        if not playbook:
            error(404, "Playbook not found")
        next_order = conn.execute("SELECT COALESCE(MAX(step_order), 0) + 1 FROM response_actions WHERE playbook_id=?", (id,)).fetchone()[0]
        order = data.step_order or next_order
        if order < next_order:
            error(409, f"Step {order} already exists; the next step is {next_order}")
        if order > next_order:
            error(422, f"Steps must be added in order; the next step is {next_order}")
        action_id = insert_step(conn, playbook, data, order, actor)
        conn.execute("UPDATE playbooks SET updated_at=? WHERE id=?", (now(), id))
        result = row_dict(conn.execute("SELECT * FROM response_actions WHERE id=?", (action_id,)).fetchone())
    deliver_later(background_tasks)
    return result


@app.put(f"{PREFIX}/actions/{{id}}/status")
def update_action_status(id: int, data: StatusUpdate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, *EDITORS)
    if data.status not in STATUSES:
        error(422, "Invalid status")
    with db() as conn:
        action = conn.execute("SELECT * FROM response_actions WHERE id=?", (id,)).fetchone()
        if not action:
            error(404, "Response action not found")
        if actor["role"] != "Security Administrator" and actor["id"] != action["assigned_to"]:
            error(403, "Only the assigned analyst or an administrator can update this action")
        if NEXT_STATUS.get(action["status"]) != data.status:
            error(409, f"Invalid transition {action['status']} -> {data.status}; allowed: Pending -> In Progress -> Completed")
        unfinished = conn.execute("SELECT step_order FROM response_actions WHERE playbook_id=? AND step_order<? AND status!='Completed' ORDER BY step_order", (action["playbook_id"], action["step_order"])).fetchone()
        if unfinished:
            error(409, f"Step {unfinished['step_order']} must be completed first")
        stamp = now()
        if data.status == "In Progress":
            conn.execute("UPDATE response_actions SET status=?, started_at=? WHERE id=?", (data.status, stamp, id))
        else:
            conn.execute("UPDATE response_actions SET status=?, completed_at=?, completed_by=? WHERE id=?", (data.status, stamp, actor["id"], id))
        conn.execute("INSERT INTO action_history(action_id,original_action_id,playbook_id,original_playbook_id,from_status,to_status,changed_by,changed_by_label,changed_at,note) VALUES(?,?,?,?,?,?,?,?,?,?)", (id, id, action["playbook_id"], action["playbook_id"], action["status"], data.status, actor["id"], actor["username"], stamp, data.note))
        conn.execute("UPDATE playbooks SET updated_at=? WHERE id=?", (stamp, action["playbook_id"]))
        queue_audit(conn, "response_action_status_changed", actor["id"], actor["username"], related_service="playbooks", subject_id=id, description=f"Action {id}: {action['status']} -> {data.status}")
        result = row_dict(conn.execute("SELECT * FROM response_actions WHERE id=?", (id,)).fetchone())
    deliver_later(background_tasks)
    return result


@app.delete(f"{PREFIX}/playbooks/{{id}}")
def delete_playbook(id: int, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, "Security Administrator")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM playbooks WHERE id=?", (id,)).fetchone():
            error(404, "Playbook not found")
        if conn.execute("SELECT 1 FROM response_actions WHERE playbook_id=? AND status='In Progress'", (id,)).fetchone():
            error(409, "Playbook has an action in progress")
        conn.execute("DELETE FROM playbooks WHERE id=?", (id,))
        queue_audit(conn, "playbook_deleted", actor["id"], actor["username"], related_service="playbooks", subject_id=id)
    deliver_later(background_tasks)
    return {"message": "Playbook deleted; its execution history is kept"}
