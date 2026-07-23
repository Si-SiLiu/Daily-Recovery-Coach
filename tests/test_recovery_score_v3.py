import sqlite3
import unittest

from src import db, recovery_score


class RecoveryScoreV3Tests(unittest.TestCase):
    def make_connection(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        db.init_db(connection)
        return connection

    def test_sleep_score_is_clamped(self):
        self.assertEqual(recovery_score.calculate_sleep_score(85), 85)
        self.assertEqual(recovery_score.calculate_sleep_score(120), 100)
        self.assertIsNone(recovery_score.calculate_sleep_score(None))

    def test_calculate_recovery_score_uses_v3_with_polar_nightly_hrv(self):
        score = recovery_score.calculate_recovery_score(
            {
                "date": "2026-07-10",
                "steps": 20000,
                "active_calories": 2200,
                "training_duration": "PT2H",
                "training_calories": 1200,
                "nightly_hrv_rmssd": 80,
                "sleep_score": None,
                "nightly_resting_hr": None,
                "morning_rmssd": None,
                "morning_mean_hr": None,
                "kubios_readiness": None,
            }
        )

        self.assertEqual(score["score_version"], "v0.3")
        self.assertEqual(score["hrv_score"], 100)
        self.assertGreater(score["recovery_score"], 60)

    def test_kubios_v2_takes_precedence_over_polar_v3(self):
        score = recovery_score.calculate_recovery_score(
            {
                "date": "2026-07-10",
                "steps": 1000,
                "active_calories": 100,
                "training_duration": None,
                "training_calories": 0,
                "nightly_hrv_rmssd": 40,
                "sleep_score": 80,
                "nightly_resting_hr": 60,
                "morning_rmssd": 80,
                "morning_mean_hr": 50,
                "kubios_readiness": "Excellent",
            }
        )

        self.assertEqual(score["score_version"], "v0.2")
        self.assertEqual(score["hrv_score"], 100)

    def test_rebuild_recovery_scores_upserts_v3_columns(self):
        connection = self.make_connection()
        connection.execute(
            """
            INSERT INTO daily_recovery_metrics (
                date,
                steps,
                active_calories,
                training_count,
                training_duration,
                training_calories,
                nightly_hrv_rmssd,
                sleep_score,
                nightly_resting_hr
            )
            VALUES ('2026-07-10', 8000, 900, 0, NULL, 0, 50, 82, 58)
            """
        )
        connection.commit()

        count = recovery_score.rebuild_recovery_scores(connection)
        row = connection.execute("SELECT * FROM recovery_scores").fetchone()

        self.assertEqual(count, 1)
        self.assertEqual(row["score_version"], "v0.3")
        self.assertIsNotNone(row["hrv_score"])
        self.assertIsNotNone(row["morning_hr_score"])
        self.assertEqual(row["readiness_score"], 82)
        connection.close()


if __name__ == "__main__":
    unittest.main()
