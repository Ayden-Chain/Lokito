"""Local, unmoderated reports: never update OSM facts or pretend they are verified."""
import sqlite3
from datetime import datetime, timezone

from facility_finder.ingest import ROOT

DB_PATH = ROOT / "data" / "community.sqlite3"


def connect(path=DB_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS contributors (
            contributor_id TEXT PRIMARY KEY,
            display_name TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility_id TEXT NOT NULL,
            contributor_id TEXT REFERENCES contributors(contributor_id),
            submitted_at TEXT NOT NULL,
            available TEXT NOT NULL CHECK(available IN ('yes','no','unknown')),
            cleanliness INTEGER CHECK(cleanliness BETWEEN 1 AND 5),
            issue TEXT NOT NULL DEFAULT '',
            moderation_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(moderation_status IN ('pending','accepted','rejected')),
            reviewed_at TEXT,
            reviewed_by TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_reports_facility ON reports(facility_id);
        CREATE VIEW IF NOT EXISTS contributor_counts AS
            SELECT contributor_id, COUNT(*) AS contribution_count
            FROM reports WHERE contributor_id IS NOT NULL GROUP BY contributor_id;
        CREATE VIEW IF NOT EXISTS verified_facilities AS
            SELECT facility_id, MAX(reviewed_at) AS last_verified_at
            FROM reports WHERE moderation_status = 'accepted' GROUP BY facility_id;
    """)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def add_report(facility_id, valid_ids, available, cleanliness=None, issue="", path=DB_PATH):
    if facility_id not in valid_ids:
        raise ValueError("Unknown facility ID")
    if available not in ("yes", "no", "unknown"):
        raise ValueError("Availability must be yes, no or unknown")
    if cleanliness is not None and (type(cleanliness) is not int or not 1 <= cleanliness <= 5):
        raise ValueError("Cleanliness must be 1–5 or unknown")
    if not isinstance(issue, str) or len(issue.strip()) > 1000:
        raise ValueError("Issue must be at most 1,000 characters")
    conn = connect(path)
    try:
        with conn:
            cur = conn.execute("""INSERT INTO reports
                (facility_id, submitted_at, available, cleanliness, issue) VALUES (?, ?, ?, ?, ?)""",
                (facility_id, datetime.now(timezone.utc).isoformat(), available, cleanliness, issue.strip()))
            return cur.lastrowid
    finally:
        conn.close()


def list_reports(facility_id, path=DB_PATH):
    conn = connect(path)
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM reports WHERE facility_id=? ORDER BY report_id DESC LIMIT 20", (facility_id,))]
    finally:
        conn.close()
