CREATE TABLE IF NOT EXISTS threats (
 id INTEGER PRIMARY KEY, type TEXT NOT NULL, value TEXT NOT NULL,
 description TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('Low','Medium','High','Critical')),
 source TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(type, value)
);
CREATE TABLE IF NOT EXISTS vulnerabilities (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, cve_id TEXT NOT NULL,
 cvss_score REAL NOT NULL CHECK(cvss_score >= 0 AND cvss_score <= 10),
 severity TEXT NOT NULL CHECK(severity IN ('Low','Medium','High','Critical')),
 asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE RESTRICT, source TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','Under Investigation','In Progress','Resolved','Closed')),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, resolution_date TEXT
);
CREATE TABLE IF NOT EXISTS incidents (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, category TEXT NOT NULL,
 severity TEXT NOT NULL CHECK(severity IN ('Low','Medium','High','Critical')),
 reporter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
 assigned_to INTEGER REFERENCES users(id) ON DELETE RESTRICT,
 status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','Under Investigation','Mitigated','Resolved','Closed')),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, resolution_date TEXT
);
CREATE TABLE IF NOT EXISTS investigation_notes (
 id INTEGER PRIMARY KEY, incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
 analyst_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 content TEXT NOT NULL, created_at TEXT NOT NULL
);
