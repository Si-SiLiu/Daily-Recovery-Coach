import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src import db
from src.local_coach.config import LocalCoachConfigError
from src.local_coach.engine import run_local_coach
from src.local_coach.prospective import evaluate_prospective, load_protocol


class LocalCoachProspectiveTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        db.init_db(self.connection)
        for day in ("2026-07-11", "2026-07-12", "2026-07-13"):
            self.connection.execute(
                "INSERT INTO daily_recovery_metrics (date,training_count,training_calories,sleep_duration,sleep_score) VALUES (?,0,0,'PT7H',70)", (day,)
            )
            self.connection.execute(
                "INSERT INTO recovery_scores (date,recovery_score,activity_load_score,training_load_score,score_version,recommendation) VALUES (?,80,40,40,'v1.0','ok')", (day,)
            )
            self.connection.execute(
                """INSERT INTO recovery_confidence
                (date,data_completeness_score,baseline_maturity_score,confidence_score,confidence_level,
                 group_scores_json,available_groups_json,missing_groups_json,confidence_version)
                VALUES (?,90,80,85,'high','{}','[]','[]','1.0.0')""", (day,)
            )
        self.connection.commit()
        run_local_coach(
            connection=self.connection, all_dates=True, today=date(2026, 7, 13)
        )
        for day in ("2026-07-11", "2026-07-12", "2026-07-13"):
            self.connection.execute(
                "UPDATE local_coach_recommendations SET created_at=? WHERE date=?", (day + " 08:00:00", day)
            )
        self.connection.commit()
        self.protocol = {
            "protocol_version": "1.0.0", "protocol_start_date": "2026-07-12",
            "target_unique_days": 2, "maximum_generation_delay_days": 1,
            "require_schema_pass_rate": 1.0, "require_deterministic_match_rate": 1.0,
            "require_no_cloud_marker_rate": 1.0, "require_safety_notice_rate": 1.0,
        }

    def tearDown(self):
        self.connection.close()

    def test_two_timely_days_pass_protocol(self):
        result = evaluate_prospective(self.connection, today=date(2026, 7, 13), protocol=self.protocol)
        self.assertTrue(result["success"])
        self.assertEqual(result["eligible_unique_days"], 2)

    def test_pre_protocol_history_is_not_counted(self):
        result = evaluate_prospective(self.connection, today=date(2026, 7, 13), protocol=self.protocol)
        self.assertEqual(result["observed_record_count"], 2)

    def test_late_backfill_is_not_eligible(self):
        self.connection.execute(
            "UPDATE local_coach_recommendations SET created_at='2026-07-16 08:00:00' WHERE date='2026-07-13'"
        )
        self.connection.commit()
        result = evaluate_prospective(self.connection, today=date(2026, 7, 16), protocol=self.protocol)
        self.assertFalse(result["success"])
        self.assertEqual(result["late_generation_count"], 1)
        self.assertIn("timely_generation", result["blockers"])

    def test_future_date_is_not_observed_early(self):
        result = evaluate_prospective(self.connection, today=date(2026, 7, 12), protocol=self.protocol)
        self.assertEqual(result["eligible_unique_days"], 1)
        self.assertEqual(result["remaining_unique_days"], 1)

    def test_missing_table_reports_collecting(self):
        empty = sqlite3.connect(":memory:")
        empty.row_factory = sqlite3.Row
        try:
            result = evaluate_prospective(empty, today=date(2026, 7, 13), protocol=self.protocol)
        finally:
            empty.close()
        self.assertEqual(result["status"], "collecting")
        self.assertEqual(result["eligible_unique_days"], 0)

    def test_progress_check_is_read_only(self):
        before = self.connection.total_changes
        evaluate_prospective(self.connection, today=date(2026, 7, 13), protocol=self.protocol)
        self.assertEqual(self.connection.total_changes, before)

    def test_invalid_protocol_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            path.write_text(json.dumps({"protocol_version": "1.0.0"}), encoding="utf-8")
            with self.assertRaises(LocalCoachConfigError):
                load_protocol(path)


if __name__ == "__main__":
    unittest.main()
