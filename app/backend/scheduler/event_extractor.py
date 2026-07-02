from app.backend.memory.sqlite_client import create_event, get_upcoming_events, event_exists
from app.backend.scheduler.jobs import schedule_event_reminders

def normalize_time(time_str):
    if not time_str:
        return None
    if 'T' in time_str:
        time_str = time_str.split('T')[1]
    elif len(time_str) > 5 and ' ' in time_str:
        time_str = time_str.split(' ')[1]

    parts = time_str.split(':')
    if len(parts) < 2:
        return time_str[:5]

    hour_part = parts[0]
    minute_part = parts[1]
    if not hour_part.isdigit() or not minute_part.isdigit():
        return time_str[:5]

    return f"{int(hour_part):02d}:{int(minute_part):02d}"

def extract_event(schedule_event):
    if event_exists(schedule_event.title, schedule_event.date):
        return
    create_event(
        schedule_event.title,
        schedule_event.type,
        schedule_event.date,
        normalize_time(schedule_event.start_time),
        normalize_time(schedule_event.end_time),
        normalize_time(schedule_event.reminder_time)
    )
    events = get_upcoming_events("upcoming")
    latest = events[-1]
    schedule_event_reminders(latest)