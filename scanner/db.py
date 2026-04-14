import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "scans.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ssid TEXT NOT NULL,
            security TEXT,
            signal_dbm INTEGER,
            frequency TEXT,
            is_alert INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ssid TEXT NOT NULL,
            expected_security TEXT NOT NULL,
            actual_security TEXT NOT NULL,
            acknowledged INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def log_scan(ssid, security, signal_dbm=None, frequency=None, is_alert=False):
    conn = get_db()
    now = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        "INSERT INTO scans (timestamp, ssid, security, signal_dbm, frequency, is_alert) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (now, ssid, security, signal_dbm, frequency, 1 if is_alert else 0),
    )
    conn.commit()
    conn.close()


def log_alert(ssid, expected, actual):
    conn = get_db()
    now = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        "INSERT INTO alerts (timestamp, ssid, expected_security, actual_security) "
        "VALUES (?, ?, ?, ?)",
        (now, ssid, expected, actual),
    )
    conn.commit()
    conn.close()


def get_recent_scans(limit=500):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM scans ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_alerts(acknowledged=False):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM alerts WHERE acknowledged = ? ORDER BY id DESC",
        (1 if acknowledged else 0,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def acknowledge_alert(alert_id):
    conn = get_db()
    conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    alerts = conn.execute("SELECT COUNT(*) FROM scans WHERE is_alert = 1").fetchone()[0]
    last_scan = conn.execute(
        "SELECT * FROM scans ORDER BY id DESC LIMIT 1"
    ).fetchone()
    last_alert = conn.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # Uptime calculation - how long have scans been running
    first_scan = conn.execute(
        "SELECT timestamp FROM scans ORDER BY id ASC LIMIT 1"
    ).fetchone()

    conn.close()
    return {
        "total_scans": total,
        "total_alerts": alerts,
        "last_scan": dict(last_scan) if last_scan else None,
        "last_alert": dict(last_alert) if last_alert else None,
        "first_scan_time": first_scan[0] if first_scan else None,
    }
