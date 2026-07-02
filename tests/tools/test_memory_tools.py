"""Unit tests for app/backend/tools/memory_tools.py.

All file-system operations (shutil.rmtree, os.remove) and all internal
helper functions (fetch_events, get_mood_trend, get_active_hours,
get_mood_before_events) are mocked.  No real DB is touched.

NOTE: Because tests/tools/conftest.py stubs @tool as a no-op decorator,
the tool functions are plain Python functions here. Called directly.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.backend.tools.memory_tools import (
    delete_all_memory,
    get_upcoming_events,
    get_mood_summary,
    get_behavior_summary,
    get_exam_stress_summary,
)


# ---------------------------------------------------------------------------
# get_upcoming_events
# ---------------------------------------------------------------------------
class TestGetUpcomingEvents:
    # A full event row: id, title, type, date, start, end, reminder, status, reminded_times
    _ROW = (1, "Exam", "college", "2026-08-01", "09:00", "11:00", "08:30", "upcoming", 0)

    def test_returns_formatted_events(self):
        with patch("app.backend.tools.memory_tools.fetch_events", return_value=[self._ROW]):
            result = get_upcoming_events()
        assert "Exam" in result
        assert "college" in result
        assert "2026-08-01" in result
        assert "09:00" in result
        assert "08:30" in result  # reminder time

    def test_no_events_returns_no_upcoming_message(self):
        with patch("app.backend.tools.memory_tools.fetch_events", return_value=[]):
            result = get_upcoming_events()
        assert "No upcoming events" in result

    def test_event_without_optional_times(self):
        row = (2, "Meeting", "personal", "2026-08-05", None, None, None, "upcoming", 0)
        with patch("app.backend.tools.memory_tools.fetch_events", return_value=[row]):
            result = get_upcoming_events()
        assert "Meeting" in result
        # None times should not appear literally in output
        assert "None" not in result

    def test_multiple_events_all_listed(self):
        row2 = (3, "Gym", "personal", "2026-08-02", "07:00", None, None, "upcoming", 0)
        with patch(
            "app.backend.tools.memory_tools.fetch_events",
            return_value=[self._ROW, row2],
        ):
            result = get_upcoming_events()
        assert "Exam" in result
        assert "Gym" in result


# ---------------------------------------------------------------------------
# delete_all_memory
# ---------------------------------------------------------------------------
class TestDeleteAllMemory:
    def test_wrong_passcode_rejected(self):
        result = delete_all_memory("wrongpassword")
        assert "Incorrect passcode" in result

    def test_passcode_check_is_case_sensitive(self):
        """FIX VERIFIED: passcode comparison is now case-sensitive.
        Lowercase and mixed-case variants must be REJECTED.
        Only the exact string 'THUNDER3328D' is accepted.
        """
        # Lowercase — must be rejected
        assert "Incorrect passcode" in delete_all_memory("thunder3328d")
        # Mixed-case — must be rejected
        assert "Incorrect passcode" in delete_all_memory("Thunder3328d")
        # Exact-case — must be accepted (deletion calls are mocked)
        with (
            patch("app.backend.tools.memory_tools.shutil.rmtree"),
            patch("app.backend.tools.memory_tools.os.remove"),
            patch("pathlib.Path.exists", return_value=False),
        ):
            result = delete_all_memory("THUNDER3328D")
        assert "wiped" in result.lower() or "forgotten" in result.lower()

    def test_correct_passcode_wipes_memory(self):
        """With correct passcode, all deletion helpers are called and success returned."""
        with (
            patch("app.backend.tools.memory_tools.shutil.rmtree") as mock_rmtree,
            patch("app.backend.tools.memory_tools.os.remove") as mock_remove,
            # Make all Path.exists() calls return True so deletion branches execute
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = delete_all_memory("THUNDER3328D")
        # shutil.rmtree should be called for chroma_data
        mock_rmtree.assert_called_once()
        # os.remove should be called twice: events.db and thunder.md
        assert mock_remove.call_count == 2
        assert "wiped" in result.lower() or "forgotten" in result.lower()

    def test_correct_passcode_skips_missing_paths(self):
        """If data paths don't exist, no deletion calls should happen (no crash)."""
        with (
            patch("app.backend.tools.memory_tools.shutil.rmtree") as mock_rmtree,
            patch("app.backend.tools.memory_tools.os.remove") as mock_remove,
            patch("pathlib.Path.exists", return_value=False),
        ):
            result = delete_all_memory("THUNDER3328D")
        mock_rmtree.assert_not_called()
        mock_remove.assert_not_called()
        assert "wiped" in result.lower() or "forgotten" in result.lower()


# ---------------------------------------------------------------------------
# get_mood_summary
# ---------------------------------------------------------------------------
class TestGetMoodSummary:
    def test_returns_summary_when_data_available(self):
        rows = [
            ("2026-07-01", "10:00", "feeling good", 0.72),
            ("2026-07-02", "11:00", "a bit tired",  0.21),
        ]
        with patch("app.backend.tools.memory_tools.get_mood_trend", return_value=(0.465, rows)):
            result = get_mood_summary(7)
        assert "0.47" in result or "0.46" in result  # rounded average
        assert "feeling good" in result
        assert "a bit tired" in result

    def test_returns_no_data_message_when_average_is_none(self):
        with patch("app.backend.tools.memory_tools.get_mood_trend", return_value=(None, [])):
            result = get_mood_summary(7)
        assert "No mood data" in result

    def test_default_days_parameter(self):
        """Calling without specifying days defaults to 7."""
        with patch(
            "app.backend.tools.memory_tools.get_mood_trend", return_value=(None, [])
        ) as mock_trend:
            get_mood_summary()
        mock_trend.assert_called_once_with(days=7)

    def test_custom_days_passed_through(self):
        with patch(
            "app.backend.tools.memory_tools.get_mood_trend", return_value=(None, [])
        ) as mock_trend:
            get_mood_summary(30)
        mock_trend.assert_called_once_with(days=30)


# ---------------------------------------------------------------------------
# get_behavior_summary
# ---------------------------------------------------------------------------
class TestGetBehaviorSummary:
    def test_returns_formatted_activity_by_hour(self):
        rows = [(9, 12), (14, 8), (21, 5)]
        with patch("app.backend.tools.memory_tools.get_active_hours", return_value=rows):
            result = get_behavior_summary()
        assert "9:00" in result
        assert "12 messages" in result
        assert "14:00" in result

    def test_returns_no_data_message_when_empty(self):
        with patch("app.backend.tools.memory_tools.get_active_hours", return_value=[]):
            result = get_behavior_summary()
        assert "No interaction data" in result


# ---------------------------------------------------------------------------
# get_exam_stress_summary
# ---------------------------------------------------------------------------
class TestGetExamStressSummary:
    def test_returns_formatted_stress_summary(self):
        results = [
            ("Midsem", "2026-07-10", 0.15),
            ("Finals", "2026-08-20", -0.30),
        ]
        with patch("app.backend.tools.memory_tools.get_mood_before_events", return_value=results):
            result = get_exam_stress_summary()
        assert "Midsem" in result
        assert "Finals" in result
        assert "0.15" in result

    def test_event_with_no_mood_data(self):
        results = [("Midsem", "2026-07-10", None)]
        with patch("app.backend.tools.memory_tools.get_mood_before_events", return_value=results):
            result = get_exam_stress_summary()
        assert "no mood data" in result.lower()

    def test_returns_no_events_message_when_empty(self):
        with patch(
            "app.backend.tools.memory_tools.get_mood_before_events", return_value=[]
        ):
            result = get_exam_stress_summary()
        assert "No college events" in result
