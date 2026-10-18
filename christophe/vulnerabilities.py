from datetime import datetime, timezone
from typing import Literal

from fastapi import BackgroundTasks, Depends
from pydantic import Field

from joey.common import db, error, now, require_role
from .common import ADMIN, ANALYST, AUDITOR, PREFIX, Input, Message, Severity, alert_admins, application, asset_exists, changed, current_user, dispatch, filter_records, find, nonempty_update, transition

STATES = ('Open', 'Under Investigation', 'In Progress', 'Resolved', 'Closed')
VulnerabilityStatus = Literal['Open', 'Under Investigation', 'In Progress', 'Resolved', 'Closed']


class VulnerabilityCreate(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    cve_id: str = Field(pattern=r'^CVE-[0-9]{4}-[0-9]{4,}$', max_length=40)
    cvss_score: float = Field(ge=0, le=10, allow_inf_nan=False)
    severity: Severity
    asset_id: int = Field(gt=0)
    source: str = Field(min_length=1, max_length=300)


class VulnerabilityUpdate(Input):
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    severity: Severity | None = None
    cvss_score: float | None = Field(default=None, ge=0, le=10, allow_inf_nan=False)
    status: VulnerabilityStatus | None = None
    resolution_date: datetime | None = None


class VulnerabilityRecord(VulnerabilityCreate):
    id: int
    status: VulnerabilityStatus
    created_at: str
    updated_at: str
    resolution_date: str | None


app = application('Vulnerability Management')


@app.post(f'{PREFIX}/vulnerabilities', status_code=201, response_model=VulnerabilityRecord,
          summary='Add New Vulnerability', description='Administrator registers a vulnerability linked to an existing asset. Validates required fields, CVE syntax, CVSS range and severity; initial status is Open.')
def create_vulnerability(data: VulnerabilityCreate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN)
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        asset_exists(conn, data.asset_id)
        stamp = now()
        id = conn.execute('INSERT INTO vulnerabilities(title,description,cve_id,cvss_score,severity,asset_id,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                          (data.title, data.description, data.cve_id, data.cvss_score, data.severity, data.asset_id, data.source, stamp, stamp)).lastrowid
        changed(conn, 'vulnerabilities', 'vulnerability_created', actor, id)
        alert_admins(conn, 'Vulnerability discovered', f'Vulnerability {id} on asset {data.asset_id}: {data.title}', 'Vulnerability Alert', data.severity)
        result = find(conn, 'vulnerabilities', id, 'Vulnerability')
    dispatch(background_tasks)
    return result


@app.get(f'{PREFIX}/vulnerabilities/search', response_model=list[VulnerabilityRecord],
         summary='Search Vulnerabilities', description='Administrator, analyst or auditor searches by CVE identifier, severity, asset and status. Filters use AND; no matches returns an empty list.')
def search_vulnerabilities(cve_id: str | None = None, severity: Severity | None = None, asset_id: int | None = None, status: VulnerabilityStatus | None = None, actor=Depends(current_user)):
    require_role(actor, ADMIN, ANALYST, AUDITOR)
    with db() as conn:
        return filter_records(conn, 'vulnerabilities', dict(cve_id=cve_id, severity=severity, asset_id=asset_id, status=status))


@app.get(f'{PREFIX}/vulnerabilities', response_model=list[VulnerabilityRecord],
         summary='Retrieve All Vulnerabilities', description='Administrator, analyst or auditor retrieves vulnerabilities with severity, affected asset and remediation status.')
def list_vulnerabilities(actor=Depends(current_user)):
    require_role(actor, ADMIN, ANALYST, AUDITOR)
    with db() as conn:
        return filter_records(conn, 'vulnerabilities', {})


@app.get(f'{PREFIX}/vulnerabilities/{{id}}', response_model=VulnerabilityRecord,
         summary='Retrieve Specific Vulnerability', description='Administrator, analyst or auditor retrieves complete vulnerability information by ID; unknown IDs return 404.')
def get_vulnerability(id: int, actor=Depends(current_user)):
    require_role(actor, ADMIN, ANALYST, AUDITOR)
    with db() as conn:
        return find(conn, 'vulnerabilities', id, 'Vulnerability')


@app.put(f'{PREFIX}/vulnerabilities/{{id}}', response_model=VulnerabilityRecord,
         summary='Update Vulnerability Information', description='Administrator or analyst updates description, severity, CVSS, status or resolution date. Enforces Open → Under Investigation → In Progress → Resolved → Closed without skipping steps.')
def update_vulnerability(id: int, data: VulnerabilityUpdate, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN, ANALYST)
    fields = nonempty_update(data)
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        before = find(conn, 'vulnerabilities', id, 'Vulnerability')
        status = fields.get('status', before['status'])
        transition(before['status'], status, STATES)
        if 'resolution_date' in fields:
            value = fields['resolution_date']
            if value.tzinfo is None:
                error(422, 'resolution_date must include a timezone')
            value = value.astimezone(timezone.utc)
            if status not in ('Resolved', 'Closed') or value < datetime.fromisoformat(before['created_at']) or value > datetime.now(timezone.utc):
                error(422, 'Resolution date must be between creation and now, on a resolved or closed vulnerability')
            fields['resolution_date'] = value.isoformat()
        elif status in ('Resolved', 'Closed') and not before['resolution_date']:
            fields['resolution_date'] = now()
        conn.execute('UPDATE vulnerabilities SET ' + ','.join(f'{key}=?' for key in fields) + ',updated_at=? WHERE id=?', (*fields.values(), now(), id))
        changed(conn, 'vulnerabilities', 'vulnerability_updated', actor, id)
        if fields.get('severity') in ('High', 'Critical') and fields['severity'] != before['severity']:
            alert_admins(conn, 'Vulnerability severity changed', f'Vulnerability {id} severity is {fields["severity"]}', 'Vulnerability Alert', fields['severity'])
        result = find(conn, 'vulnerabilities', id, 'Vulnerability')
    dispatch(background_tasks)
    return result


@app.delete(f'{PREFIX}/vulnerabilities/{{id}}', response_model=Message,
            summary='Delete Vulnerability', description='Administrator removes an existing vulnerability. Analyst, auditor and employee deletion attempts are rejected and audited.')
def delete_vulnerability(id: int, background_tasks: BackgroundTasks, actor=Depends(current_user)):
    require_role(actor, ADMIN)
    with db() as conn:
        find(conn, 'vulnerabilities', id, 'Vulnerability')
        conn.execute('DELETE FROM vulnerabilities WHERE id=?', (id,))
        changed(conn, 'vulnerabilities', 'vulnerability_deleted', actor, id)
    dispatch(background_tasks)
    return {'message': 'Vulnerability deleted'}
