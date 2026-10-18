"""Security Reports: aggregates other services' APIs with the caller's token, never their tables."""
import os
from collections import Counter
from contextlib import asynccontextmanager

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException

from joey.common import api_error_handler, current_user, db, error, now, queue_audit, require_role, token_secret

from .common import PREFIX, date_range, init_db, parse_time

# Each source is the full list URL of an upstream API. Change the environment value when an owner changes ports or prefix.
SOURCES = {
    "assets": ("ASSET_REPORT_SOURCE", "http://127.0.0.1:8002/api/Joey-Saade/assets", "created_at"),
    "threats": ("THREAT_REPORT_SOURCE", "http://127.0.0.1:8004/api/Christophe-El-Chabab/threats", "created_at"),
    "vulnerabilities": ("VULNERABILITY_REPORT_SOURCE", "http://127.0.0.1:8005/api/Christophe-El-Chabab/vulnerabilities", "created_at"),
    "incidents": ("INCIDENT_REPORT_SOURCE", "http://127.0.0.1:8006/api/Christophe-El-Chabab/incidents", "created_at"),
    "activity": ("AUDIT_REPORT_SOURCE", "http://127.0.0.1:8007/api/Karl-Khouri/logs", "occurred_at"),
}
CLOSED_INCIDENT = ("Resolved", "Closed")
CLOSED_VULNERABILITY = ("Resolved", "Closed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    token_secret(); init_db()
    yield


app = FastAPI(title="Karl Khouri — Security Reports", lifespan=lifespan)
api_error_handler(app)


_client = None


def http_get(url, headers):
    # One reused client: building a new one per call costs about a second on Windows and starved concurrent requests.
    global _client
    if _client is None:
        _client = httpx.Client(timeout=float(os.getenv("REPORT_UPSTREAM_TIMEOUT", "5")))
    return _client.get(url, headers=headers)


def fetch(source, authorization):
    """Return the upstream record list, or raise an error naming the failed source. No default data is substituted."""
    variable, default, _ = SOURCES[source]
    url = os.getenv(variable, default)
    if not url:
        error(503, f"{source} source is not configured ({variable})")
    try:
        response = http_get(url, {"Authorization": authorization})
    except httpx.HTTPError as exc:
        error(503, f"{source} service is unavailable ({type(exc).__name__})")
    if response.status_code in (401, 403):
        error(response.status_code, f"{source} service denied access to this report")
    if response.status_code != 200:
        error(502, f"{source} service returned HTTP {response.status_code}")
    try:
        body = response.json()
    except ValueError:
        error(502, f"{source} service returned invalid JSON")
    records = body.get("items", body.get("data")) if isinstance(body, dict) else body
    if not isinstance(records, list) or not all(isinstance(x, dict) for x in records):
        error(502, f"{source} service returned an unexpected format")
    return records


def within(records, field, start, end):
    if not start and not end:
        return records
    kept = []
    for record in records:
        try:
            stamp = parse_time(str(record.get(field)), field)
        except HTTPException:
            continue  # Records without a readable timestamp cannot be placed in a requested period.
        if (not start or stamp >= start) and (not end or stamp <= end):
            kept.append(record)
    return kept


def group(records, field):
    return dict(sorted(Counter(str(r.get(field) or "Unspecified") for r in records).items()))


def build(source, records):
    total = len(records)
    if source == "assets":
        return {"total": total, "by_type": group(records, "type"), "by_criticality": group(records, "criticality"), "by_status": group(records, "status"), "by_department": group(records, "department"), "active_high_or_critical": sum(r.get("status") == "Active" and r.get("criticality") in ("High", "Critical") for r in records)}
    if source == "threats":
        return {"total": total, "by_type": group(records, "type"), "by_severity": group(records, "severity")}
    if source == "vulnerabilities":
        scores = [r["cvss_score"] for r in records if isinstance(r.get("cvss_score"), (int, float))]
        return {"total": total, "by_severity": group(records, "severity"), "by_status": group(records, "status"), "open": sum(r.get("status") not in CLOSED_VULNERABILITY for r in records), "average_cvss": round(sum(scores) / len(scores), 2) if scores else None}
    if source == "incidents":
        return {"total": total, "by_status": group(records, "status"), "by_severity": group(records, "severity"), "open": sum(r.get("status") not in CLOSED_INCIDENT for r in records), "unassigned": sum(r.get("assigned_to") is None for r in records)}
    stamps = sorted(str(r["occurred_at"]) for r in records if r.get("occurred_at"))
    return {"total_events": total, "by_action": group(records, "action"), "by_severity": group(records, "severity"), "by_service": group(records, "related_service"), "failed_logins": sum(r.get("action") == "login_failed" for r in records), "unauthorized_access": sum(r.get("action") == "unauthorized_access" for r in records), "top_actors": dict(Counter(str(r.get("actor_label") or "Unknown") for r in records).most_common(10)), "first_event_at": stamps[0] if stamps else None, "last_event_at": stamps[-1] if stamps else None}


def report(source, actor, authorization, start_date, end_date, background_tasks):
    require_role(actor, "Security Administrator", "Security Auditor")
    start, end = date_range(start_date, end_date)
    records = within(fetch(source, authorization), SOURCES[source][2], start, end)
    record_generation(actor, source, background_tasks)
    return {"report": source, "generated_at": now(), "generated_by": actor["username"], "filters": {"start_date": start_date, "end_date": end_date}, **build(source, records)}


def record_generation(actor, source, background_tasks):
    with db() as conn:
        queue_audit(conn, "report_generated", actor["id"], actor["username"], related_service="reports", subject_id=source)
    from joey.outbox import deliver_pending
    background_tasks.add_task(deliver_pending)


@app.get(f"{PREFIX}/reports/summary")
def summary(background_tasks: BackgroundTasks, start_date: str | None = None, end_date: str | None = None, actor=Depends(current_user), authorization: str | None = Header(default=None)):
    require_role(actor, "Security Administrator", "Security Auditor")
    start, end = date_range(start_date, end_date)
    sections, unavailable = {}, []
    for source, (_, _, field) in SOURCES.items():
        try:
            sections[source] = build(source, within(fetch(source, authorization), field, start, end))
        except HTTPException as exc:
            # A missing source is reported as unavailable (null), never as zero records.
            sections[source] = None
            unavailable.append({"source": source, "status": exc.status_code, "message": exc.detail})
    record_generation(actor, "summary", background_tasks)
    return {"report": "summary", "generated_at": now(), "generated_by": actor["username"], "filters": {"start_date": start_date, "end_date": end_date}, "complete": not unavailable, "unavailable": unavailable, **sections}


def route(source):
    def handler(background_tasks: BackgroundTasks, start_date: str | None = None, end_date: str | None = None, actor=Depends(current_user), authorization: str | None = Header(default=None)):
        return report(source, actor, authorization, start_date, end_date, background_tasks)
    handler.__name__ = f"{source}_report"
    return handler


for _source in ("incidents", "assets", "threats", "vulnerabilities", "activity"):
    app.get(f"{PREFIX}/reports/{_source}")(route(_source))
