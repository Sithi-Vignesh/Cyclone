from app.backend.memory.sqlite_client import get_ended_events, update_event
from app.backend.core.queue import reminder_queue

def check_in():
    events = get_ended_events()
    for event in events:
        id = event[0]
        title = event[1]
        reminder_queue.put(f"Hey Thunder! Just checking in — how did '{title}' go?")
        update_event("status", "completed", id)