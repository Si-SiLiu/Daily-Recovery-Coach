import sqlite3
import unittest
from datetime import date

from src import db
from src.local_coach.engine import generate_recommendation, run_local_coach
from src.local_coach.storage import load_input, load_recommendation, upsert_recommendation


class LocalCoachStorageTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        db.init_db(self.connection)
        self.connection.execute("INSERT INTO daily_recovery_metrics (date, training_count, training_calories, sleep_duration, sleep_score) VALUES ('2026-07-08', 1, 200, 'PT7H', 75)")
        self.connection.execute("INSERT INTO recovery_scores (date,recovery_score,activity_load_score,training_load_score,score_version,recommendation) VALUES ('2026-07-08',80,50,55,'v1.0','ok')")
        self.connection.execute("INSERT INTO recovery_confidence (date,data_completeness_score,baseline_maturity_score,confidence_score,confidence_level,group_scores_json,available_groups_json,missing_groups_json,confidence_version) VALUES ('2026-07-08',90,80,85,'high','{}','[]','[]','1.0.0')")
        self.connection.commit()

    def tearDown(self):
        self.connection.close()

    def test_input_assembly_is_missing_safe_and_historical(self):
        item = load_input(self.connection, "2026-07-08", today=date(2026, 7, 12))
        self.assertEqual(item.recovery_score, 80)
        self.assertTrue(item.is_historical)

    def test_upsert_is_idempotent(self):
        output = generate_recommendation(load_input(self.connection, "2026-07-08"))
        upsert_recommendation(self.connection, output)
        upsert_recommendation(self.connection, output)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM local_coach_recommendations").fetchone()[0], 1)

    def test_round_trip_preserves_structured_output(self):
        output = generate_recommendation(load_input(self.connection, "2026-07-08"))
        upsert_recommendation(self.connection, output)
        loaded = load_recommendation(self.connection, "2026-07-08")
        self.assertEqual(loaded["morning_training"], output["morning_training"])

    def test_dry_run_does_not_write(self):
        result = run_local_coach(connection=self.connection, all_dates=True, dry_run=True)
        self.assertEqual(result["records_validated"], 1)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM local_coach_recommendations").fetchone()[0], 0)

    def test_live_run_writes_one_record(self):
        result = run_local_coach(connection=self.connection, all_dates=True)
        self.assertEqual(result["local_coach_records_updated"], 1)


if __name__ == "__main__":
    unittest.main()
