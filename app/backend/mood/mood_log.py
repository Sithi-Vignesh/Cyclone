import sqlite3
from pathlib import Path
from datetime import datetime

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


init_mood_log()