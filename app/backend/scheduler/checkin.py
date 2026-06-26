from app.backend.memory.sqlite_client import get_ended_events, update_event
from app.backend.core.queue import reminder_queue

def check_in():
    events = get_ended_events()
    for event in events:
        id = event[0]
        reminder_queue.put(f"Thunder just finished '{event[1]}' ({event[2]}) on {event[3]} from {event[4]} to {event[5]}. Naturally ask how it went in your tone.")
        update_event("status", "completed", id)