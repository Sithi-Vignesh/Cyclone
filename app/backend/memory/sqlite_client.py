import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "events.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            type TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            status TEXT DEFAULT 'upcoming',
            reminded_times TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def create_event(title, type, date, start_time, end_time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (title, type, date, start_time, end_time)
        VALUES (?, ?, ?, ?, ?)
    """,(title, type, date, start_time, end_time))
    conn.commit()
    conn.close()

def get_upcoming_events(status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM events WHERE status = ?
    """,(status,))
    events = cursor.fetchall()
    conn.commit()
    conn.close()
    return events

def update_event(update_field, field_data, id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE events SET {update_field} = ? WHERE id = ?
    """,(field_data, id))
    conn.commit()
    conn.close()

def delete_event(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM events WHERE id = ?
    """,(id,))
    conn.commit()
    conn.close()