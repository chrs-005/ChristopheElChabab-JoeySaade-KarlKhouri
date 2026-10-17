CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, full_name TEXT NOT NULL, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
 email TEXT NOT NULL COLLATE NOCASE UNIQUE, password_hash TEXT NOT NULL, department TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('Security Administrator','Security Analyst','Security Auditor','Regular Employee')),
 status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Inactive','Suspended')),
 created_at TEXT NOT NULL, last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS assets (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL, ip_address TEXT NOT NULL,
 operating_system TEXT, department TEXT NOT NULL, owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 location TEXT NOT NULL, criticality TEXT NOT NULL CHECK(criticality IN ('Low','Medium','High','Critical')),
 status TEXT NOT NULL CHECK(status IN ('Active','Inactive','Under Maintenance')),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset_history (
 id INTEGER PRIMARY KEY, asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL, original_asset_id INTEGER NOT NULL,
 changed_by INTEGER REFERENCES users(id) ON DELETE SET NULL, changed_at TEXT NOT NULL,
 before_json TEXT, after_json TEXT, action TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 title TEXT NOT NULL, message TEXT NOT NULL,
 type TEXT NOT NULL CHECK(type IN ('Incident Assignment','Security Alert','System Notification','Threat Alert','Vulnerability Alert')),
 severity TEXT NOT NULL CHECK(severity IN ('Low','Medium','High','Critical')),
 status TEXT NOT NULL DEFAULT 'Unread' CHECK(status IN ('Unread','Read')),
 created_at TEXT NOT NULL, read_at TEXT, event_id TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS outbox (
 id INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, destination TEXT NOT NULL,
 payload_json TEXT NOT NULL, created_at TEXT NOT NULL, delivered_at TEXT, attempts INTEGER NOT NULL DEFAULT 0,
 last_error TEXT
);
