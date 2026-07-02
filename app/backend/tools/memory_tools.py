from app.backend.memory.sqlite_client import get_upcoming_events as fetch_events
from app.backend.mood.mood_log import get_mood_trend
from app.backend.mood.interaction_log import get_active_hours
from langchain.tools import tool
from app.backend.mood.mood_log import get_mood_before_events
import shutil
import os
from pathlib import Path

@tool
def get_upcoming_events() -> str:
    """Returns all upcoming events and reminders scheduled for Thunder."""
    events = fetch_events("upcoming")
    if not events:
        return "No upcoming events found."
    result = []
    for event in events:
        id, title, type, date, start_time, end_time, reminder_time, status, reminded_times = event
        line = f"- [{type}] {title} on {date}"
        if start_time: line += f" at {start_time}"
        if end_time: line += f" to {end_time}"
        if reminder_time: line += f" (reminder: {reminder_time})"
        result.append(line)
    return "Upcoming events:\n" + "\n".join(result)


@tool
def delete_all_memory(passcode: str) -> str:
    """Deletes all of Thunder's memory including ChromaDB, events.db, and thunder.md. Requires a passcode."""

    if passcode != "THUNDER3328D":
        return "Incorrect passcode. Memory deletion cancelled."

    base = Path(__file__).parent.parent

    # Wipe ChromaDB
    chroma_path = base.parent.parent / "chroma_data"
    if chroma_path.exists():
        shutil.rmtree(chroma_path)

    # Wipe events.db
    db_path = base / "data" / "events.db"
    if db_path.exists():
        os.remove(db_path)

    # Wipe thunder.md
    md_path = base / "data" / "thunder.md"
    if md_path.exists():
        os.remove(md_path)

    return "All memory wiped. I've forgotten everything, THUNDER. Fresh start."

@tool
def get_mood_summary(days: int = 7) -> str:
    """Returns Thunder's average sentiment and mood entries over the given number of past days. Defaults to 7 if not specified."""
    average, rows = get_mood_trend(days=days)
    if average is None:
        return f"No mood data available for the last {days} days."
    return f"Average sentiment over last {days} days: {average:.2f}\nEntries:\n" + "\n".join(
        f"- {r[0]} {r[1]}: \"{r[2]}\" (score: {r[3]:.2f})" for r in rows
    )

@tool
def get_behavior_summary() -> str:
    """Returns Thunder's interaction patterns - which hours of the day he's most active, based on logged timestamps."""
    rows = get_active_hours()
    if not rows:
        return "No interaction data available yet."
    formatted = "\n".join(f"- {hour}:00 → {count} messages" for hour, count in rows)
    return f"Thunder's activity by hour (most active first):\n{formatted}"

@tool
def get_exam_stress_summary() -> str:
    """Returns Thunder's average mood in the days leading up to each college event, to check if he's stressed before exams."""
    results = get_mood_before_events("college")
    if not results:
        return "No college events found to check mood against."
    lines = []
    for title, date, avg in results:
        if avg is None:
            lines.append(f"- {title} ({date}): no mood data in the preceding days")
        else:
            lines.append(f"- {title} ({date}): average sentiment {avg:.2f}")
    return "Mood before college events:\n" + "\n".join(lines)