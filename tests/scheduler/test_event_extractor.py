from unittest.mock import MagicMock, patch

import pytest

from app.backend.chat.schemas import ScheduleEvent
from app.backend.scheduler import event_extractor


class TestNormalizeTime:
    def test_none_returns_none(self):
        assert event_extractor.normalize_time(None) is None

    def test_empty_string_returns_none(self):
        assert event_extractor.normalize_time("") is None

    def test_plain_hh_mm_unchanged(self):
        assert event_extractor.normalize_time("18:01") == "18:01"

    def test_iso_datetime_strips_date_prefix(self):
        assert event_extractor.normalize_time("2026-06-30T18:01") == "18:01"

    def test_space_separated_datetime_strips_date(self):
        assert event_extractor.normalize_time("2026-06-30 18:01") == "18:01"

    def test_truncates_seconds_if_present(self):
        assert event_extractor.normalize_time("18:01:30") == "18:01"

    def test_short_malformed_iso_returns_partial_time(self):
        # No 'T' and len <= 5, so returned as-is truncated to 5 chars
        assert event_extractor.normalize_time("18:1") == "18:01"

    def test_iso_with_seconds(self):
        assert event_extractor.normalize_time("2026-06-30T18:01:45") == "18:01"

    def test_single_digit_minute_zero_padded(self):
        assert event_extractor.normalize_time("18:1") == "18:01"

    def test_single_digit_hour_and_minute_zero_padded(self):
        assert event_extractor.normalize_time("9:5") == "09:05"


class TestExtractEvent:
    def test_skips_when_event_already_exists(self, events_db):
        events_db.create_event("Dup", "personal", "2026-07-10", "09:00", "10:00", None)
        schedule = ScheduleEvent(
            title="Dup",
            type="personal",
            date="2026-07-10",
            start_time="09:00",
            end_time="10:00",
        )

        with patch.object(event_extractor, "schedule_event_reminders") as mock_schedule:
            event_extractor.extract_event(schedule)
            mock_schedule.assert_not_called()

        assert len(events_db.get_upcoming_events("upcoming")) == 1

    def test_creates_event_and_schedules_reminders(self, events_db):
        schedule = ScheduleEvent(
            title="New Event",
            type="projects",
            date="2026-08-01",
            start_time="2026-08-01T14:00",
            end_time="2026-08-01 15:00",
            reminder_time="2026-08-01T13:30",
        )

        with patch.object(event_extractor, "schedule_event_reminders") as mock_schedule:
            event_extractor.extract_event(schedule)

        events = events_db.get_upcoming_events("upcoming")
        assert len(events) == 1
        event = events[0]
        assert event[1] == "New Event"
        assert event[4] == "14:00"
        assert event[5] == "15:00"
        assert event[6] == "13:30"
        mock_schedule.assert_called_once_with(event)

    def test_normalizes_none_times_to_none(self, events_db):
        schedule = ScheduleEvent(
            title="All Day",
            type="important",
            date="2026-08-02",
            start_time=None,
            end_time=None,
            reminder_time=None,
        )

        with patch.object(event_extractor, "schedule_event_reminders"):
            event_extractor.extract_event(schedule)

        event = events_db.get_upcoming_events("upcoming")[0]
        assert event[4] is None
        assert event[5] is None
        assert event[6] is None
