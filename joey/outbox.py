"""Retry pending service notifications from the transactional outbox."""
import json
import os

import httpx

from .common import PREFIX, db, now, service_secret


def deliver_pending():
    url = os.getenv("NOTIFICATION_SERVICE_URL", "http://127.0.0.1:8003").rstrip("/")
    with db() as conn:
        events = conn.execute("SELECT * FROM outbox WHERE delivered_at IS NULL ORDER BY CASE destination WHEN 'notification' THEN 0 ELSE 1 END, id LIMIT 100").fetchall()
    for event in events:
        target = url if event["destination"] == "notification" else os.getenv("AUDIT_SERVICE_URL", "").rstrip("/")
        if not target:
            continue
        path = "/notifications" if event["destination"] == "notification" else "/logs"
        key = service_secret() if event["destination"] == "notification" else os.getenv("AUDIT_SERVICE_AUTH_SECRET", "")
        if len(key) < 32:
            continue
        try:
            response = httpx.post(f"{target}{PREFIX if event['destination'] == 'notification' else '/api/Christophe-El-Chabab'}{path}", json=json.loads(event["payload_json"]), headers={"X-Service-Key": key}, timeout=3)
            response.raise_for_status()
            failure = None
        except (httpx.HTTPError, RuntimeError) as exc:
            failure = str(exc)[:500]
        with db() as conn:
            conn.execute("UPDATE outbox SET attempts=attempts+1, delivered_at=?, last_error=? WHERE id=?", (now() if failure is None else None, failure, event["id"]))


if __name__ == "__main__":
    deliver_pending()
