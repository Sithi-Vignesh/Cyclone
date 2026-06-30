import sqlite3
from pathlib import Path
from datetime import datetime
from app.backend.memory.sqlite_client import get_events_by_type

DB_PATH = Path(__file__).parent.parent / "data" / "mood_log.db"

def init_mood_log():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mood_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            message TEXT,
            sentiment_score REAL
        )
    """)
    conn.commit()
    conn.close()

def log_mood(message: str, score: float):
    now = datetime.now()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mood_log (date, time, message, sentiment_score) VALUES (?, ?, ?, ?)",
        (now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), message, score)
    )
    conn.commit()
    conn.close()

def get_mood_trend(days: int = 7):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date, time, message, sentiment_score FROM mood_log WHERE date >= date('now', ?)",
        (f"-{days} days",)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None, []

    scores = [row[3] for row in rows]
    average = sum(scores) / len(scores)
    return average, rows


def get_mood_before_events(event_type="college", days_before=3):
    events = get_events_by_type(event_type)
    if not events:
        return []

    results = []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for event in events:
        title, date = event[1], event[3]
        cursor.execute(
            "SELECT AVG(sentiment_score) FROM mood_log WHERE date BETWEEN date(?, ?) AND date(?)",
            (date, f"-{days_before} days", date)
        )
        avg = cursor.fetchone()[0]
        results.append((title, date, avg))
    conn.close()
    return results


init_mood_log()