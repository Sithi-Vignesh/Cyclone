from apscheduler.schedulers.background import BackgroundScheduler
from app.backend.memory.modifier import consolidate_memories
from app.backend.memory.sqlite_client import update_event, get_upcoming_events, get_ended_events
from app.backend.scheduler.checkin import check_in
from app.backend.core.queue import reminder_queue
from datetime import datetime, timedelta
from app.backend.core import state
import logging

scheduler = BackgroundScheduler()

def parse_reminder_dt(date_str, time_str):
    if 'T' in time_str:
        time_str = time_str.split('T')[1]
    elif len(time_str) > 5 and ' ' in time_str:
        time_str = time_str.split(' ')[1]
    time_str = time_str[:5]
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

def start_scheduler():
    consolidate_memories()
    scheduler.start()
    events = get_upcoming_events("upcoming")
    for event in events:
        schedule_event_reminders(event)
    scheduler.add_job(check_in, 'interval', minutes=1)
    scheduler.add_job(mark_completed_events, 'interval', minutes=1)

def remind_user(event):
    message = f"Thunder has an upcoming event: '{event[1]}' ({event[2]}) at {event[4]}. Naturally remind them about it in your tone."
    if not state.awake:
        state.awake = True
        print(f"\nCyclone: Hey Thunder! ⏰ Reminder: '{event[1]}' is coming up!")
        print("Me: ", end="", flush=True)
    else:
        reminder_queue.put(message)
    current = event[8] if event[8] else ""
    updated = current + ("," if current else "") + datetime.now().strftime("%Y-%m-%d %H:%M")
    update_event("reminded_times", updated, event[0])

def schedule_event_reminders(event):
    if event[6]:
        try:
            reminder_dt = parse_reminder_dt(event[3], event[6])
        except (ValueError, IndexError) as e:
            logging.warning(f"Skipping reminder for '{event[1]}' — malformed reminder_time '{event[6]}': {e}")
            return
    elif event[4]:
        try:
            event_dt = datetime.strptime(f"{event[3]} {event[4]}", "%Y-%m-%d %H:%M")
            reminder_dt = event_dt - timedelta(hours=1)
        except ValueError as e:
            logging.warning(f"Skipping reminder for '{event[1]}' — malformed start_time '{event[4]}': {e}")
            return
    else:
        return

    if datetime.now() < reminder_dt and str(reminder_dt) not in (event[8] or ""):
        scheduler.add_job(remind_user, 'date', run_date=reminder_dt, args=[event])

def mark_completed_events():
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    # Case 1: events with end_time passed
    ended = get_ended_events()
    for event in ended:
        update_event("status", "completed", event[0])

    # Case 2: reminder-only events (no end_time, no start_time, only reminder_time passed)
    upcoming = get_upcoming_events("upcoming")
    for event in upcoming:
        id, title, type, date, start_time, end_time, reminder_time, status, reminded_times = event
        if not start_time and not end_time and reminder_time:
            try:
                reminder_dt = parse_reminder_dt(date, reminder_time)
            except (ValueError, IndexError) as e:
                logging.warning(f"Skipping completion check for event {id} — bad reminder_time '{reminder_time}': {e}")
                continue
            if now > reminder_dt:
                update_event("status", "completed", id)

        # Case 3: no time at all — mark completed at end of that day
        if not start_time and not end_time and not reminder_time and date:
            end_of_day = datetime.strptime(f"{date} 23:59", "%Y-%m-%d %H:%M")
            if now > end_of_day:
                update_event("status", "completed", id)