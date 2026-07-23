import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src import db
from src.local_coach.config import LocalCoachConfigError
from src.local_coach.engine import run_local_coach
from src.local_coach.evaluation import evaluate_longitudinal, load_evaluation_config


class LocalCoachEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        db.init_db(self.connection)
        for day, score in (("2026-07-07", 80), ("2026-07-08", 60)):
            self.connection.execute(
                "INSERT INTO daily_recovery_metrics (date,training_count,training_calories,sleep_duration,sleep_score) VALUES (?,0,0,'PT7H',70)",
                (day,),
            )
            self.connection.execute(
                "INSERT INTO recovery_scores (date,recovery_score,activity_load_score,training_load_score,score_version,recommendation) VALUES (?,?,40,40,'v1.0','ok')",
                (day, score),
            )
            self.connection.execute(
                """INSERT INTO recovery_confidence
                (date,data_completeness_score,baseline_maturity_score,confidence_score,confidence_level,
                 group_scores_json,available_groups_json,missing_groups_json,confidence_version)
                VALUES (?,90,80,85,'high','{}','[]','[]','1.0.0')""", (day,)
            )
        self.connection.commit()
        run_local_coach(connection=self.connection, all_dates=True)
        self.config = {
            "evaluation_version": "1.0.0", "minimum_records": 2,
            "required_schema_pass_rate": 1.0, "required_deterministic_match_rate": 1.0,
            "required_no_cloud_marker_rate": 1.0, "required_safety_notice_rate": 1.0,
            "maximum_duplicate_keys": 0,
        }

    def tearDown(self):
        self.connection.close()

    def evaluate(self, **kwargs):
        return evaluate_longitudinal(self.connection, today=date(2026, 7, 12),
                                     evaluation_config=self.config, **kwargs)

    def test_complete_history_passes_all_checks(self):
        result = self.evaluate()
        self.assertTrue(result["success"])
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["deterministic_match_rate"], 1.0)

    def test_evaluation_is_read_only(self):
        before = self.connection.total_changes
        self.evaluate()
        self.assertEqual(self.connection.total_changes, before)

    def test_tampered_advice_blocks_deterministic_match(self):
        self.connection.execute(
            "UPDATE local_coach_recommendations SET morning_training_json='{}' WHERE date='2026-07-08'"
        )
        self.connection.commit()
        result = self.evaluate()
        self.assertFalse(result["success"])
        self.assertIn("schema_valid", result["blockers"])

    def test_missing_safety_notice_blocks_release(self):
        self.connection.execute(
            "UPDATE local_coach_recommendations SET safety_notices_json='[]' WHERE date='2026-07-08'"
        )
        self.connection.commit()
        result = self.evaluate()
        self.assertIn("safety_notices", result["blockers"])

    def test_date_filter_can_trigger_minimum_record_blocker(self):
        result = self.evaluate(date_from="2026-07-08", date_to="2026-07-08")
        self.assertEqual(result["record_count"], 1)
        self.assertIn("minimum_records", result["blockers"])

    def test_missing_table_fails_closed_without_crash(self):
        empty = sqlite3.connect(":memory:")
        empty.row_factory = sqlite3.Row
        try:
            result = evaluate_longitudinal(empty, evaluation_config=self.config)
        finally:
            empty.close()
        self.assertFalse(result["success"])
        self.assertEqual(result["record_count"], 0)

    def test_invalid_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evaluation.json"
            path.write_text(json.dumps({"evaluation_version": "1.0.0"}), encoding="utf-8")
            with self.assertRaises(LocalCoachConfigError):
                load_evaluation_config(path)


if __name__ == "__main__":
    unittest.main()
