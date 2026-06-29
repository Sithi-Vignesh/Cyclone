from app.backend.memory.sqlite_client import get_upcoming_events as fetch_events
from langchain.tools import tool
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

    if passcode.lower() != "thunder3328d":
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