import json
import sqlite3
import unittest

from src import db, recovery_confidence


class RecoveryConfidenceTests(unittest.TestCase):
    def full_metric(self):
        return {
            "date": "2026-07-10", "steps": 10000, "active_calories": 500,
            "training_count": 1, "training_duration": "PT1H", "training_calories": 400,
            "nightly_hrv_rmssd": 50, "morning_rmssd": None,
            "nightly_resting_hr": 55, "morning_mean_hr": None,
            "sleep_duration": "PT8H", "sleep_score": 85,
            "respiration_rate": 14, "kubios_readiness": None,
        }

    def full_baselines(self, valid_days=28):
        return {
            name: {"window_days": 28, "valid_days": valid_days}
            for metrics in recovery_confidence.MATURITY_METRICS.values()
            for name in metrics
        }

    def test_empty_day_is_very_low(self):
        result = recovery_confidence.calculate_confidence({"date": "2026-07-10"}, {}, "1.0.0")
        self.assertEqual(result["data_completeness_score"], 0)
        self.assertEqual(result["confidence_score"], 0)
        self.assertEqual(result["confidence_level"], "very_low")

    def test_full_day_and_history_are_high(self):
        result = recovery_confidence.calculate_confidence(self.full_metric(), self.full_baselines(), "1.0.0")
        self.assertEqual(result["data_completeness_score"], 100)
        self.assertEqual(result["baseline_maturity_score"], 100)
        self.assertEqual(result["confidence_score"], 100)
        self.assertEqual(result["confidence_level"], "high")

    def test_recorded_no_training_day_is_complete(self):
        metric = {"date": "2026-07-10", "training_count": 0}
        groups = recovery_confidence.completeness_groups(metric)
        self.assertEqual(groups["training_load"], 100)
        metric["training_count"] = None
        self.assertEqual(recovery_confidence.completeness_groups(metric)["training_load"], 0)

    def test_alternative_hrv_and_heart_rate_sources_are_complete(self):
        metric = {"morning_rmssd": 40, "morning_mean_hr": 60}
        groups = recovery_confidence.completeness_groups(metric)
        self.assertEqual(groups["hrv"], 100)
        self.assertEqual(groups["resting_heart_rate"], 100)

    def test_partial_activity_sleep_and_invalid_values(self):
        metric = {"steps": 0, "sleep_score": 80, "sleep_duration": "invalid", "nightly_hrv_rmssd": -1}
        groups = recovery_confidence.completeness_groups(metric)
        self.assertEqual(groups["activity_load"], 50)
        self.assertEqual(groups["sleep"], 50)
        self.assertEqual(groups["hrv"], 0)

    def test_seven_day_and_capped_maturity(self):
        self.assertEqual(recovery_confidence.metric_maturity({"valid_days": 7, "window_days": 28}), 25)
        self.assertEqual(recovery_confidence.metric_maturity({"valid_days": 40, "window_days": 28}), 100)

    def test_confidence_boundaries(self):
        self.assertEqual(recovery_confidence.confidence_level(85), "high")
        self.assertEqual(recovery_confidence.confidence_level(70), "medium")
        self.assertEqual(recovery_confidence.confidence_level(50), "low")
        self.assertEqual(recovery_confidence.confidence_level(49), "very_low")

    def test_rebuild_is_idempotent_and_recovery_rows_are_unchanged(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        db.init_db(connection)
        metric = self.full_metric()
        columns = ",".join(metric)
        placeholders = ",".join("?" for _ in metric)
        connection.execute(f"INSERT INTO daily_recovery_metrics ({columns}) VALUES ({placeholders})", tuple(metric.values()))
        connection.execute("INSERT INTO recovery_scores (date,recovery_score,activity_load_score,training_load_score,recommendation,score_version) VALUES ('2026-07-10',75,10,20,'正常训练','v1.0')")
        connection.commit()
        before = tuple(connection.execute("SELECT * FROM recovery_scores").fetchone())
        self.assertEqual(recovery_confidence.rebuild_confidence(connection), 1)
        self.assertEqual(recovery_confidence.rebuild_confidence(connection), 1)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM recovery_confidence").fetchone()[0], 1)
        after = tuple(connection.execute("SELECT * FROM recovery_scores").fetchone())
        self.assertEqual(before, after)
        row = connection.execute("SELECT * FROM recovery_confidence").fetchone()
        self.assertEqual(row["confidence_version"], "1.0.0")
        self.assertIn("hrv", json.loads(row["group_scores_json"]))
        connection.close()


if __name__ == "__main__":
    unittest.main()
