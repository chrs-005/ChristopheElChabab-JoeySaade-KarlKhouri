import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, field_validator
from starlette.background import BackgroundTask

from joey.common import api_error_handler, db, error, init_db as init_shared_db, now, queue_audit, row_dict, service_secret, token_secret
from .delivery import deliver_pending
from joey.common import current_user as shared_current_user

PREFIX = '/api/Christophe-ElChabab'
ADMIN = 'Security Administrator'
ANALYST = 'Security Analyst'
AUDITOR = 'Security Auditor'
EMPLOYEE = 'Regular Employee'
Severity = Literal['Low', 'Medium', 'High', 'Critical']


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    @field_validator('asset_id', 'reporter_id', 'analyst_id', 'cvss_score', mode='before', check_fields=False)
    @classmethod
    def reject_boolean_numbers(cls, value):
        if isinstance(value, bool):
            raise ValueError('A boolean is not a valid ID or CVSS score')
        return value


class Message(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    status: Literal['error']
    message: str
    errors: list[dict[str, str]] | None = None


bearer = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    header = f'Bearer {credentials.credentials}' if credentials else None
    return shared_current_user(header)


def init_db():
    init_shared_db()
    with db() as conn:
        conn.executescript((Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8'))


@asynccontextmanager
async def lifespan(_: FastAPI):
    token_secret()
    service_secret()
    init_db()
    yield


def application(title):
    responses = {code: {'model': ErrorResponse, 'description': message} for code, message in {
        401: 'Missing, invalid, or expired credentials; unavailable account',
        403: 'Role or record ownership does not permit this operation',
        404: 'Requested resource does not exist',
        409: 'Duplicate resource or invalid lifecycle transition',
        422: 'Invalid request fields, values, or references',
    }.items()}
    app = FastAPI(title=f'Christophe ElChabab — {title}', lifespan=lifespan, responses=responses)
    api_error_handler(app)

    @app.middleware('http')
    async def deliver_denied_audit(request, call_next):
        response = await call_next(request)
        if response.status_code == 403:
            response.background = BackgroundTask(deliver_pending)
        return response

    return app


def find(conn, table, id, label):
    row = conn.execute(f'SELECT * FROM {table} WHERE id=?', (id,)).fetchone()
    if row is None:
        error(404, f'{label} not found')
    return row_dict(row)


def asset_exists(conn, asset_id):
    if not conn.execute('SELECT 1 FROM assets WHERE id=?', (asset_id,)).fetchone():
        error(422, 'Affected asset does not exist')


def changed(conn, service, action, actor, subject_id):
    queue_audit(conn, action, actor['id'], actor['username'], related_service=service, subject_id=subject_id)


def notify(conn, user_id, title, message, type, severity):
    event_id = str(uuid.uuid4())
    payload = dict(event_id=event_id, user_id=user_id, title=title, message=message, type=type, severity=severity)
    conn.execute('INSERT INTO outbox(event_id,destination,payload_json,created_at) VALUES(?,?,?,?)',
                 (event_id, 'notification', json.dumps(payload), now()))


def alert_admins(conn, title, message, type, severity):
    for user in conn.execute("SELECT id FROM users WHERE role=? AND status='Active'", (ADMIN,)):
        notify(conn, user['id'], title, message, type, severity)


def dispatch(background_tasks):
    background_tasks.add_task(deliver_pending)


def filter_records(conn, table, filters):
    selected = {key: value for key, value in filters.items() if value is not None}
    where = ' WHERE ' + ' AND '.join(f'{key}=?' for key in selected) if selected else ''
    return [row_dict(row) for row in conn.execute(f'SELECT * FROM {table}{where} ORDER BY id', list(selected.values()))]


def nonempty_update(data):
    fields = data.model_dump(exclude_unset=True)
    if not fields or any(value is None for value in fields.values()):
        error(422, 'Provide at least one non-null update field')
    return fields


def transition(current, proposed, lifecycle):
    if proposed == current:
        return
    index = lifecycle.index(current)
    if index == len(lifecycle) - 1 or proposed != lifecycle[index + 1]:
        error(409, f'Invalid status transition: {current} to {proposed}')
