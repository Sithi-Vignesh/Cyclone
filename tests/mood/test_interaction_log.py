import sqlite3
from datetime import datetime

import pytest


class TestLogInteraction:
    def test_log_interaction_inserts_row(self, interaction_db, tmp_path):
        interaction_db.log_interaction()

        conn = sqlite3.connect(tmp_path / "interaction_log.db")
        row = conn.execute(
            "SELECT date, time, hour, day_of_week FROM interaction_log"
        ).fetchone()
        conn.close()

        now = datetime.now()
        assert row is not None
        assert row[0] == now.strftime("%Y-%m-%d")
        assert row[2] == now.hour
        assert row[3] == now.strftime("%A")


class TestGetActiveHours:
    def test_empty_db_returns_empty_list(self, interaction_db):
        assert interaction_db.get_active_hours() == []

    def test_returns_hours_sorted_by_count_descending(self, interaction_db, tmp_path):
        db_path = tmp_path / "interaction_log.db"
        conn = sqlite3.connect(db_path)
        for _ in range(3):
            conn.execute(
                "INSERT INTO interaction_log (date, time, hour, day_of_week) VALUES (?, ?, ?, ?)",
                ("2026-07-01", "10:00", 10, "Wednesday"),
            )
        for _ in range(1):
            conn.execute(
                "INSERT INTO interaction_log (date, time, hour, day_of_week) VALUES (?, ?, ?, ?)",
                ("2026-07-01", "14:00", 14, "Wednesday"),
            )
        conn.commit()
        conn.close()

        rows = interaction_db.get_active_hours()

        assert rows[0] == (10, 3)
        assert rows[1] == (14, 1)

    def test_single_hour_boundary_midnight(self, interaction_db, tmp_path):
        db_path = tmp_path / "interaction_log.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO interaction_log (date, time, hour, day_of_week) VALUES (?, ?, ?, ?)",
            ("2026-07-01", "00:00", 0, "Wednesday"),
        )
        conn.commit()
        conn.close()

        rows = interaction_db.get_active_hours()
        assert rows == [(0, 1)]
