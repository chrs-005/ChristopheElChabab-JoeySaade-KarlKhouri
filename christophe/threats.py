import ipaddress
import re
import sqlite3
from typing import Literal

from fastapi import BackgroundTasks, Depends
from pydantic import Field, model_validator

from joey.common import db, error, now, require_role
from .common import ADMIN, ANALYST, AUDITOR, PREFIX, Input, Message, Severity, alert_admins, application, changed, current_user, dispatch, filter_records, find, nonempty_update

ThreatType = Literal['IP Address', 'Domain', 'File Hash', 'Malware Signature', 'Other Indicators']


def indicator(type, value):
    if type == 'IP Address':
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            raise ValueError('Invalid IP threat address')
    if type == 'Domain':
        value = (value[:-1] if value.endswith('.') else value).lower()
        if len(value) > 253 or '.' not in value or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part) for part in value.split('.')):
            raise ValueError('Invalid threat domain')
    if type == 'File Hash':
        value = value.lower()
        if len(value) not in (32, 40, 64) or not re.fullmatch(r'[0-9a-f]+', value):
            raise ValueError('File hash must be MD5, SHA-1, or SHA-256 hexadecimal')
    return value


class ThreatCreate(Input):
    type: ThreatType
    value: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1, max_length=5000)
    severity: Severity
    source: str = Field(min_length=1, max_length=300)

    @model_validator(mode='after')
    def validate_indicator(self):
        self.value = indicator(self.type, self.value)
        return self


class ThreatUpdate(Input):
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    severity: Severity | None = None
    source: str | None = Field(default=None, min_length=1, max_length=300)


class ThreatRecord(ThreatCreate):
    id: int
    created_at: str
    updated_at: str


app = application('Threat Intelligence')


@app.post(f'{PREFIX}/threats', status_code=201, response_model=ThreatRecord,
          summary='Add Threat Indicator', description='Administrator adds a unique validated threat indicator. Returns the stored threat with its ID and timestamps.')
def create_threat(data: ThreatCreate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN)
    with db() as conn:
        stamp = now()
        try:
            id = conn.execute('INSERT INTO threats(type,value,description,severity,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                              (data.type, data.value, data.description, data.severity, data.source, stamp, stamp)).lastrowid
        except sqlite3.IntegrityError:
            error(409, 'Threat indicator already exists for this type and value')
        changed(conn, 'threats', 'threat_created', actor, id)
        alert_admins(conn, 'Threat indicator added', f'Threat {id}: {data.type} {data.value}', 'Threat Alert', data.severity)
        result = find(conn, 'threats', id, 'Threat')
    dispatch(background_tasks)
    return result


@app.get(f'{PREFIX}/threats/search', response_model=list[ThreatRecord],
         summary='Search Threat Indicators', description='Administrator, analyst or auditor searches by threat type, value, severity and source. Filters are combined with AND; no matches returns an empty list.')
def search_threats(type: ThreatType | None = None, value: str | None = None, severity: Severity | None = None, source: str | None = None, actor=Depends(current_user)):
    require_role(actor, ADMIN, ANALYST, AUDITOR)
    if value is not None and type is not None:
        try:
            value = indicator(type, value.strip())
        except ValueError as exc:
            error(422, str(exc))
    with db() as conn:
        return filter_records(conn, 'threats', dict(type=type, value=value, severity=severity, source=source))


@app.get(f'{PREFIX}/threats', response_model=list[ThreatRecord],
         summary='Retrieve All Threat Indicators', description='Administrator, analyst or auditor retrieves stored threat information, severity, source and date added.')
def list_threats(actor=Depends(current_user)):
    require_role(actor, ADMIN, ANALYST, AUDITOR)
    with db() as conn:
        return filter_records(conn, 'threats', {})


@app.get(f'{PREFIX}/threats/{{id}}', response_model=ThreatRecord,
         summary='Retrieve Specific Threat Indicator', description='Administrator, analyst or auditor retrieves an existing threat by ID. An unknown ID returns 404.')
def get_threat(id: int, actor=Depends(current_user)):
    require_role(actor, ADMIN, ANALYST, AUDITOR)
    with db() as conn:
        return find(conn, 'threats', id, 'Threat')


@app.put(f'{PREFIX}/threats/{{id}}', response_model=ThreatRecord,
         summary='Update Threat Information', description='Administrator updates a nonempty subset of description, severity and source. Returns the updated threat; clients cannot replace its type or value.')
def update_threat(id: int, data: ThreatUpdate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN)
    fields = nonempty_update(data)
    with db() as conn:
        before = find(conn, 'threats', id, 'Threat')
        conn.execute('UPDATE threats SET ' + ','.join(f'{key}=?' for key in fields) + ',updated_at=? WHERE id=?', (*fields.values(), now(), id))
        changed(conn, 'threats', 'threat_updated', actor, id)
        if fields.get('severity') in ('High', 'Critical') and fields['severity'] != before['severity']:
            alert_admins(conn, 'Threat severity changed', f'Threat {id} severity is {fields["severity"]}', 'Threat Alert', fields['severity'])
        result = find(conn, 'threats', id, 'Threat')
    dispatch(background_tasks)
    return result


@app.delete(f'{PREFIX}/threats/{{id}}', response_model=Message,
            summary='Delete Threat Indicator', description='Administrator deletes an existing threat. Other roles are forbidden and the denial is audited.')
def delete_threat(id: int, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN)
    with db() as conn:
        find(conn, 'threats', id, 'Threat')
        conn.execute('DELETE FROM threats WHERE id=?', (id,))
        changed(conn, 'threats', 'threat_deleted', actor, id)
    dispatch(background_tasks)
    return {'message': 'Threat deleted'}
