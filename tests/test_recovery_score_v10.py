import sqlite3
import unittest
from datetime import date, timedelta

from src import db, recovery_score


class RecoveryScoreV10Tests(unittest.TestCase):
    def make_connection(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        db.init_db(connection)
        return connection

    def usable_baseline(self, metric_name, robust_z_score, latest_value=50):
        return {
            "date": "2026-07-10",
            "window_days": 28,
            "valid_days": 7,
            "metric_name": metric_name,
            "latest_value": latest_value,
            "percent_change": None,
            "z_score": None,
            "robust_z_score": robust_z_score,
            "status": "within_baseline",
        }

    def insert_day(self, connection, day, **values):
        columns = ["date"]
        params = [day]
        for key, value in values.items():
            columns.append(key)
            params.append(value)
        placeholders = ", ".join(["?"] * len(columns))
        connection.execute(
            f"""
            INSERT INTO daily_recovery_metrics ({", ".join(columns)})
            VALUES ({placeholders})
            """,
            params,
        )
        connection.commit()

    def test_baseline_score_directions(self):
        high_good = recovery_score.score_from_baseline(
            self.usable_baseline("nightly_hrv_rmssd", 1),
            "higher_is_better",
        )
        low_good = recovery_score.score_from_baseline(
            self.usable_baseline("nightly_resting_hr", 1),
            "lower_is_better",
        )
        load = recovery_score.score_from_baseline(
            self.usable_baseline("training_duration", 1),
            "higher_is_load",
        )

        self.assertGreater(high_good, 75)
        self.assertLess(low_good, 75)
        self.assertGreater(load, 50)

    def test_calculate_recovery_score_uses_v10_with_usable_baselines(self):
        metric = {
            "date": "2026-07-10",
            "steps": 12000,
            "active_calories": 1200,
            "training_duration": "PT90M",
            "training_calories": 700,
            "nightly_hrv_rmssd": 40,
            "sleep_score": 70,
            "nightly_resting_hr": 65,
            "morning_rmssd": None,
            "morning_mean_hr": None,
            "kubios_readiness": None,
        }
        baselines = {
            "nightly_hrv_rmssd": self.usable_baseline("nightly_hrv_rmssd", -2),
            "nightly_resting_hr": self.usable_baseline("nightly_resting_hr", 2),
            "sleep_score": self.usable_baseline("sleep_score", -1),
            "steps": self.usable_baseline("steps", 2),
            "active_calories": self.usable_baseline("active_calories", 2),
            "training_duration": self.usable_baseline("training_duration", 2),
            "training_calories": self.usable_baseline("training_calories", 2),
        }

        score = recovery_score.calculate_recovery_score(metric, baselines=baselines)

        self.assertEqual(score["score_version"], "v1.0")
        self.assertLess(score["recovery_score"], 60)
        self.assertEqual(score["recommendation"], "减量训练")
        self.assertIsNotNone(score["hrv_score"])
        self.assertIsNotNone(score["morning_hr_score"])
        self.assertIsNotNone(score["readiness_score"])

    def test_insufficient_baselines_fall_back_to_existing_versions(self):
        metric = {
            "date": "2026-07-10",
            "steps": 1000,
            "active_calories": 100,
            "training_duration": None,
            "training_calories": 0,
            "nightly_hrv_rmssd": 50,
            "sleep_score": None,
            "nightly_resting_hr": None,
            "morning_rmssd": None,
            "morning_mean_hr": None,
            "kubios_readiness": None,
        }
        baselines = {
            "nightly_hrv_rmssd": {
                **self.usable_baseline("nightly_hrv_rmssd", 0),
                "valid_days": 6,
                "status": "insufficient_data",
            }
        }

        score = recovery_score.calculate_recovery_score(metric, baselines=baselines)

        self.assertEqual(score["score_version"], "v0.3")

    def test_rebuild_scores_recomputes_baselines_and_uses_v10(self):
        connection = self.make_connection()
        start = date(2026, 1, 1)
        for index in range(7):
            self.insert_day(
                connection,
                (start + timedelta(days=index)).isoformat(),
                steps=5000 + index * 10,
                active_calories=500 + index * 5,
                training_count=1,
                training_duration="PT45M",
                training_calories=350 + index * 2,
                nightly_hrv_rmssd=55 + index,
                sleep_score=82,
                nightly_resting_hr=58,
            )
        self.insert_day(
            connection,
            "2026-01-08",
            steps=12000,
            active_calories=1200,
            training_count=1,
            training_duration="PT2H",
            training_calories=900,
            nightly_hrv_rmssd=45,
            sleep_score=70,
            nightly_resting_hr=68,
        )

        count = recovery_score.rebuild_recovery_scores(connection)
        latest = connection.execute(
            "SELECT * FROM recovery_scores WHERE date = '2026-01-08'"
        ).fetchone()
        baseline_count = connection.execute(
            "SELECT COUNT(*) FROM baseline_metrics"
        ).fetchone()[0]

        self.assertEqual(count, 8)
        self.assertGreater(baseline_count, 0)
        self.assertEqual(latest["score_version"], "v1.0")
        self.assertLess(latest["recovery_score"], 80)
        connection.close()


if __name__ == "__main__":
    unittest.main()
