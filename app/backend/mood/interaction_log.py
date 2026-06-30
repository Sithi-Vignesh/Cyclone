import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "mood_log.db"

def init_interaction_log():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interaction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            hour INTEGER,
            day_of_week TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_interaction():
    now = datetime.now()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO interaction_log (date, time, hour, day_of_week) VALUES (?, ?, ?, ?)",
        (now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), now.hour, now.strftime("%A"))
    )
    conn.commit()
    conn.close()

def get_active_hours():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT hour, COUNT(*) as count FROM interaction_log GROUP BY hour ORDER BY count DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


init_interaction_log()