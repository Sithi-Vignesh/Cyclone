from apscheduler.schedulers.background import BackgroundScheduler
from app.backend.memory.modifier import consolidate_memories
from app.backend.memory.sqlite_client import update_event, get_upcoming_events
from app.backend.core.queue import reminder_queue
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()

def start_scheduler():
    consolidate_memories()
    scheduler.start()
    events = get_upcoming_events("upcoming")
    for event in events:
        schedule_event_reminders(event)

def remind_user(event):
    message = f"⏰ Reminder: '{event[1]}' is coming up!"
    reminder_queue.put(message)
    current = event[8] if event[8] else ""
    updated = current + ("," if current else "") + datetime.now().strftime("%Y-%m-%d %H:%M")
    update_event("reminded_times", updated, event[0])

def schedule_event_reminders(event):
    if event[6]:
        reminder_dt = datetime.strptime(f"{event[3]} {event[6]}", "%Y-%m-%d %H:%M")
    elif event[4]:
        event_dt = datetime.strptime(f"{event[3]} {event[4]}", "%Y-%m-%d %H:%M")
        reminder_dt = event_dt - timedelta(hours=1)
    else:
        return

    if datetime.now() < reminder_dt and str(reminder_dt) not in (event[8] or ""):
        scheduler.add_job(remind_user, 'date', run_date=reminder_dt, args=[event])