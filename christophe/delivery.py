"""Deliver the existing outbox using one HTTP client and one worker per process."""
import json
import os
from threading import Lock

import httpx

from joey.common import PREFIX as NOTIFICATION_PREFIX, db, now, service_secret

_guard = Lock()
_running = False
_requested = False


def make_client():
    return httpx.Client(timeout=3)


def deliver_batch(client):
    with db() as conn:
        events = conn.execute("SELECT * FROM outbox WHERE delivered_at IS NULL ORDER BY CASE destination WHEN 'notification' THEN 0 ELSE 1 END, id LIMIT 100").fetchall()
    delivered = 0
    for event in events:
        with db() as conn:
            pending = conn.execute('SELECT delivered_at FROM outbox WHERE id=?', (event['id'],)).fetchone()
        if not pending or pending['delivered_at'] is not None:
            continue
        if event['destination'] == 'notification':
            base = os.getenv('NOTIFICATION_SERVICE_URL', 'http://127.0.0.1:8003')
            prefix, path, key = NOTIFICATION_PREFIX, '/notifications', service_secret()
        elif event['destination'] == 'audit':
            base = os.getenv('AUDIT_SERVICE_URL', '')
            prefix, path, key = '/api/Karl-Khouri', '/logs', os.getenv('AUDIT_SERVICE_AUTH_SECRET', '')
        else:
            continue
        if not base or len(key) < 32:
            continue
        try:
            response = client.post(base.rstrip('/') + prefix + path, json=json.loads(event['payload_json']), headers={'X-Service-Key': key})
            response.raise_for_status()
            failure = None
            delivered += 1
        except httpx.HTTPError as exc:
            failure = str(exc)[:500]
        with db() as conn:
            if failure is None:
                conn.execute('UPDATE outbox SET attempts=attempts+1,delivered_at=COALESCE(delivered_at,?),last_error=NULL WHERE id=?', (now(), event['id']))
            else:
                conn.execute('UPDATE outbox SET attempts=attempts+1,last_error=? WHERE id=? AND delivered_at IS NULL', (failure, event['id']))
    return delivered


def deliver_pending():
    global _running, _requested
    with _guard:
        _requested = True
        if _running:
            return
        _running, _requested = True, False
    try:
        with make_client() as client:
            while True:
                delivered = deliver_batch(client)
                with _guard:
                    if not _requested and not delivered:
                        _running = False
                        return
                    _requested = False
    except BaseException:
        with _guard:
            _running = False
        raise
