from app.backend.memory.sqlite_client import create_event, get_upcoming_events, event_exists
from app.backend.scheduler.jobs import schedule_event_reminders

def extract_event(schedule_event):
    if event_exists(schedule_event.title, schedule_event.date):
        return
    create_event(schedule_event.title, schedule_event.type, schedule_event.date, schedule_event.start_time, schedule_event.end_time, schedule_event.reminder_time)
    events = get_upcoming_events("upcoming")
    latest = events[-1]
    schedule_event_reminders(latest)