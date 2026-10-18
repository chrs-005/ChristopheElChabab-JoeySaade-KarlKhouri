from typing import Literal

from fastapi import BackgroundTasks, Depends
from pydantic import Field

from joey.common import db, error, now, require_role, row_dict
from .common import ADMIN, ANALYST, AUDITOR, EMPLOYEE, PREFIX, Input, Severity, alert_admins, application, asset_exists, changed, current_user, dispatch, find, notify, transition

STATES = ('Open', 'Under Investigation', 'Mitigated', 'Resolved', 'Closed')
IncidentStatus = Literal['Open', 'Under Investigation', 'Mitigated', 'Resolved', 'Closed']


class IncidentCreate(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    category: str = Field(min_length=1, max_length=100)
    severity: Severity
    reporter_id: int = Field(gt=0)
    asset_id: int = Field(gt=0)


class Assignment(Input):
    analyst_id: int = Field(gt=0)


class StatusUpdate(Input):
    status: IncidentStatus


class NoteCreate(Input):
    content: str = Field(min_length=1, max_length=5000)


class NoteRecord(NoteCreate):
    id: int
    incident_id: int
    analyst_id: int
    created_at: str


class IncidentRecord(IncidentCreate):
    id: int
    assigned_to: int | None
    status: IncidentStatus
    created_at: str
    updated_at: str
    resolution_date: str | None


class IncidentDetail(IncidentRecord):
    notes: list[NoteRecord]


app = application('Incident Management')


def access(actor, incident, modify=False):
    if modify:
        require_role(actor, ADMIN, ANALYST)
    if actor['role'] == ANALYST and incident['assigned_to'] != actor['id']:
        error(403, 'Incident is not assigned to this analyst')
    if actor['role'] == EMPLOYEE and incident['reporter_id'] != actor['id']:
        error(403, 'Incident belongs to another reporter')


def detail(conn, id, actor):
    incident = find(conn, 'incidents', id, 'Incident')
    access(actor, incident)
    incident['notes'] = [row_dict(row) for row in conn.execute('SELECT * FROM investigation_notes WHERE incident_id=? ORDER BY id', (id,))] if actor['role'] != EMPLOYEE else []
    return incident


@app.post(f'{PREFIX}/incidents', status_code=201, response_model=IncidentDetail,
          summary='Create Incident', description='Administrator or employee reports an incident with severity, reporter and affected asset. Employees must report under their own identity; records begin Open.')
def create_incident(data: IncidentCreate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN, EMPLOYEE)
    if actor['role'] == EMPLOYEE and data.reporter_id != actor['id']:
        error(403, 'Cannot report an incident as another user')
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        asset_exists(conn, data.asset_id)
        if not conn.execute("SELECT 1 FROM users WHERE id=? AND status='Active'", (data.reporter_id,)).fetchone():
            error(422, 'Reporter does not exist or is not active')
        stamp = now()
        id = conn.execute('INSERT INTO incidents(title,description,category,severity,reporter_id,asset_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                          (data.title, data.description, data.category, data.severity, data.reporter_id, data.asset_id, stamp, stamp)).lastrowid
        changed(conn, 'incidents', 'incident_created', actor, id)
        alert_admins(conn, 'Security incident reported', f'Incident {id}: {data.title}', 'Security Alert', data.severity)
        result = detail(conn, id, actor)
    dispatch(background_tasks)
    return result


@app.get(f'{PREFIX}/incidents', response_model=list[IncidentRecord],
         summary='Retrieve All Incidents', description='Administrator or auditor sees all incidents. To support the role summary, analysts receive only assigned incidents and employees only their own submitted incidents; neither can retrieve the full organization list.')
def list_incidents(actor=Depends(current_user)):
    require_role(actor, ADMIN, AUDITOR, ANALYST, EMPLOYEE)
    where, args = '', ()
    if actor['role'] == ANALYST:
        where, args = ' WHERE assigned_to=?', (actor['id'],)
    elif actor['role'] == EMPLOYEE:
        where, args = ' WHERE reporter_id=?', (actor['id'],)
    with db() as conn:
        return [row_dict(row) for row in conn.execute('SELECT * FROM incidents' + where + ' ORDER BY id', args)]


@app.get(f'{PREFIX}/incidents/{{id}}', response_model=IncidentDetail,
         summary='Retrieve Specific Incident', description='Administrator or auditor reads an incident. Analysts must be assigned and employees must be its reporter. Staff responses include linked investigation notes; employees receive no confidential note content.')
def get_incident(id: int, actor=Depends(current_user)):
    with db() as conn:
        return detail(conn, id, actor)


@app.put(f'{PREFIX}/incidents/{{id}}/assign', response_model=IncidentDetail,
         summary='Assign Incident to Analyst', description='Administrator assigns an existing incident to an active Security Analyst, records an audit event and notifies the assignee.')
def assign_incident(id: int, data: Assignment, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN)
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        incident = find(conn, 'incidents', id, 'Incident')
        analyst = conn.execute('SELECT * FROM users WHERE id=?', (data.analyst_id,)).fetchone()
        if not analyst or analyst['role'] != ANALYST or analyst['status'] != 'Active':
            error(422, 'Assignee must be an active Security Analyst')
        conn.execute('UPDATE incidents SET assigned_to=?,updated_at=? WHERE id=?', (data.analyst_id, now(), id))
        changed(conn, 'incidents', 'incident_assigned', actor, id)
        notify(conn, data.analyst_id, 'Incident assigned', f'Incident {id}: {incident["title"]}', 'Incident Assignment', incident['severity'])
        result = detail(conn, id, actor)
    dispatch(background_tasks)
    return result


@app.put(f'{PREFIX}/incidents/{{id}}/status', response_model=IncidentDetail,
         summary='Update Incident Status', description='Administrator or assigned analyst progresses Open → Under Investigation → Mitigated → Resolved → Closed. Invalid jumps are rejected; resolution time is stored.')
def update_status(id: int, data: StatusUpdate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN, ANALYST)
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        incident = find(conn, 'incidents', id, 'Incident')
        access(actor, incident, modify=True)
        transition(incident['status'], data.status, STATES)
        resolution = incident['resolution_date'] or (now() if data.status in ('Resolved', 'Closed') else None)
        conn.execute('UPDATE incidents SET status=?,resolution_date=?,updated_at=? WHERE id=?', (data.status, resolution, now(), id))
        changed(conn, 'incidents', 'incident_status_changed', actor, id)
        result = detail(conn, id, actor)
    dispatch(background_tasks)
    return result


@app.post(f'{PREFIX}/incidents/{{id}}/notes', status_code=201, response_model=NoteRecord,
          summary='Add Investigation Notes', description='Administrator or assigned analyst adds a note linked to the incident. Author identity and creation time are derived by the server, never trusted from request fields.')
def add_note(id: int, data: NoteCreate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN, ANALYST)
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        incident = find(conn, 'incidents', id, 'Incident')
        access(actor, incident, modify=True)
        note_id = conn.execute('INSERT INTO investigation_notes(incident_id,analyst_id,content,created_at) VALUES(?,?,?,?)', (id, actor['id'], data.content, now())).lastrowid
        changed(conn, 'incidents', 'investigation_note_added', actor, id)
        result = find(conn, 'investigation_notes', note_id, 'Note')
    dispatch(background_tasks)
    return result
