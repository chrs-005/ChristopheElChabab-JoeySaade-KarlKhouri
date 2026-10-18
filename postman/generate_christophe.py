"""Build Christophe ElChabab's runnable requests; no simulated responses or credentials."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
PREFIX = '/api/Christophe-ElChabab'
JOEY = '/api/Joey-Saade'
KARL = '/api/Karl-Khouri'


def request(name, method, base, path, code=200, body=None, token='adminToken', save=None, prefix=PREFIX, tests=()):
    headers = [{'key': 'Authorization', 'value': 'Bearer {{' + token + '}}'}] if token else []
    req = dict(method=method, header=headers, url='{{' + base + '}}' + prefix + path,
               description=f'Christophe ElChabab — {name}. Expected HTTP {code}. Capture the actual method, URL, request body (if any), status and response; caption with your full name and what the call demonstrates.')
    if body is not None:
        req['header'].append(dict(key='Content-Type', value='application/json'))
        req['body'] = dict(mode='raw', raw=json.dumps(body, indent=2), options=dict(raw=dict(language='json')))
    script = [f"pm.test('Expected HTTP {code}', () => pm.response.to.have.status({code}));"]
    if code >= 400:
        script += ["pm.test('Clear error response', () => { const r = pm.response.json(); pm.expect(r.status).to.eql('error'); pm.expect(r.message).to.be.a('string').and.not.empty; });"]
    else:
        list_call = method == 'GET' and (path.split('?')[0] in ('/threats','/vulnerabilities','/incidents') or '/search' in path or '/notifications/user/' in path)
        script += ["pm.test('Response has expected JSON shape', () => pm.expect(pm.response.json()).to.be.an('" + ('array' if list_call else 'object') + "'));"]
        if method in ('POST','PUT') and base in ('threatUrl','vulnerabilityUrl','incidentUrl'):
            script += ["pm.test('Returned fields match the submitted request', () => { const sent = JSON.parse(pm.variables.replaceIn(pm.request.body.raw)); const got = pm.response.json(); for (const [key, value] of Object.entries(sent)) { if (Object.prototype.hasOwnProperty.call(got, key)) pm.expect(got[key]).to.eql(typeof got[key] === 'number' ? Number(value) : value); } });"]
        if method == 'PUT' and path.endswith('/assign'):
            script += ["pm.test('Assigned to requested analyst', () => pm.expect(pm.response.json().assigned_to).to.eql(Number(pm.environment.get('analystId'))));"]
        if name == 'List own submitted incidents':
            script += ["pm.test('Only own reports returned', () => pm.response.json().forEach(r => pm.expect(r.reporter_id).to.eql(Number(pm.environment.get('employeeId')))));"]
        if name == 'List assigned incidents':
            script += ["pm.test('Only assigned incidents returned', () => pm.response.json().forEach(r => pm.expect(r.assigned_to).to.eql(Number(pm.environment.get('analystId')))));"]
        if name == 'Verify assignment notification':
            script += ["pm.test('Assignment notice exists', () => pm.expect(pm.response.json().some(r => r.type === 'Incident Assignment')).to.eql(true));"]
        if name in ('Verify threat audit entries','Verify incident assignment audit','Verify permission violation audit'):
            script += ["pm.test('Real audit records exist', () => pm.expect(pm.response.json()).to.be.an('array').and.not.empty);"]
        if name == 'Verify summary report':
            script += ["pm.test('All report sources available', () => { pm.expect(pm.response.json().complete).to.eql(true); pm.expect(pm.response.json().unavailable).to.eql([]); });"]
    if save:
        for variable, field in save.items():
            script.append(f"if (pm.response.code === {code}) pm.environment.set('{variable}', pm.response.json().{field});")
    script += list(tests)
    events = [dict(listen='test', script=dict(type='text/javascript', exec=script))]
    probes = {
        'Verify assignment notification': "r.type === 'Incident Assignment' && r.message.includes('Incident ' + pm.environment.get('incidentId') + ':')",
        'Verify threat audit entries': "r.action === 'threat_created' && String(r.subject_id) === String(pm.environment.get('threatId'))",
        'Verify incident assignment audit': "r.action === 'incident_assigned' && String(r.subject_id) === String(pm.environment.get('incidentId'))",
        'Verify permission violation audit': "r.action === 'unauthorized_access' && Number(r.actor_user_id) === Number(pm.environment.get('employeeId'))",
    }
    if name in probes:
        predicate = probes[name]
        probe = [
            "const target = pm.variables.replaceIn(pm.request.url.toString());",
            "let attempt = 0;",
            "function waitForDelivery() {",
            "  pm.sendRequest({url: target, method: 'GET', header: {Authorization: 'Bearer ' + pm.environment.get('" + token + "')}}, (err, res) => {",
            "    if (err || res.code !== 200) throw new Error('Cannot verify real event delivery');",
            "    const records = res.json();",
            "    if (Array.isArray(records) && records.some(r => " + predicate + ")) return;",
            "    if (++attempt >= 40) throw new Error('Actual outbox event was not delivered within the bounded wait');",
            "    setTimeout(waitForDelivery, 500);",
            "  });",
            "}",
            "waitForDelivery();",
        ]
        events.insert(0, dict(listen='prerequest', script=dict(type='text/javascript', exec=probe)))
        script += ["pm.test('This run produced the expected event', () => pm.expect(pm.response.json().some(r => " + predicate + ")).to.eql(true));"]
    return dict(name=name, request=req, event=events)


setup = [request('Log in as administrator', 'POST','userUrl','/users/login',body=dict(username_or_email='{{adminUsername}}',password='{{adminPassword}}'),token=None,prefix=JOEY,save=dict(adminToken='access_token'),tests=["if (pm.response.code === 200) pm.environment.set('runTag', String(Date.now()));"]),
         request('Reject incorrect password','POST','userUrl','/users/login',401,body=dict(username_or_email='{{adminUsername}}',password='incorrect-password'),token=None,prefix=JOEY)]
for key, role in [('analyst','Security Analyst'),('auditor','Security Auditor'),('employee','Regular Employee'),('otherEmployee','Regular Employee')]:
    setup.append(request('Register ' + key,'POST','userUrl','/users/register',201,body=dict(full_name='Christophe ElChabab ' + key,username='cc_' + key + '_{{runTag}}',email='cc_' + key + '_{{runTag}}@example.test',password='{{newUserPassword}}',department='SOC',role='Regular Employee'),token=None,prefix=JOEY,save={key+'Id':'id',key+'Username':'username'}))
    if role != 'Regular Employee':
        setup.append(request('Assign ' + role,'PATCH','userUrl','/users/{{' + key + 'Id}}/admin',body=dict(role=role),prefix=JOEY))
    setup.append(request('Log in as ' + key,'POST','userUrl','/users/login',body=dict(username_or_email='{{' + key + 'Username}}',password='{{newUserPassword}}'),token=None,prefix=JOEY,save={key+'Token':'access_token'}))
setup.append(request('Create affected asset','POST','assetUrl','/assets',201,body=dict(name='Christophe ElChabab Gateway {{runTag}}',type='Server',ip_address='10.0.0.25',department='SOC',owner_id='{{employeeId}}',location='Lab',criticality='High'),prefix=JOEY,save=dict(assetId='id')))

threat = dict(type='Domain',value='cc-{{runTag}}.example',description='Phishing indicator investigated by Christophe ElChabab',severity='High',source='SOC')
threats = [
    request('Create domain threat','POST','threatUrl','/threats',201,body=threat,save=dict(threatId='id')),
    request('Create IP threat','POST','threatUrl','/threats',201,body=dict(threat,type='IP Address',value='198.51.100.42',severity='Critical'),save=dict(ipThreatId='id')),
    request('Reject duplicate domain','POST','threatUrl','/threats',409,body=threat),
    request('Reject invalid IP','POST','threatUrl','/threats',422,body=dict(threat,type='IP Address',value='999.1.2.3')),
    request('Reject invalid hash','POST','threatUrl','/threats',422,body=dict(threat,type='File Hash',value='not-a-hash')),
    request('Reject malformed domain terminator','POST','threatUrl','/threats',422,body=dict(threat,value='evil.example..')),
    request('Reject missing fields','POST','threatUrl','/threats',422,body={}),
    request('Reject employee reading threats','GET','threatUrl','/threats',403,token='employeeToken'),
    request('Reject missing authentication','GET','threatUrl','/threats',401,token=None),
    request('List threats as auditor','GET','threatUrl','/threats',token='auditorToken'),
    request('Get threat as analyst','GET','threatUrl','/threats/{{threatId}}',token='analystToken'),
    request('Reject unknown threat ID','GET','threatUrl','/threats/999999999',404),
    request('Search by type','GET','threatUrl','/threats/search?type=Domain',token='analystToken'),
    request('Search by severity and source','GET','threatUrl','/threats/search?severity=High&source=SOC'),
    request('Search by value','GET','threatUrl','/threats/search?value=cc-{{runTag}}.example'),
    request('Update threat','PUT','threatUrl','/threats/{{threatId}}',body=dict(description='Indicator confirmed by Christophe ElChabab',severity='Critical',source='Investigation')),
    request('Reject analyst threat update','PUT','threatUrl','/threats/{{threatId}}',403,body=dict(description='Unauthorized update'),token='analystToken'),
    request('Reject analyst threat deletion','DELETE','threatUrl','/threats/{{threatId}}',403,token='analystToken'),
]
vuln = dict(title='Christophe ElChabab gateway finding',description='Missing security update',cve_id='CVE-2026-12345',cvss_score=8.1,severity='High',asset_id='{{assetId}}',source='Scanner')
vulns = [
    request('Create vulnerability','POST','vulnerabilityUrl','/vulnerabilities',201,body=vuln,save=dict(vulnerabilityId='id')),
    request('Create second vulnerability','POST','vulnerabilityUrl','/vulnerabilities',201,body=dict(vuln,title='Christophe ElChabab secondary finding',severity='Medium',cvss_score=5.0),save=dict(secondVulnerabilityId='id')),
    request('Reject CVSS outside range','POST','vulnerabilityUrl','/vulnerabilities',422,body=dict(vuln,cvss_score=11)),
    request('Reject boolean CVSS','POST','vulnerabilityUrl','/vulnerabilities',422,body=dict(vuln,cvss_score=True)),
    request('Reject boolean vulnerability asset','POST','vulnerabilityUrl','/vulnerabilities',422,body=dict(vuln,asset_id=True)),
    request('Reject invalid CVE','POST','vulnerabilityUrl','/vulnerabilities',422,body=dict(vuln,cve_id='invalid')),
    request('Reject nonstandard CVE digits','POST','vulnerabilityUrl','/vulnerabilities',422,body=dict(vuln,cve_id='CVE-２０２６-１２３４５')),
    request('Reject unknown asset','POST','vulnerabilityUrl','/vulnerabilities',422,body=dict(vuln,asset_id=999999999)),
    request('List vulnerabilities as auditor','GET','vulnerabilityUrl','/vulnerabilities',token='auditorToken'),
    request('Get vulnerability','GET','vulnerabilityUrl','/vulnerabilities/{{vulnerabilityId}}',token='analystToken'),
    request('Reject unknown vulnerability','GET','vulnerabilityUrl','/vulnerabilities/999999999',404),
    request('Search CVE','GET','vulnerabilityUrl','/vulnerabilities/search?cve_id=CVE-2026-12345'),
    request('Search asset and severity','GET','vulnerabilityUrl','/vulnerabilities/search?asset_id={{assetId}}&severity=High'),
    request('Reject auditor update','PUT','vulnerabilityUrl','/vulnerabilities/{{vulnerabilityId}}',403,body=dict(description='Unauthorized'),token='auditorToken'),
    request('Reject lifecycle skip','PUT','vulnerabilityUrl','/vulnerabilities/{{vulnerabilityId}}',409,body=dict(status='Closed'),token='analystToken'),
    request('Update vulnerability information','PUT','vulnerabilityUrl','/vulnerabilities/{{vulnerabilityId}}',body=dict(description='Validated by Christophe ElChabab',cvss_score=9.1,severity='Critical'),token='analystToken'),
]
vulns += [request('Vulnerability -> ' + status,'PUT','vulnerabilityUrl','/vulnerabilities/{{vulnerabilityId}}',body=dict(status=status),token='analystToken') for status in ('Under Investigation','In Progress','Resolved','Closed')]
vulns += [request('Search closed vulnerabilities','GET','vulnerabilityUrl','/vulnerabilities/search?status=Closed'),request('Reject analyst deletion','DELETE','vulnerabilityUrl','/vulnerabilities/{{vulnerabilityId}}',403,token='analystToken')]
incident = dict(title='Christophe ElChabab phishing incident',description='Suspicious message received',category='Phishing',severity='High',reporter_id='{{employeeId}}',asset_id='{{assetId}}')
incidents = [
    request('Report incident as employee','POST','incidentUrl','/incidents',201,body=incident,token='employeeToken',save=dict(incidentId='id')),
    request('Create second incident','POST','incidentUrl','/incidents',201,body=dict(incident,title='Christophe ElChabab critical incident',severity='Critical'),save=dict(secondIncidentId='id')),
    request('Reject invalid severity','POST','incidentUrl','/incidents',422,body=dict(incident,severity='Extreme'),token='employeeToken'),
    request('Reject boolean reporter','POST','incidentUrl','/incidents',422,body=dict(incident,reporter_id=True)),
    request('Reject boolean incident asset','POST','incidentUrl','/incidents',422,body=dict(incident,asset_id=True)),
    request('Reject reporter impersonation','POST','incidentUrl','/incidents',403,body=dict(incident,reporter_id='{{otherEmployeeId}}'),token='employeeToken'),
    request('List incidents as administrator','GET','incidentUrl','/incidents'),
    request('List own submitted incidents','GET','incidentUrl','/incidents',token='employeeToken'),
    request('Get own incident','GET','incidentUrl','/incidents/{{incidentId}}',token='employeeToken'),
    request('Reject another employee reading incident','GET','incidentUrl','/incidents/{{incidentId}}',403,token='otherEmployeeToken'),
    request('Reject unassigned analyst reading incident','GET','incidentUrl','/incidents/{{incidentId}}',403,token='analystToken'),
    request('Reject unknown incident ID','GET','incidentUrl','/incidents/999999999',404),
    request('Reject employee assignment','PUT','incidentUrl','/incidents/{{incidentId}}/assign',403,body=dict(analyst_id='{{analystId}}'),token='employeeToken'),
    request('Reject nonanalyst assignee','PUT','incidentUrl','/incidents/{{incidentId}}/assign',422,body=dict(analyst_id='{{employeeId}}')),
    request('Assign incident to analyst','PUT','incidentUrl','/incidents/{{incidentId}}/assign',body=dict(analyst_id='{{analystId}}')),
    request('List assigned incidents','GET','incidentUrl','/incidents',token='analystToken'),
    request('Reject incident lifecycle skip','PUT','incidentUrl','/incidents/{{incidentId}}/status',409,body=dict(status='Closed'),token='analystToken'),
    request('Reject employee changing status','PUT','incidentUrl','/incidents/{{incidentId}}/status',403,body=dict(status='Under Investigation'),token='employeeToken'),
    request('Add investigation note','POST','incidentUrl','/incidents/{{incidentId}}/notes',201,body=dict(content='Christophe ElChabab reviewed gateway logs and identified phishing'),token='analystToken'),
    request('Reject empty note','POST','incidentUrl','/incidents/{{incidentId}}/notes',422,body=dict(content=' '),token='analystToken'),
    request('Retrieve incident with notes','GET','incidentUrl','/incidents/{{incidentId}}',token='analystToken'),
]
incidents += [request('Incident -> ' + status,'PUT','incidentUrl','/incidents/{{incidentId}}/status',body=dict(status=status),token='analystToken') for status in ('Under Investigation','Mitigated','Resolved','Closed')]
integrations = [
    request('Verify assignment notification','GET','notificationUrl','/notifications/user/{{analystId}}',token='analystToken',prefix=JOEY),
    request('Verify threat audit entries','GET','auditUrl','/logs/search?related_service=threats',prefix=KARL),
    request('Verify incident assignment audit','GET','auditUrl','/logs/search?action=incident_assigned',prefix=KARL),
    request('Verify permission violation audit','GET','auditUrl','/logs/search?action=unauthorized_access',prefix=KARL),
]
integrations += [request('Verify ' + name + ' report','GET','reportUrl','/reports/' + name,prefix=KARL) for name in ('threats','vulnerabilities','incidents','summary')]
cleanup = [request('Delete domain threat','DELETE','threatUrl','/threats/{{threatId}}'),request('Confirm deleted threat','GET','threatUrl','/threats/{{threatId}}',404),request('Delete IP threat','DELETE','threatUrl','/threats/{{ipThreatId}}'),request('Delete vulnerability','DELETE','vulnerabilityUrl','/vulnerabilities/{{vulnerabilityId}}'),request('Confirm deleted vulnerability','GET','vulnerabilityUrl','/vulnerabilities/{{vulnerabilityId}}',404),request('Delete second vulnerability','DELETE','vulnerabilityUrl','/vulnerabilities/{{secondVulnerabilityId}}')]
collection = dict(info=dict(name='Sprint I — Christophe ElChabab services',schema='https://schema.getpostman.com/json/collection/v2.1.0/collection.json',description='Run folders in order against your own system. Fill administrator credentials and newUserPassword locally. Setup creates role accounts and an asset through Joey APIs. Threats/vulnerabilities/incidents are Christophe ElChabab routes; integration calls verify Karl/Joey services. No saved response is fabricated. Capture actual screenshots before Cleanup.'),item=[dict(name=name,item=items) for name,items in [('01 Setup',setup),('02 Threat Intelligence',threats),('03 Vulnerability Management',vulns),('04 Incident Management',incidents),('05 Peer integration',integrations),('06 Cleanup',cleanup)]])
values = dict(userUrl='http://127.0.0.1:8001',assetUrl='http://127.0.0.1:8002',notificationUrl='http://127.0.0.1:8003',threatUrl='http://127.0.0.1:8004',vulnerabilityUrl='http://127.0.0.1:8005',incidentUrl='http://127.0.0.1:8006',auditUrl='http://127.0.0.1:8007',reportUrl='http://127.0.0.1:8009',adminUsername='',adminPassword='',newUserPassword='')
for key in ('adminToken','analystToken','auditorToken','employeeToken','otherEmployeeToken','analystId','auditorId','employeeId','otherEmployeeId','analystUsername','auditorUsername','employeeUsername','otherEmployeeUsername','assetId','threatId','ipThreatId','vulnerabilityId','secondVulnerabilityId','incidentId','secondIncidentId','runTag'):
    values[key] = ''
environment = dict(name='Christophe ElChabab local template',values=[dict(key=key,value=value,enabled=True,type='secret' if 'Password' in key or 'Token' in key else 'default') for key,value in values.items()],_postman_variable_scope='environment')
(ROOT / 'christophe.collection.json').write_text(json.dumps(collection,indent=2) + '\n',encoding='utf-8')
(ROOT / 'christophe.environment.template.json').write_text(json.dumps(environment,indent=2) + '\n',encoding='utf-8')
