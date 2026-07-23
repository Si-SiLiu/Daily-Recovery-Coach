import sqlite3
import unittest
from datetime import date

from src import db
from src.local_coach.collection import monitor_daily_collection


class LocalCoachCollectionMonitorTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        db.init_db(self.connection)
        self.protocol = {
            "protocol_version": "1.0.0", "protocol_start_date": "2026-07-12",
            "target_unique_days": 14, "maximum_generation_delay_days": 1,
            "require_schema_pass_rate": 1.0, "require_deterministic_match_rate": 1.0,
            "require_no_cloud_marker_rate": 1.0, "require_safety_notice_rate": 1.0,
        }

    def tearDown(self):
        self.connection.close()

    def insert_record(self, day, created=None):
        values = (day,) + tuple("{}" for _ in range(7)) + ("[]", "[]", "1.0.0", "1.0.0", 1)
        self.connection.execute("""INSERT INTO local_coach_recommendations
            (date,morning_training_json,evening_training_json,sleep_advice_json,hydration_advice_json,
             nutrition_advice_json,recovery_advice_json,rationale_json,data_limitations_json,safety_notices_json,
             engine_version,rule_config_version,generated_without_cloud_ai)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", values)
        if created:
            self.connection.execute(
                "UPDATE local_coach_recommendations SET created_at=? WHERE date=?", (created, day)
            )
        self.connection.commit()

    def monitor(self, day):
        return monitor_daily_collection(self.connection, today=date.fromisoformat(day), protocol=self.protocol)

    def test_protocol_start_day_is_awaiting_without_overdue_gap(self):
        result = self.monitor("2026-07-12")
        self.assertEqual(result["status"], "awaiting_today")
        self.assertEqual(result["overdue_missing_days"], 0)
        self.assertTrue(result["on_track"])

    def test_today_record_marks_collected(self):
        self.insert_record("2026-07-12", "2026-07-12 08:00:00")
        result = self.monitor("2026-07-12")
        self.assertTrue(result["today_collected"])
        self.assertEqual(result["status"], "collected_today")
        self.assertEqual(result["current_streak_days"], 1)

    def test_streak_continues_while_waiting_for_today(self):
        self.insert_record("2026-07-12", "2026-07-12 08:00:00")
        self.insert_record("2026-07-13", "2026-07-13 08:00:00")
        result = self.monitor("2026-07-14")
        self.assertEqual(result["status"], "awaiting_today")
        self.assertEqual(result["current_streak_days"], 2)

    def test_past_missing_day_requires_attention(self):
        self.insert_record("2026-07-12", "2026-07-12 08:00:00")
        result = self.monitor("2026-07-14")
        self.assertEqual(result["status"], "attention_required")
        self.assertEqual(result["overdue_missing_days"], 1)

    def test_late_generation_requires_attention(self):
        self.insert_record("2026-07-12", "2026-07-15 08:00:00")
        result = self.monitor("2026-07-15")
        self.assertEqual(result["late_generation_count"], 1)
        self.assertFalse(result["on_track"])

    def test_before_protocol_start_is_not_started(self):
        result = self.monitor("2026-07-11")
        self.assertEqual(result["status"], "protocol_not_started")

    def test_monitor_is_read_only(self):
        before = self.connection.total_changes
        self.monitor("2026-07-12")
        self.assertEqual(self.connection.total_changes, before)


if __name__ == "__main__":
    unittest.main()
