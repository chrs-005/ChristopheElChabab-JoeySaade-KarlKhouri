"""Independent brief-contract and adversarial checks from the second review."""
import json
from pathlib import Path

import pytest
import httpx

from christophe import incidents, threats, vulnerabilities
from joey.common import db
from test_christophe import system, create, THREAT, VULN, INCIDENT

PREFIX = '/api/Christophe-ElChabab'


def test_exact_brief_routes_and_owner_name():
    expected = {
        'threats': {('post','/threats'),('get','/threats'),('get','/threats/{id}'),('get','/threats/search'),('put','/threats/{id}'),('delete','/threats/{id}')},
        'vulnerabilities': {('post','/vulnerabilities'),('get','/vulnerabilities'),('get','/vulnerabilities/{id}'),('put','/vulnerabilities/{id}'),('get','/vulnerabilities/search'),('delete','/vulnerabilities/{id}')},
        'incidents': {('post','/incidents'),('get','/incidents'),('get','/incidents/{id}'),('put','/incidents/{id}/assign'),('put','/incidents/{id}/status'),('post','/incidents/{id}/notes')},
    }
    for name, app in [('threats',threats.app),('vulnerabilities',vulnerabilities.app),('incidents',incidents.app)]:
        actual = {(method,path) for path, operations in app.openapi()['paths'].items() for method in operations}
        assert actual == {(method,PREFIX+suffix) for method,suffix in expected[name]}


def test_domain_with_multiple_trailing_dots_is_rejected(system):
    c,h = system
    from christophe.common import PREFIX as current_prefix
    response = c['threats'].post(current_prefix+'/threats',json=dict(THREAT,value='evil.example..'),headers=h[1])
    assert response.status_code == 422


def test_non_ascii_cve_digits_are_rejected(system):
    c,h = system
    from christophe.common import PREFIX as current_prefix
    response = c['vulnerabilities'].post(current_prefix+'/vulnerabilities',json=dict(VULN,cve_id='CVE-２０２６-１２３４５'),headers=h[1])
    assert response.status_code == 422


def test_permission_denial_triggers_outbox_delivery(system, monkeypatch):
    c,h = system
    from christophe.common import PREFIX as current_prefix
    calls = []
    monkeypatch.setattr('christophe.common.deliver_pending',lambda: calls.append('delivery'))
    response = c['threats'].get(current_prefix+'/threats',headers=h[4])
    assert response.status_code == 403
    assert calls == ['delivery']
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM outbox WHERE payload_json LIKE '%unauthorized_access%'").fetchone()[0] == 1


def test_openapi_documents_bearer_auth_outputs_and_errors():
    for app in (threats.app,vulnerabilities.app,incidents.app):
        schema = app.openapi()
        assert any(s.get('scheme') == 'bearer' for s in schema['components'].get('securitySchemes',{}).values())
        for operations in schema['paths'].values():
            for operation in operations.values():
                assert operation.get('security')
                assert operation.get('description')
                success = operation['responses'].get('200') or operation['responses'].get('201')
                assert success['content']['application/json']['schema']
                assert {'401','403','404','409','422'} <= set(operation['responses'])


def test_collection_documents_requests_and_uses_correct_prefix():
    collection = json.loads(Path('postman/christophe.collection.json').read_text(encoding='utf-8'))
    items = [item for folder in collection['item'] for item in folder['item']]
    for item in items:
        req = item['request']
        assert req['description']
        if any(x in req['url'] for x in ('{{threatUrl}}','{{vulnerabilityUrl}}','{{incidentUrl}}')):
            assert PREFIX in req['url']
    checks = '\n'.join(line for item in items for event in item['event'] for line in event['script']['exec'])
    assert 'pm.response.json()' in checks and 'to.be.an' in checks


@pytest.mark.parametrize('service,body,field', [
    ('vulnerabilities', VULN, 'cvss_score'),
    ('vulnerabilities', VULN, 'asset_id'),
    ('incidents', INCIDENT, 'reporter_id'),
    ('incidents', INCIDENT, 'asset_id'),
])
def test_booleans_are_not_valid_numbers(system, service, body, field):
    c,h = system
    result = c[service].post(f'{PREFIX}/{service}',json=dict(body,**{field:True}),headers=h[1])
    assert result.status_code == 422


@pytest.mark.parametrize('service', ['threats','vulnerabilities','incidents'])
def test_role_matrix_for_every_required_endpoint(system, service):
    c,h = system
    body = {'threats':THREAT,'vulnerabilities':VULN,'incidents':INCIDENT}[service]
    record = create(c,h,service,body)
    id = record['id']
    base = f'{PREFIX}/{service}'
    if service == 'incidents':
        assert c[service].put(base+f'/{id}/assign',json=dict(analyst_id=2),headers=h[1]).status_code == 200
        specs = [
            ('post','',body,{1,4}),('get','',None,{1,2,3,4}),('get',f'/{id}',None,{1,2,3,4}),
            ('put',f'/{id}/assign',dict(analyst_id=2),{1}),
            ('put',f'/{id}/status',dict(status='Under Investigation'),{1,2}),
            ('post',f'/{id}/notes',dict(content='Role-matrix check'),{1,2}),
        ]
    else:
        specs = [
            ('post','',dict(body,**({'value':'matrix.example'} if service=='threats' else {})),{1}),
            ('get','',None,{1,2,3}),('get',f'/{id}',None,{1,2,3}),
            ('get','/search',None,{1,2} if service=='threats' else {1,2,3}),
            ('put',f'/{id}',dict(description='Role-matrix update'),{1} if service=='threats' else {1,2}),
            ('delete',f'/{id}',None,{1}),
        ]
    for method,suffix,payload,allowed in specs:
        for role in (2,3,4,1):
            kwargs = dict(headers=h[role])
            if payload is not None:
                kwargs['json'] = payload
            response = getattr(c[service],method)(base+suffix,**kwargs)
            expected = (201 if method=='post' else 200) if role in allowed else 403
            assert response.status_code == expected, (service,method,suffix,role,response.text)
        kwargs = {} if payload is None else dict(json=payload)
        assert getattr(c[service],method)(base+suffix,**kwargs).status_code == 401


def test_incident_trusted_author_and_inactive_assignee(system):
    c,h = system
    incident = create(c,h,'incidents',INCIDENT)
    path = f'{PREFIX}/incidents/{incident["id"]}'
    with db() as conn:
        conn.execute("UPDATE users SET status='Suspended' WHERE id=2")
    assert c['incidents'].put(path+'/assign',json=dict(analyst_id=2),headers=h[1]).status_code == 422
    with db() as conn:
        conn.execute("UPDATE users SET status='Active' WHERE id=2")
    assert c['incidents'].put(path+'/assign',json=dict(analyst_id=2),headers=h[1]).status_code == 200
    assert c['incidents'].post(path+'/notes',json=dict(content='Forged author',analyst_id=1),headers=h[2]).status_code == 422
    note = c['incidents'].post(path+'/notes',json=dict(content='Actual analyst'),headers=h[2])
    assert note.status_code == 201 and note.json()['analyst_id'] == 2
    assert c['incidents'].get(path,headers=h[4]).json()['notes'] == []


def test_foreign_keys_and_persistence_cover_all_owned_tables(system):
    c,h = system
    threat = create(c,h,'threats',THREAT)
    vuln = create(c,h,'vulnerabilities',VULN)
    incident = create(c,h,'incidents',INCIDENT)
    path = f'{PREFIX}/incidents/{incident["id"]}'
    assert c['incidents'].put(path+'/assign',json=dict(analyst_id=2),headers=h[1]).status_code == 200
    note = c['incidents'].post(path+'/notes',json=dict(content='Persisted note'),headers=h[2]).json()
    with db() as conn:
        assert conn.execute('SELECT value FROM threats WHERE id=?',(threat['id'],)).fetchone()[0] == THREAT['value']
        assert conn.execute('SELECT asset_id FROM vulnerabilities WHERE id=?',(vuln['id'],)).fetchone()[0] == 1
        assert conn.execute('SELECT reporter_id,assigned_to FROM incidents WHERE id=?',(incident['id'],)).fetchone()[:] == (4,2)
        assert conn.execute('SELECT incident_id,analyst_id FROM investigation_notes WHERE id=?',(note['id'],)).fetchone()[:] == (incident['id'],2)
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []


def test_delivery_drains_notification_generated_audits_without_losing_events(system, monkeypatch):
    from christophe import delivery
    c,h = system
    create(c,h,'threats',THREAT)
    incident = create(c,h,'incidents',INCIDENT)
    assert c['incidents'].put(f'{PREFIX}/incidents/{incident["id"]}/assign',json=dict(analyst_id=2),headers=h[1]).status_code == 200
    monkeypatch.setenv('AUDIT_SERVICE_URL','http://audit.test')
    monkeypatch.setenv('NOTIFICATION_SERVICE_URL','http://notify.test')
    def handle(request):
        name = 'logs' if request.url.host == 'audit.test' else 'notifications'
        response = c[name].post(request.url.path,json=json.loads(request.content),headers=dict(request.headers))
        return httpx.Response(response.status_code,json=response.json(),request=request)
    monkeypatch.setattr(delivery,'make_client',lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    delivery.deliver_pending()
    with db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM outbox WHERE delivered_at IS NULL').fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='notification_created'").fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='incident_assigned'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM notifications WHERE type='Incident Assignment' AND user_id=2").fetchone()[0] == 1
    delivery.deliver_pending()
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='incident_assigned'").fetchone()[0] == 1


def test_delivery_failure_preserves_event_for_retry(system, monkeypatch):
    from christophe import delivery
    c,h = system
    create(c,h,'threats',THREAT)
    monkeypatch.setenv('AUDIT_SERVICE_URL','http://audit.test')
    monkeypatch.setenv('NOTIFICATION_SERVICE_URL','http://notify.test')
    def unavailable(request):
        raise httpx.ConnectError('Test service unavailable',request=request)
    monkeypatch.setattr(delivery,'make_client',lambda: httpx.Client(transport=httpx.MockTransport(unavailable)))
    delivery.deliver_pending()
    with db() as conn:
        pending = conn.execute('SELECT attempts,last_error FROM outbox WHERE delivered_at IS NULL').fetchall()
        assert pending and all(row['attempts'] == 1 and row['last_error'] for row in pending)
