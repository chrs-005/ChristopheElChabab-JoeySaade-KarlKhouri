"""Actual nine-process HTTP integration check, using a disposable database."""
import os
import shutil
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing

import httpx

from live_smoke import wait_ready

PORTS = dict(users=18001, assets=18002, notifications=18003, threats=18004, vulnerabilities=18005, incidents=18006, audit_logs=18007, playbooks=18008, reports=18009)
JOEY = '/api/Joey-Saade'
CHRISTOPHE = '/api/Christophe-ElChabab'
KARL = '/api/Karl-Khouri'
PASSWORD = 'SecurePassword123'


def url(name, path):
    prefix = JOEY if name in ('users', 'assets', 'notifications') else CHRISTOPHE if name in ('threats', 'vulnerabilities', 'incidents') else KARL
    return f'http://127.0.0.1:{PORTS[name]}{prefix}{path}'


def main():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        env = dict(os.environ)
        env.update(DATABASE_PATH=str(Path(temp) / 'integration.db'), AUTH_SECRET='live-auth-secret-at-least-32-characters',
                   SERVICE_AUTH_SECRET='live-service-secret-at-least-32-characters', AUDIT_SERVICE_AUTH_SECRET='live-audit-secret-at-least-32-characters',
                   NOTIFICATION_SERVICE_URL='http://127.0.0.1:18003', AUDIT_SERVICE_URL='http://127.0.0.1:18007',
                   BOOTSTRAP_ADMIN_NAME='Christophe ElChabab', BOOTSTRAP_ADMIN_USERNAME='christophe_admin', BOOTSTRAP_ADMIN_EMAIL='christophe@example.test',
                   BOOTSTRAP_ADMIN_PASSWORD=PASSWORD, BOOTSTRAP_ADMIN_DEPARTMENT='SOC')
        for name, variable in [('users','USER_REPORT_SOURCE'), ('assets','ASSET_REPORT_SOURCE'), ('threats','THREAT_REPORT_SOURCE'), ('vulnerabilities','VULNERABILITY_REPORT_SOURCE'), ('incidents','INCIDENT_REPORT_SOURCE'), ('audit_logs','AUDIT_REPORT_SOURCE')]:
            env[variable] = url(name, '/logs' if name == 'audit_logs' else '/' + name)
        subprocess.run([sys.executable, '-c', 'from christophe.common import init_db; init_db(); from karl.common import init_db; init_db()'], env=env, check=True)
        subprocess.run([sys.executable, '-m', 'joey.bootstrap_admin'], env=env, check=True)
        processes, logs = [], []
        with httpx.Client(timeout=30) as client:
            def call(name, method, path, expected=200, headers=None, body=None):
                response = client.request(method, url(name, path), headers=headers, json=body)
                assert response.status_code == expected, (name, path, response.status_code, response.text)
                print(f'{method} {name}{path}: HTTP {response.status_code}', flush=True)
                return response.json()
            try:
                for name, port in PORTS.items():
                    package = 'joey' if name in ('users','assets','notifications') else 'christophe' if name in ('threats','vulnerabilities','incidents') else 'karl'
                    logs.append(open(Path(temp) / (name + '.log'), 'w'))
                    processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', f'{package}.{name}:app', '--host', '127.0.0.1', '--port', str(port)], env=env, stdout=logs[-1], stderr=subprocess.STDOUT))
                for port in PORTS.values():
                    wait_ready(port)
                print('All nine real HTTP services are ready', flush=True)
                def login(username):
                    token = call('users','POST','/users/login',body=dict(username_or_email=username,password=PASSWORD))['access_token']
                    return {'Authorization': 'Bearer ' + token}
                admin = login('christophe_admin')
                analyst = call('users','POST','/users/register',201,body=dict(full_name='Christophe ElChabab Analyst',username='christophe_analyst',email='analyst@example.test',password=PASSWORD,department='SOC'))
                call('users','PATCH',f'/users/{analyst["id"]}/admin',headers=admin,body=dict(role='Security Analyst'))
                analyst_h = login('christophe_analyst')
                employee = call('users','POST','/users/register',201,body=dict(full_name='Christophe ElChabab Reporter',username='christophe_reporter',email='reporter@example.test',password=PASSWORD,department='IT'))
                employee_h = login('christophe_reporter')
                call('users','POST','/users/login',401,body=dict(username_or_email='christophe_admin',password='wrong-password'))
                asset = call('assets','POST','/assets',201,headers=admin,body=dict(name='Christophe ElChabab Gateway',type='Server',ip_address='10.0.0.25',department='SOC',owner_id=analyst['id'],location='Lab',criticality='Critical'))
                for severity, type, value in [('High','Domain','phishing.example'),('Critical','IP Address','203.0.113.42')]:
                    threat = call('threats','POST','/threats',201,headers=admin,body=dict(type=type,value=value,description='Observed in investigation',severity=severity,source='SOC'))
                call('threats','POST','/threats',409,headers=admin,body=dict(type='Domain',value='PHISHING.EXAMPLE.',description='Duplicate indicator',severity='High',source='SOC'))
                call('threats','POST','/threats',422,headers=admin,body=dict(type='IP Address',value='invalid',description='Invalid indicator',severity='High',source='SOC'))
                call('threats','GET','/threats',401)
                call('threats','DELETE',f'/threats/{threat["id"]}',403,headers=employee_h)
                vuln = call('vulnerabilities','POST','/vulnerabilities',201,headers=admin,body=dict(title='Unpatched gateway',description='Scan finding',cve_id='CVE-2026-12345',cvss_score=8.1,severity='High',asset_id=asset['id'],source='Scanner'))
                incident = call('incidents','POST','/incidents',201,headers=employee_h,body=dict(title='Christophe ElChabab phishing incident',description='Suspicious email',category='Phishing',severity='High',reporter_id=employee['id'],asset_id=asset['id']))
                iid = incident['id']
                call('incidents','PUT',f'/incidents/{iid}/assign',403,headers=employee_h,body=dict(analyst_id=analyst['id']))
                call('incidents','PUT',f'/incidents/{iid}/assign',headers=admin,body=dict(analyst_id=analyst['id']))
                call('incidents','PUT',f'/incidents/{iid}/status',409,headers=analyst_h,body=dict(status='Closed'))
                call('incidents','POST',f'/incidents/{iid}/notes',201,headers=analyst_h,body=dict(content='Reviewed actual gateway logs'))
                for status in ('Under Investigation','Mitigated','Resolved','Closed'):
                    call('incidents','PUT',f'/incidents/{iid}/status',headers=analyst_h,body=dict(status=status))
                for status in ('Under Investigation','In Progress','Resolved','Closed'):
                    call('vulnerabilities','PUT',f'/vulnerabilities/{vuln["id"]}',headers=analyst_h,body=dict(status=status))
                notes = call('incidents','GET',f'/incidents/{iid}',headers=admin)['notes']
                assert len(notes) == 1 and notes[0]['analyst_id'] == analyst['id']
                # Exercise the remaining response-workflow service with this analyst.
                playbook = call('playbooks','POST','/playbooks',201,headers=admin,body=dict(name='Christophe ElChabab response',description='Contain phishing',category='Phishing',severity='High',steps=[dict(title='Block sender',description='Apply mail filter',assigned_to=analyst['id'])]))
                for status in ('In Progress','Completed'):
                    call('playbooks','PUT',f'/actions/{playbook["actions"][0]["id"]}/status',headers=analyst_h,body=dict(status=status))
                subprocess.run([sys.executable,'-m','joey.outbox'],env=env,check=True)
                subprocess.run([sys.executable,'-m','joey.outbox'],env=env,check=True)
                assigned = call('notifications','GET',f'/notifications/user/{analyst["id"]}',headers=analyst_h)
                assert any(x['type'] == 'Incident Assignment' for x in assigned)
                audit = call('audit_logs','GET','/logs',headers=admin)
                assert {'threat_created','vulnerability_created','incident_created','incident_assigned','incident_status_changed','investigation_note_added','unauthorized_access'} <= {x['action'] for x in audit}
                for name, count in [('incidents',1),('vulnerabilities',1),('threats',2)]:
                    result = call('reports','GET',f'/reports/{name}',headers=admin)
                    stored = call(name,'GET','/' + name,headers=admin)
                    assert result['total'] == len(stored) == count
                summary = call('reports','GET','/reports/summary',headers=admin)
                assert summary['complete'] is True and summary['unavailable'] == []
                with closing(sqlite3.connect(env['DATABASE_PATH'])) as conn:
                    assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
                    assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                    assert conn.execute("SELECT COUNT(*) FROM incidents WHERE status='Closed' AND resolution_date IS NOT NULL").fetchone()[0] == 1
                    assert conn.execute("SELECT COUNT(*) FROM vulnerabilities WHERE status='Closed' AND resolution_date IS NOT NULL").fetchone()[0] == 1
                print('PASS: all nine services; real API calls, permissions, validation, lifecycles, notes, audit, notifications, playbooks, report reconciliation, database integrity', flush=True)
                if '--postman' in sys.argv:
                    npx = shutil.which('npx.cmd') or shutil.which('npx')
                    if not npx:
                        raise RuntimeError('The optional collection check needs Node.js/npm (npx)')
                    args = [npx, '--yes', 'newman@6.2.1', 'run', 'postman/christophe.collection.json', '-e', 'postman/christophe.environment.template.json', '--reporters', 'cli', '--reporter-cli-no-banner', '--reporter-cli-no-console', '--timeout-request', '30000', '--bail']
                    values = dict(userUrl='http://127.0.0.1:18001', assetUrl='http://127.0.0.1:18002', notificationUrl='http://127.0.0.1:18003', threatUrl='http://127.0.0.1:18004', vulnerabilityUrl='http://127.0.0.1:18005', incidentUrl='http://127.0.0.1:18006', auditUrl='http://127.0.0.1:18007', reportUrl='http://127.0.0.1:18009', adminUsername='christophe_admin', adminPassword=PASSWORD, newUserPassword=PASSWORD)
                    for key, value in values.items():
                        args += ['--env-var', f'{key}={value}']
                    subprocess.run(args, env=env, check=True)
                    print('PASS: exported Christophe Postman collection executed by Newman against nine actual servers', flush=True)
            finally:
                for process in processes:
                    process.terminate()
                for process in processes:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                for log in logs:
                    log.close()
                tracebacks = [name for name in PORTS if 'Traceback' in (Path(temp) / (name + '.log')).read_text(encoding='utf-8',errors='replace')]
                assert not tracebacks, f'Server exceptions: {tracebacks}'


if __name__ == '__main__':
    main()
