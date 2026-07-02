from datetime import datetime, timedelta

import pytest


class TestInitDb:
    def test_creates_events_table(self, events_db, tmp_path):
        import sqlite3

        conn = sqlite3.connect(tmp_path / "events.db")
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
        ).fetchall()
        conn.close()
        assert len(tables) == 1


class TestCreateEvent:
    def test_inserts_event_with_defaults(self, events_db):
        events_db.create_event("Meeting", "college", "2026-07-10", "09:00", "10:00", "08:30")

        events = events_db.get_upcoming_events("upcoming")
        assert len(events) == 1
        event = events[0]
        assert event[1] == "Meeting"
        assert event[2] == "college"
        assert event[3] == "2026-07-10"
        assert event[4] == "09:00"
        assert event[5] == "10:00"
        assert event[6] == "08:30"
        assert event[7] == "upcoming"
        assert event[8] == ""

    def test_none_reminder_time_allowed(self, events_db):
        events_db.create_event("No Reminder", "personal", "2026-07-11", None, None, None)
        event = events_db.get_upcoming_events("upcoming")[0]
        assert event[6] is None


class TestUpdateEvent:
    def test_updates_status_field(self, events_db):
        events_db.create_event("Task", "projects", "2026-07-12", "10:00", "11:00", None)
        event_id = events_db.get_upcoming_events("upcoming")[0][0]

        events_db.update_event("status", "completed", event_id)

        assert events_db.get_upcoming_events("upcoming") == []
        assert len(events_db.get_upcoming_events("completed")) == 1

    def test_updates_reminded_times_field(self, events_db):
        events_db.create_event("Task", "projects", "2026-07-12", "10:00", "11:00", None)
        event_id = events_db.get_upcoming_events("upcoming")[0][0]

        events_db.update_event("reminded_times", "2026-07-12 09:00", event_id)

        event = events_db.get_upcoming_events("upcoming")[0]
        assert event[8] == "2026-07-12 09:00"


class TestGetUpcomingEvents:
    def test_filters_by_status(self, events_db):
        events_db.create_event("A", "personal", "2026-07-01", None, None, None)
        event_id = events_db.get_upcoming_events("upcoming")[0][0]
        events_db.update_event("status", "completed", event_id)
        events_db.create_event("B", "personal", "2026-07-02", None, None, None)

        upcoming = events_db.get_upcoming_events("upcoming")
        completed = events_db.get_upcoming_events("completed")

        assert len(upcoming) == 1
        assert upcoming[0][1] == "B"
        assert len(completed) == 1
        assert completed[0][1] == "A"

    def test_empty_when_no_matches(self, events_db):
        assert events_db.get_upcoming_events("upcoming") == []


class TestEventExists:
    def test_returns_false_when_missing(self, events_db):
        assert events_db.event_exists("Ghost", "2026-01-01") is False

    def test_returns_true_for_matching_title_and_date(self, events_db):
        events_db.create_event("Exists", "personal", "2026-05-01", None, None, None)
        assert events_db.event_exists("Exists", "2026-05-01") is True

    def test_distinguishes_same_title_different_date(self, events_db):
        events_db.create_event("Repeat", "personal", "2026-05-01", None, None, None)
        assert events_db.event_exists("Repeat", "2026-05-02") is False


class TestGetEndedEvents:
    def test_returns_events_with_end_time_passed_today(self, events_db):
        today = datetime.now().strftime("%Y-%m-%d")
        past = (datetime.now() - timedelta(minutes=5)).strftime("%H:%M")
        future = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")

        events_db.create_event("Ended", "personal", today, "08:00", past, None)
        events_db.create_event("Not Ended", "personal", today, "08:00", future, None)

        ended = events_db.get_ended_events()
        titles = [e[1] for e in ended]
        assert "Ended" in titles
        assert "Not Ended" not in titles

    def test_ignores_events_on_other_dates(self, events_db):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        events_db.create_event("Yesterday", "personal", yesterday, "08:00", "09:00", None)

        ended = events_db.get_ended_events()
        assert ended == []

    def test_ignores_events_without_end_time(self, events_db):
        today = datetime.now().strftime("%Y-%m-%d")
        events_db.create_event("No End", "personal", today, "08:00", None, None)

        ended = events_db.get_ended_events()
        assert ended == []

    def test_single_digit_hour_end_time_found_after_normalization(
        self, events_db, monkeypatch
    ):
        """End times stored via normalize_time() are zero-padded for correct string compare."""
        from app.backend.scheduler.event_extractor import normalize_time

        fixed_now = datetime(2026, 7, 2, 11, 0, 0)

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        monkeypatch.setattr(
            "app.backend.memory.sqlite_client.datetime", FixedDatetime
        )

        end_time = normalize_time("9:00")
        events_db.create_event(
            "Early End", "personal", "2026-07-02", "08:00", end_time, None
        )

        ended = events_db.get_ended_events()
        assert end_time == "09:00"
        assert any(e[1] == "Early End" for e in ended)


class TestGetEventsByType:
    def test_filters_by_type(self, events_db):
        events_db.create_event("Class", "college", "2026-07-01", None, None, None)
        events_db.create_event("Gym", "personal", "2026-07-02", None, None, None)
        events_db.create_event("Lab", "college", "2026-07-03", None, None, None)

        college = events_db.get_events_by_type("college")
        assert len(college) == 2
        assert all(e[2] == "college" for e in college)

    def test_empty_for_unknown_type(self, events_db):
        assert events_db.get_events_by_type("nonexistent") == []

    def test_empty_when_no_events(self, events_db):
        assert events_db.get_events_by_type("college") == []
