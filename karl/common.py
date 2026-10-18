"""Shared helpers for Karl Khouri's services; authentication and the database come from the agreed joey.common contract."""
import os
from datetime import datetime, time as day_time, timezone
from pathlib import Path

from joey import common as shared

PREFIX = "/api/Karl-Khouri"
SEVERITIES = ("Low", "Medium", "High", "Critical")


def init_db():
    shared.init_db()
    with shared.db() as conn:
        conn.executescript((Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))


def audit_secret():
    value = os.getenv("AUDIT_SERVICE_AUTH_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("AUDIT_SERVICE_AUTH_SECRET must contain at least 32 characters")
    if value == os.getenv("SERVICE_AUTH_SECRET"):
        raise RuntimeError("AUDIT_SERVICE_AUTH_SECRET must differ from SERVICE_AUTH_SECRET")
    return value


def parse_time(value, field, end_of_day=False):
    """Parse an ISO date or datetime into an aware UTC datetime; a bare end date covers the whole day."""
    try:
        if len(value) == 10:
            parsed = datetime.combine(datetime.fromisoformat(value).date(), day_time.max if end_of_day else day_time.min)
        else:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        shared.error(422, f"{field} must be an ISO-8601 date or datetime")
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def date_range(start_date, end_date):
    start = parse_time(start_date, "start_date") if start_date else None
    end = parse_time(end_date, "end_date", end_of_day=True) if end_date else None
    if start and end and start > end:
        shared.error(422, "start_date must not be after end_date")
    return start, end


def stored_time(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
