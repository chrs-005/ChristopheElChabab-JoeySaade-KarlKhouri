from contextlib import ExitStack
import pytest
from fastapi.testclient import TestClient

from christophe import incidents, threats, vulnerabilities
from christophe.common import ADMIN, ANALYST, AUDITOR, EMPLOYEE, PREFIX
from joey import assets, notifications, users
from joey.common import PREFIX as JOEY, create_token, db, hash_password, now
from joey.outbox import deliver_pending
from karl import audit_logs, reports
from karl.common import PREFIX as KARL

THREAT = dict(type='Domain', value='evil.example', description='Phishing indicator', severity='High', source='SOC')
VULN = dict(title='Unpatched service', description='Discovered during scan', cve_id='CVE-2026-12345', cvss_score=8.1, severity='High', asset_id=1, source='Scanner')
INCIDENT = dict(title='Christophe ElChabab phishing investigation', description='Suspicious message reported', category='Phishing', severity='High', reporter_id=4, asset_id=1)


@pytest.fixture
def system(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'test.db'))
    monkeypatch.setenv('AUTH_SECRET', 'test-auth-secret-with-at-least-32-characters')
    monkeypatch.setenv('SERVICE_AUTH_SECRET', 'test-service-secret-with-at-least-32-characters')
    monkeypatch.setenv('AUDIT_SERVICE_AUTH_SECRET', 'test-audit-secret-with-at-least-32-characters')
    monkeypatch.setattr('christophe.common.deliver_pending', lambda: None)
    monkeypatch.setattr('joey.outbox.deliver_pending', lambda: None)
    apps = dict(threats=threats.app, vulnerabilities=vulnerabilities.app, incidents=incidents.app, users=users.app, assets=assets.app, notifications=notifications.app, logs=audit_logs.app, reports=reports.app)
    with ExitStack() as stack:
        c = {name: stack.enter_context(TestClient(app)) for name, app in apps.items()}
        with db() as conn:
            for id, role in enumerate((ADMIN, ANALYST, AUDITOR, EMPLOYEE, ANALYST, EMPLOYEE), 1):
                conn.execute('INSERT INTO users(id,full_name,username,email,password_hash,department,role,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                             (id, f'User {id}', f'user{id}', f'user{id}@example.test', hash_password('SecurePassword123'), 'SOC', role, 'Active', now()))
        h = {}
        for id in range(1, 7):
            r = c['users'].post(f'{JOEY}/users/login', json=dict(username_or_email=f'user{id}', password='SecurePassword123'))
            assert r.status_code == 200
            h[id] = {'Authorization': 'Bearer ' + r.json()['access_token']}
        result = c['assets'].post(f'{JOEY}/assets', json=dict(name='Gateway', type='Server', ip_address='10.0.0.1', department='SOC', owner_id=1, location='Lab', criticality='High'), headers=h[1])
        assert result.status_code == 201
        yield c, h


def create(c, h, service, body):
    r = c[service].post(f'{PREFIX}/{service}', json=body, headers=h[1])
    assert r.status_code == 201, r.text
    return r.json()


def test_threat_crud_search_normalization_and_duplicate(system):
    c, h = system
    item = create(c, h, 'threats', dict(THREAT, value='EVIL.Example.'))
    assert item['value'] == THREAT['value']
    assert c['threats'].post(f'{PREFIX}/threats', json=THREAT, headers=h[1]).status_code == 409
    for type, value in [('IP Address', '2001:db8:0:0::1'), ('File Hash', 'A' * 64), ('Malware Signature', 'test-signature'), ('Other Indicators', 'test-indicator')]:
        create(c, h, 'threats', dict(THREAT, type=type, value=value))
    assert len(c['threats'].get(f'{PREFIX}/threats', headers=h[3]).json()) == 5
    for params in [dict(type='Domain'), dict(value='evil.example'), dict(severity='High'), dict(source='SOC'), dict(type='Domain', value='EVIL.Example.')]:
        result = c['threats'].get(f'{PREFIX}/threats/search', params=params, headers=h[2])
        assert result.status_code == 200 and result.json()
    assert c['threats'].get(f'{PREFIX}/threats/search', params=dict(source="' OR 1=1 --"), headers=h[1]).json() == []
    assert c['threats'].put(f'{PREFIX}/threats/{item["id"]}', json=dict(description='Updated', severity='Critical', source='Review'), headers=h[1]).json()['severity'] == 'Critical'
    assert c['threats'].delete(f'{PREFIX}/threats/{item["id"]}', headers=h[1]).status_code == 200
    assert c['threats'].get(f'{PREFIX}/threats/{item["id"]}', headers=h[1]).status_code == 404


@pytest.mark.parametrize('fields', [dict(type='Weather'), dict(type='IP Address', value='999.1.2.3'), dict(value='not a domain'), dict(type='File Hash', value='abc'), dict(value=' '), dict(severity='Extreme'), dict(source=' '), dict(description=''), dict(unexpected=True)])
def test_threat_validation(system, fields):
    c, h = system
    assert c['threats'].post(f'{PREFIX}/threats', json=dict(THREAT, **fields), headers=h[1]).status_code == 422


@pytest.mark.parametrize('service,body', [('threats', THREAT), ('vulnerabilities', VULN)])
def test_read_write_permissions_and_missing_resources(system, service, body):
    c, h = system
    item = create(c, h, service, body)
    path = f'{PREFIX}/{service}'
    assert c[service].get(path).status_code == 401
    assert c[service].get(path, headers={'Authorization': 'Bearer forged'}).status_code == 401
    assert c[service].get(path, headers={'Authorization': 'Bearer ' + create_token(1, ttl=-1)}).status_code == 401
    for id in (2, 3):
        assert c[service].get(path, headers=h[id]).status_code == 200
        assert c[service].get(path + f'/{item["id"]}', headers=h[id]).status_code == 200
        assert c[service].post(path, json=body, headers=h[id]).status_code == 403
        assert c[service].delete(path + f'/{item["id"]}', headers=h[id]).status_code == 403
    assert c[service].get(path, headers=h[4]).status_code == 403
    assert c[service].get(path + f'/{item["id"]}', headers=h[4]).status_code == 403
    for method, suffix, data in [('get', '/999999', None), ('put', '/999999', dict(description='Updated')), ('delete', '/999999', None)]:
        kwargs = {'headers': h[1]}
        if data is not None:
            kwargs['json'] = data
        assert getattr(c[service], method)(path + suffix, **kwargs).status_code == 404
    assert c[service].put(path + f'/{item["id"]}', json={}, headers=h[1]).status_code == 422
    assert c[service].put(path + f'/{item["id"]}', json=dict(description=None), headers=h[1]).status_code == 422
    assert c[service].put(path + f'/{item["id"]}', json=dict(description='Updated'), headers=h[3]).status_code == 403
    allowed = 200 if service == 'vulnerabilities' else 403
    assert c[service].put(path + f'/{item["id"]}', json=dict(description='Updated'), headers=h[2]).status_code == allowed


def test_vulnerability_lifecycle_references_dates_and_search(system):
    c, h = system
    item = create(c, h, 'vulnerabilities', VULN)
    path = f'{PREFIX}/vulnerabilities/{item["id"]}'
    assert c['assets'].delete(f'{JOEY}/assets/1', headers=h[1]).status_code == 409
    assert c['vulnerabilities'].put(path, json=dict(status='Resolved'), headers=h[2]).status_code == 409
    assert c['vulnerabilities'].put(path, json=dict(resolution_date=now()), headers=h[2]).status_code == 422
    for status in ('Under Investigation', 'In Progress', 'Resolved', 'Closed'):
        result = c['vulnerabilities'].put(path, json=dict(status=status), headers=h[2])
        assert result.status_code == 200, result.text
        assert result.json()['status'] == status
    assert result.json()['resolution_date'] is not None
    assert c['vulnerabilities'].put(path, json=dict(status='Open'), headers=h[1]).status_code == 409
    assert c['vulnerabilities'].put(path, json=dict(resolution_date='2000-01-01T00:00:00Z'), headers=h[1]).status_code == 422
    assert c['vulnerabilities'].put(path, json=dict(resolution_date='2999-01-01T00:00:00Z'), headers=h[1]).status_code == 422
    assert c['vulnerabilities'].put(path, json=dict(resolution_date='2026-01-01T00:00:00'), headers=h[1]).status_code == 422
    for params in [dict(cve_id=VULN['cve_id']), dict(severity='High'), dict(asset_id=1), dict(status='Closed')]:
        assert len(c['vulnerabilities'].get(f'{PREFIX}/vulnerabilities/search', params=params, headers=h[3]).json()) == 1
    assert c['vulnerabilities'].delete(path, headers=h[1]).status_code == 200


@pytest.mark.parametrize('fields', [dict(cvss_score=-1), dict(cvss_score=11), dict(cve_id='bad'), dict(asset_id=99999), dict(title=' '), dict(severity='Extreme'), dict(status='Closed'), dict(source='')])
def test_vulnerability_validation(system, fields):
    c, h = system
    assert c['vulnerabilities'].post(f'{PREFIX}/vulnerabilities', json=dict(VULN, **fields), headers=h[1]).status_code == 422


def test_incident_ownership_assignment_notes_and_complete_lifecycle(system):
    c, h = system
    path = f'{PREFIX}/incidents'
    item = c['incidents'].post(path, json=INCIDENT, headers=h[4])
    assert item.status_code == 201
    id = item.json()['id']
    for role in (2, 3):
        assert c['incidents'].post(path, json=INCIDENT, headers=h[role]).status_code == 403
    assert c['incidents'].post(path, json=dict(INCIDENT, reporter_id=6), headers=h[4]).status_code == 403
    assert c['incidents'].get(path, headers=h[6]).json() == []
    assert c['incidents'].get(path, headers=h[2]).json() == []
    assert len(c['incidents'].get(path, headers=h[4]).json()) == 1
    for role in (2, 5, 6):
        assert c['incidents'].get(path + f'/{id}', headers=h[role]).status_code == 403
    for invalid in (1, 3, 4, 99999):
        assert c['incidents'].put(path + f'/{id}/assign', json=dict(analyst_id=invalid), headers=h[1]).status_code == 422
    assert c['incidents'].put(path + f'/{id}/assign', json=dict(analyst_id=2), headers=h[4]).status_code == 403
    assert c['incidents'].put(path + f'/{id}/assign', json=dict(analyst_id=2), headers=h[1]).json()['assigned_to'] == 2
    assert len(c['incidents'].get(path, headers=h[2]).json()) == 1
    assert c['incidents'].put(path + f'/{id}/status', json=dict(status='Closed'), headers=h[2]).status_code == 409
    for role in (3, 4, 5):
        assert c['incidents'].put(path + f'/{id}/status', json=dict(status='Under Investigation'), headers=h[role]).status_code == 403
        assert c['incidents'].post(path + f'/{id}/notes', json=dict(content='Investigation'), headers=h[role]).status_code == 403
    note = c['incidents'].post(path + f'/{id}/notes', json=dict(content='Gateway logs reviewed'), headers=h[2])
    assert note.status_code == 201 and note.json()['analyst_id'] == 2
    assert c['incidents'].get(path + f'/{id}', headers=h[2]).json()['notes'][0]['id'] == note.json()['id']
    assert c['incidents'].get(path + f'/{id}', headers=h[4]).json()['notes'] == []
    for status in ('Under Investigation', 'Mitigated', 'Resolved', 'Closed'):
        result = c['incidents'].put(path + f'/{id}/status', json=dict(status=status), headers=h[2])
        assert result.status_code == 200 and result.json()['status'] == status
    assert result.json()['resolution_date'] is not None
    assert c['incidents'].get(path + '/999999', headers=h[1]).status_code == 404
    assert c['incidents'].post(path + f'/{id}/notes', json=dict(content=' '), headers=h[2]).status_code == 422


@pytest.mark.parametrize('fields', [dict(title=''), dict(description=' '), dict(category=' '), dict(severity='Extreme'), dict(asset_id=99999), dict(reporter_id=99999), dict(status='Closed')])
def test_incident_validation(system, fields):
    c, h = system
    assert c['incidents'].post(f'{PREFIX}/incidents', json=dict(INCIDENT, **fields), headers=h[1]).status_code == 422


def test_authentication_live_account_status_and_required_fields(system):
    c, h = system
    for name in ('threats', 'vulnerabilities', 'incidents'):
        assert c[name].get(f'{PREFIX}/{name}').status_code == 401
        assert c[name].post(f'{PREFIX}/{name}', json={}, headers=h[1]).status_code == 422
    with db() as conn:
        conn.execute("UPDATE users SET status='Suspended' WHERE id=1")
    assert c['threats'].get(f'{PREFIX}/threats', headers=h[1]).status_code == 401


def test_events_reach_real_peer_handlers_and_reports_use_actual_records(system, monkeypatch):
    c, h = system
    threat = create(c, h, 'threats', THREAT)
    vuln = create(c, h, 'vulnerabilities', VULN)
    incident = create(c, h, 'incidents', INCIDENT)
    assert c['incidents'].put(f'{PREFIX}/incidents/{incident["id"]}/assign', json=dict(analyst_id=2), headers=h[1]).status_code == 200
    assert c['threats'].delete(f'{PREFIX}/threats/{threat["id"]}', headers=h[4]).status_code == 403
    monkeypatch.setenv('AUDIT_SERVICE_URL', 'http://audit.test')
    monkeypatch.setenv('NOTIFICATION_SERVICE_URL', 'http://notify.test')
    def post(url, json, headers, timeout):
        base, name = ('http://audit.test', 'logs') if url.startswith('http://audit.test') else ('http://notify.test', 'notifications')
        return c[name].post(url[len(base):], json=json, headers=headers)
    monkeypatch.setattr('joey.outbox.httpx.post', post)
    deliver_pending()
    deliver_pending()
    with db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM outbox WHERE delivered_at IS NULL').fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='incident_assigned'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='unauthorized_access'").fetchone()[0] >= 1
        assert conn.execute("SELECT COUNT(*) FROM notifications WHERE type='Incident Assignment' AND user_id=2").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM notifications WHERE type IN ('Threat Alert','Vulnerability Alert','Security Alert')").fetchone()[0] == 3
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    for service in ('threats', 'vulnerabilities', 'incidents'):
        monkeypatch.setenv({'threats':'THREAT_REPORT_SOURCE', 'vulnerabilities':'VULNERABILITY_REPORT_SOURCE', 'incidents':'INCIDENT_REPORT_SOURCE'}[service], f'http://test/{service}')
    def get(url, headers):
        service = url.rsplit('/', 1)[1]
        return c[service].get(f'{PREFIX}/{service}', headers=headers)
    monkeypatch.setattr(reports, 'http_get', get)
    for service in ('threats', 'vulnerabilities', 'incidents'):
        r = c['reports'].get(f'{KARL}/reports/{service}', headers=h[3])
        assert r.status_code == 200 and r.json()['total'] == 1
