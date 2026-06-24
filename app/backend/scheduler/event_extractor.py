from app.backend.memory.sqlite_client import create_event

def extract_event(schedule_event):
    create_event(schedule_event.title, schedule_event.type, schedule_event.date, schedule_event.start_time, schedule_event.end_time)