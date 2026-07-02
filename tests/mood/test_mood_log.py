import sqlite3
from datetime import datetime, timedelta

import pytest


def _insert_mood(db_path, date, time, message, score):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO mood_log (date, time, message, sentiment_score) VALUES (?, ?, ?, ?)",
        (date, time, message, score),
    )
    conn.commit()
    conn.close()


class TestLogMood:
    def test_log_mood_inserts_row(self, mood_db, tmp_path):
        mood_db.log_mood("feeling good", 0.8)

        conn = sqlite3.connect(tmp_path / "mood_log.db")
        row = conn.execute(
            "SELECT date, time, message, sentiment_score FROM mood_log"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[2] == "feeling good"
        assert row[3] == pytest.approx(0.8)
        assert row[0] == datetime.now().strftime("%Y-%m-%d")

    def test_log_mood_zero_sentiment(self, mood_db, tmp_path):
        mood_db.log_mood("neutral", 0.0)

        conn = sqlite3.connect(tmp_path / "mood_log.db")
        score = conn.execute("SELECT sentiment_score FROM mood_log").fetchone()[0]
        conn.close()

        assert score == pytest.approx(0.0)


class TestGetMoodTrend:
    def test_empty_db_returns_none_and_empty_list(self, mood_db):
        average, rows = mood_db.get_mood_trend()
        assert average is None
        assert rows == []

    def test_returns_average_and_rows(self, mood_db, tmp_path):
        today = datetime.now().strftime("%Y-%m-%d")
        db_path = tmp_path / "mood_log.db"
        _insert_mood(db_path, today, "10:00", "good", 0.6)
        _insert_mood(db_path, today, "11:00", "great", 0.8)

        average, rows = mood_db.get_mood_trend(days=7)

        assert average == pytest.approx(0.7)
        assert len(rows) == 2
        assert all(len(row) == 4 for row in rows)

    def test_excludes_old_entries_outside_window(self, mood_db, tmp_path):
        db_path = tmp_path / "mood_log.db"
        old_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        _insert_mood(db_path, old_date, "10:00", "old", -0.5)
        _insert_mood(db_path, today, "10:00", "recent", 0.5)

        average, rows = mood_db.get_mood_trend(days=7)

        assert average == pytest.approx(0.5)
        assert len(rows) == 1

    def test_custom_days_parameter(self, mood_db, tmp_path):
        db_path = tmp_path / "mood_log.db"
        borderline = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        _insert_mood(db_path, borderline, "10:00", "borderline", 0.3)

        avg_7, rows_7 = mood_db.get_mood_trend(days=7)
        avg_14, rows_14 = mood_db.get_mood_trend(days=14)

        assert avg_7 is None and rows_7 == []
        assert avg_14 == pytest.approx(0.3)
        assert len(rows_14) == 1


class TestGetMoodBeforeEvents:
    def test_no_matching_events_returns_empty_list(self, mood_db, events_db):
        result = mood_db.get_mood_before_events(event_type="college")
        assert result == []

    def test_computes_average_mood_before_event(self, mood_db, events_db, tmp_path):
        event_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        events_db.create_event("Exam", "college", event_date, "09:00", "10:00", None)

        db_path = tmp_path / "mood_log.db"
        before_1 = (datetime.strptime(event_date, "%Y-%m-%d") - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        before_2 = (datetime.strptime(event_date, "%Y-%m-%d") - timedelta(days=2)).strftime(
            "%Y-%m-%d"
        )
        _insert_mood(db_path, before_1, "10:00", "nervous", -0.2)
        _insert_mood(db_path, before_2, "10:00", "calm", 0.4)

        result = mood_db.get_mood_before_events(event_type="college", days_before=3)

        assert len(result) == 1
        title, date, avg = result[0]
        assert title == "Exam"
        assert date == event_date
        assert avg == pytest.approx(0.1)

    def test_event_with_no_mood_entries_returns_null_average(
        self, mood_db, events_db
    ):
        event_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        events_db.create_event("Lecture", "college", event_date, "09:00", "10:00", None)

        result = mood_db.get_mood_before_events(event_type="college", days_before=3)

        assert len(result) == 1
        assert result[0][2] is None
