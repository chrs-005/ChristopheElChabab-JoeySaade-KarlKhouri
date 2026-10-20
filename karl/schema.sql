-- Karl Khouri: Security Audit Logging, Security Playbook and Response Automation.
-- Applied after joey/schema.sql because users(id) is referenced. Reports store no tables.
-- AUTOINCREMENT: a deleted log, playbook or action ID is never handed out again, because audit subjects,
-- execution history and notification event IDs keep referring to it.
CREATE TABLE IF NOT EXISTS audit_logs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
 actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL, original_actor_user_id INTEGER, actor_label TEXT,
 action TEXT NOT NULL, description TEXT NOT NULL,
 severity TEXT NOT NULL CHECK(severity IN ('Information','Warning','Error','Critical')),
 related_service TEXT NOT NULL, subject_id TEXT, occurred_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
 source TEXT NOT NULL CHECK(source IN ('service','user','audit'))
);
CREATE INDEX IF NOT EXISTS audit_logs_actor ON audit_logs(original_actor_user_id);
CREATE INDEX IF NOT EXISTS audit_logs_occurred ON audit_logs(occurred_at);
-- Only the FK's ON DELETE SET NULL may touch a stored entry; content is otherwise immutable.
CREATE TRIGGER IF NOT EXISTS audit_logs_immutable BEFORE UPDATE ON audit_logs
WHEN NOT (NEW.actor_user_id IS NULL AND NEW.id IS OLD.id AND NEW.event_id IS OLD.event_id AND NEW.original_actor_user_id IS OLD.original_actor_user_id
 AND NEW.actor_label IS OLD.actor_label AND NEW.action IS OLD.action AND NEW.description IS OLD.description AND NEW.severity IS OLD.severity
 AND NEW.related_service IS OLD.related_service AND NEW.subject_id IS OLD.subject_id AND NEW.occurred_at IS OLD.occurred_at
 AND NEW.recorded_at IS OLD.recorded_at AND NEW.source IS OLD.source)
BEGIN SELECT RAISE(ABORT, 'Audit log entries are immutable'); END;
CREATE TABLE IF NOT EXISTS playbooks (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL COLLATE NOCASE UNIQUE, description TEXT NOT NULL,
 category TEXT NOT NULL CHECK(category IN ('Malware','Phishing','Ransomware','Unauthorized Access','Data Breach','Denial of Service','Insider Threat','Vulnerability Remediation','Other')),
 severity TEXT NOT NULL CHECK(severity IN ('Low','Medium','High','Critical')),
 created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS response_actions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, playbook_id INTEGER NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
 step_order INTEGER NOT NULL CHECK(step_order >= 1), title TEXT NOT NULL, description TEXT NOT NULL,
 assigned_to INTEGER REFERENCES users(id) ON DELETE RESTRICT,
 status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','In Progress','Completed')),
 created_at TEXT NOT NULL, started_at TEXT, completed_at TEXT, completed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
 UNIQUE(playbook_id, step_order)
);
CREATE TABLE IF NOT EXISTS action_history (
 id INTEGER PRIMARY KEY, action_id INTEGER REFERENCES response_actions(id) ON DELETE SET NULL, original_action_id INTEGER NOT NULL,
 playbook_id INTEGER REFERENCES playbooks(id) ON DELETE SET NULL, original_playbook_id INTEGER NOT NULL,
 from_status TEXT, to_status TEXT NOT NULL, changed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
 changed_by_label TEXT NOT NULL, changed_at TEXT NOT NULL, note TEXT
);
