"""Shared helpers for Karl Khouri's services; authentication and the database come from the agreed joey.common contract."""
import os
import re
from datetime import datetime, time as day_time, timezone
from pathlib import Path

from joey import common as shared

PREFIX = "/api/Karl-Khouri"
SEVERITIES = ("Low", "Medium", "High", "Critical")


# Tables whose IDs must never be handed out again after a deletion, with the highest ID that other
# records (deletion entries, execution history, notification event IDs) already refer to.
NEVER_REUSED = {
    "audit_logs": "SELECT MAX(CAST(subject_id AS INTEGER)) FROM audit_logs WHERE action='audit_log_deleted'",
    "playbooks": "SELECT MAX(original_playbook_id) FROM action_history",
    "response_actions": "SELECT MAX(id) FROM (SELECT original_action_id AS id FROM action_history UNION ALL "
                        "SELECT CAST(substr(event_id, 17, instr(substr(event_id, 17), '-') - 1) AS INTEGER) FROM outbox WHERE event_id LIKE 'playbook-action-%')",
}


def init_db():
    shared.init_db()
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with shared.db() as conn:
        for table in NEVER_REUSED:
            existing = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if existing and "AUTOINCREMENT" not in existing["sql"].upper():
                upgrade_to_autoincrement(conn, table, schema)
        conn.executescript(schema)  # also recreates the trigger and indexes dropped by an upgrade
        for table, referenced in NEVER_REUSED.items():
            highest = max(conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}").fetchone()[0], conn.execute(referenced).fetchone()[0] or 0)
            conn.execute("INSERT INTO sqlite_sequence(name, seq) SELECT ?, 0 WHERE NOT EXISTS (SELECT 1 FROM sqlite_sequence WHERE name=?)", (table, table))
            conn.execute("UPDATE sqlite_sequence SET seq=MAX(seq, ?) WHERE name=?", (highest, table))


def upgrade_to_autoincrement(conn, table, schema):
    """Rebuild a table created before AUTOINCREMENT was added, keeping its rows (SQLite cannot alter a primary key)."""
    create = re.search(rf"CREATE TABLE IF NOT EXISTS {table} \(.*?\n\);", schema, re.S).group(0)
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.executescript(f"BEGIN; {create.replace(table, table + '_upgraded', 1)} INSERT INTO {table}_upgraded SELECT * FROM {table}; "
                       f"DROP TABLE {table}; ALTER TABLE {table}_upgraded RENAME TO {table}; COMMIT;")
    conn.execute("PRAGMA foreign_keys=ON")


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
