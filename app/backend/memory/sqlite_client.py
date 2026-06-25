import sqlite3
from pathlib import Path
from datetime import datetime

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
            reminder_time TEXT,
            status TEXT DEFAULT 'upcoming',
            reminded_times TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def create_event(title, type, date, start_time, end_time, reminder_time=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (title, type, date, start_time, end_time, reminder_time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, type, date, start_time, end_time, reminder_time))
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

def event_exists(title, date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM events WHERE title = ? AND date = ?", (title, date))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_ended_events():
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM events 
        WHERE status = 'upcoming' 
        AND date = ? 
        AND end_time <= ?
    """, (today, current_time))
    events = cursor.fetchall()
    conn.close()
    return events