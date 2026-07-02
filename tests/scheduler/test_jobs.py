from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.backend.scheduler import jobs


class TestParseReminderDt:
    def test_plain_time(self):
        result = jobs.parse_reminder_dt("2026-07-02", "18:01")
        assert result == datetime(2026, 7, 2, 18, 1)

    def test_iso_datetime_time_part(self):
        result = jobs.parse_reminder_dt("2026-07-02", "2026-06-30T18:01")
        assert result == datetime(2026, 7, 2, 18, 1)

    def test_space_separated_datetime(self):
        result = jobs.parse_reminder_dt("2026-07-02", "2026-06-30 18:01")
        assert result == datetime(2026, 7, 2, 18, 1)

    def test_truncates_seconds(self):
        result = jobs.parse_reminder_dt("2026-07-02", "18:01:59")
        assert result == datetime(2026, 7, 2, 18, 1)

    def test_malformed_time_raises_value_error(self):
        with pytest.raises(ValueError):
            jobs.parse_reminder_dt("2026-07-02", "not-a-time")

    def test_malformed_date_raises_value_error(self):
        with pytest.raises(ValueError):
            jobs.parse_reminder_dt("bad-date", "18:01")

    def test_empty_time_string_raises_value_error(self):
        with pytest.raises(ValueError):
            jobs.parse_reminder_dt("2026-07-02", "")


def _make_event(
    id=1,
    title="Test",
    type="personal",
    date="2026-07-02",
    start_time="14:00",
    end_time="15:00",
    reminder_time=None,
    status="upcoming",
    reminded_times="",
):
    return (id, title, type, date, start_time, end_time, reminder_time, status, reminded_times)


class TestScheduleEventReminders:
    def test_schedules_future_reminder_time(self):
        future = datetime.now() + timedelta(hours=2)
        event = _make_event(
            reminder_time=future.strftime("%H:%M"),
            date=future.strftime("%Y-%m-%d"),
            start_time=None,
            end_time=None,
        )

        with patch.object(jobs, "scheduler") as mock_scheduler:
            jobs.schedule_event_reminders(event)
            mock_scheduler.add_job.assert_called_once()
            _, kwargs = mock_scheduler.add_job.call_args
            assert kwargs["run_date"] == jobs.parse_reminder_dt(
                event[3], event[6]
            )

    def test_skips_past_reminder_time(self):
        past = datetime.now() - timedelta(hours=1)
        event = _make_event(
            reminder_time=past.strftime("%H:%M"),
            date=past.strftime("%Y-%m-%d"),
            start_time=None,
            end_time=None,
        )

        with patch.object(jobs, "scheduler") as mock_scheduler:
            jobs.schedule_event_reminders(event)
            mock_scheduler.add_job.assert_not_called()

    def test_falls_back_to_one_hour_before_start(self):
        start = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=3)
        event = _make_event(
            date=start.strftime("%Y-%m-%d"),
            start_time=start.strftime("%H:%M"),
            end_time=None,
            reminder_time=None,
        )

        with patch.object(jobs, "scheduler") as mock_scheduler:
            jobs.schedule_event_reminders(event)
            mock_scheduler.add_job.assert_called_once()
            run_date = mock_scheduler.add_job.call_args.kwargs["run_date"]
            assert run_date == start - timedelta(hours=1)

    def test_skips_malformed_reminder_time(self):
        event = _make_event(reminder_time="bad", start_time=None, end_time=None)

        with patch.object(jobs, "scheduler") as mock_scheduler:
            jobs.schedule_event_reminders(event)
            mock_scheduler.add_job.assert_not_called()

    def test_skips_malformed_start_time(self):
        event = _make_event(start_time="bad", reminder_time=None)

        with patch.object(jobs, "scheduler") as mock_scheduler:
            jobs.schedule_event_reminders(event)
            mock_scheduler.add_job.assert_not_called()

    def test_no_times_does_not_schedule(self):
        event = _make_event(start_time=None, end_time=None, reminder_time=None)

        with patch.object(jobs, "scheduler") as mock_scheduler:
            jobs.schedule_event_reminders(event)
            mock_scheduler.add_job.assert_not_called()

    def test_skips_if_already_reminded_at_same_datetime(self):
        future = datetime.now() + timedelta(hours=2)
        reminder_dt = jobs.parse_reminder_dt(
            future.strftime("%Y-%m-%d"), future.strftime("%H:%M")
        )
        event = _make_event(
            date=future.strftime("%Y-%m-%d"),
            start_time=None,
            end_time=None,
            reminder_time=future.strftime("%H:%M"),
            reminded_times=str(reminder_dt),
        )

        with patch.object(jobs, "scheduler") as mock_scheduler:
            jobs.schedule_event_reminders(event)
            mock_scheduler.add_job.assert_not_called()


class TestMarkCompletedEvents:
    def test_marks_ended_events_completed(self, events_db):
        today = datetime.now().strftime("%Y-%m-%d")
        past_time = (datetime.now() - timedelta(hours=1)).strftime("%H:%M")
        events_db.create_event("Ended", "personal", today, "08:00", past_time, None)
        event_id = events_db.get_upcoming_events("upcoming")[0][0]

        jobs.mark_completed_events()

        updated = events_db.get_upcoming_events("completed")
        assert any(e[0] == event_id for e in updated)

    def test_marks_reminder_only_event_after_reminder_passed(self, events_db):
        past = datetime.now() - timedelta(minutes=30)
        events_db.create_event(
            "Reminder Only",
            "important",
            past.strftime("%Y-%m-%d"),
            None,
            None,
            past.strftime("%H:%M"),
        )
        event_id = events_db.get_upcoming_events("upcoming")[0][0]

        jobs.mark_completed_events()

        statuses = [
            e[7] for e in events_db.get_upcoming_events("upcoming") + events_db.get_upcoming_events("completed")
        ]
        completed = events_db.get_upcoming_events("completed")
        assert any(e[0] == event_id for e in completed)

    def test_marks_date_only_event_after_end_of_day(self, events_db):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        events_db.create_event("All Day Yesterday", "personal", yesterday, None, None, None)
        event_id = events_db.get_upcoming_events("upcoming")[0][0]

        jobs.mark_completed_events()

        completed = events_db.get_upcoming_events("completed")
        assert any(e[0] == event_id for e in completed)

    def test_does_not_mark_future_reminder_only_event(self, events_db):
        future = datetime.now() + timedelta(hours=2)
        events_db.create_event(
            "Future Reminder",
            "important",
            future.strftime("%Y-%m-%d"),
            None,
            None,
            future.strftime("%H:%M"),
        )
        event_id = events_db.get_upcoming_events("upcoming")[0][0]

        jobs.mark_completed_events()

        still_upcoming = events_db.get_upcoming_events("upcoming")
        assert any(e[0] == event_id for e in still_upcoming)

    def test_skips_bad_reminder_time_during_completion_check(self, events_db):
        events_db.create_event(
            "Bad Reminder",
            "personal",
            "2026-07-01",
            None,
            None,
            "not-a-time",
        )

        jobs.mark_completed_events()

        assert len(events_db.get_upcoming_events("upcoming")) == 1
