-- Schema do banco de dados para o Incident Response Bot

CREATE TABLE IF NOT EXISTS incidents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'P4',
    status          TEXT NOT NULL DEFAULT 'open',
    assignee        TEXT DEFAULT '',
    created_by      TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at     TIMESTAMP,
    escalation_level INTEGER DEFAULT 0,
    channel_id      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS timeline (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action      TEXT NOT NULL,
    user        TEXT NOT NULL,
    details     TEXT DEFAULT '',
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

CREATE TABLE IF NOT EXISTS oncall (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT NOT NULL,
    username   TEXT NOT NULL,
    level      INTEGER NOT NULL DEFAULT 1,
    start_date TIMESTAMP,
    end_date   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runbooks (
    name     TEXT PRIMARY KEY,
    title    TEXT NOT NULL,
    content  TEXT NOT NULL,
    keywords TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_timeline_incident ON timeline(incident_id);
CREATE INDEX IF NOT EXISTS idx_oncall_dates ON oncall(start_date, end_date);
