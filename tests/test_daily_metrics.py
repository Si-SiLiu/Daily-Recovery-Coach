import sqlite3
import unittest

from src import daily_metrics, db


class DailyMetricsTests(unittest.TestCase):
    def make_connection(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        db.init_db(connection)
        return connection

    def test_duration_helpers(self):
        self.assertEqual(daily_metrics.duration_to_seconds("PT2H4M30S"), 7470)
        self.assertEqual(daily_metrics.duration_to_seconds("PT45M"), 2700)
        self.assertEqual(daily_metrics.seconds_to_iso_duration(7470), "PT2H4M30S")
        self.assertEqual(daily_metrics.seconds_to_iso_duration(2700), "PT45M")
        self.assertIsNone(daily_metrics.seconds_to_iso_duration(0))

    def test_build_daily_metrics_merges_activity_and_training(self):
        connection = self.make_connection()
        connection.execute(
            """
            INSERT INTO polar_daily_activity_raw (
                source, external_id, date, raw_json, steps, calories, active_calories, duration
            )
            VALUES ('polar', 'activity-1', '2026-07-10', '{}', 1000, 2200, 500, 'PT1H')
            """
        )
        connection.execute(
            """
            INSERT INTO polar_training_sessions_raw (
                source, external_id, date, raw_json, sport, start_time, duration, calories
            )
            VALUES ('polar', 'session-1', '2026-07-10', '{}', 'RUNNING', '2026-07-10T07:00:00', 'PT30M', 300)
            """
        )
        connection.execute(
            """
            INSERT INTO polar_training_sessions_raw (
                source, external_id, date, raw_json, sport, start_time, duration, calories
            )
            VALUES ('polar', 'session-2', '2026-07-10', '{}', 'CYCLING', '2026-07-10T18:00:00', 'PT45M', 450)
            """
        )
        connection.commit()

        metrics = daily_metrics.build_daily_metrics(connection)

        self.assertEqual(len(metrics), 1)
        metric = metrics[0]
        self.assertEqual(metric["date"], "2026-07-10")
        self.assertEqual(metric["steps"], 1000)
        self.assertEqual(metric["calories"], 2200)
        self.assertEqual(metric["active_calories"], 500)
        self.assertEqual(metric["activity_duration"], "PT1H")
        self.assertEqual(metric["training_count"], 2)
        self.assertEqual(metric["training_duration"], "PT1H15M")
        self.assertEqual(metric["training_calories"], 750)
        connection.close()

    def test_rebuild_upserts_daily_metrics(self):
        connection = self.make_connection()
        connection.execute(
            """
            INSERT INTO polar_daily_activity_raw (
                source, external_id, date, raw_json, steps, calories, active_calories, duration
            )
            VALUES ('polar', 'activity-1', '2026-07-10', '{}', 1000, 2200, 500, 'PT1H')
            """
        )
        connection.commit()

        first_count = daily_metrics.rebuild_daily_recovery_metrics(connection)
        connection.execute(
            """
            UPDATE polar_daily_activity_raw
            SET steps = 1500, calories = 2300
            WHERE date = '2026-07-10'
            """
        )
        connection.commit()
        second_count = daily_metrics.rebuild_daily_recovery_metrics(connection)

        row_count = connection.execute(
            "SELECT COUNT(*) FROM daily_recovery_metrics"
        ).fetchone()[0]
        row = connection.execute("SELECT * FROM daily_recovery_metrics").fetchone()

        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 1)
        self.assertEqual(row_count, 1)
        self.assertEqual(row["steps"], 1500)
        self.assertEqual(row["calories"], 2300)
        self.assertEqual(row["training_count"], 0)
        connection.close()

    def test_training_only_day_is_included(self):
        connection = self.make_connection()
        connection.execute(
            """
            INSERT INTO polar_training_sessions_raw (
                source, external_id, date, raw_json, sport, start_time, duration, calories
            )
            VALUES ('polar', 'session-1', '2026-07-11', '{}', 'RUNNING', '2026-07-11T07:00:00', 'PT30M', 300)
            """
        )
        connection.commit()

        daily_metrics.rebuild_daily_recovery_metrics(connection)
        row = connection.execute("SELECT * FROM daily_recovery_metrics").fetchone()

        self.assertEqual(row["date"], "2026-07-11")
        self.assertIsNone(row["steps"])
        self.assertEqual(row["training_count"], 1)
        self.assertEqual(row["training_duration"], "PT30M")
        self.assertEqual(row["training_calories"], 300)
        connection.close()

    def test_sleep_and_nightly_fields_are_included(self):
        connection = self.make_connection()
        connection.execute(
            """
            INSERT INTO polar_sleep_raw (
                source, external_id, date, raw_json, sleep_duration, sleep_score
            )
            VALUES ('polar', 'sleep-1', '2026-07-10', '{}', 'PT7H30M', 82)
            """
        )
        connection.execute(
            """
            INSERT INTO polar_nightly_recharge_raw (
                source, external_id, date, raw_json, hrv_rmssd, resting_hr, respiration_rate
            )
            VALUES ('polar', 'nightly-1', '2026-07-10', '{}', 42, 58, 14.2)
            """
        )
        connection.commit()

        daily_metrics.rebuild_daily_recovery_metrics(connection)
        row = connection.execute("SELECT * FROM daily_recovery_metrics").fetchone()

        self.assertEqual(row["date"], "2026-07-10")
        self.assertEqual(row["sleep_duration"], "PT7H30M")
        self.assertEqual(row["sleep_score"], 82)
        self.assertEqual(row["nightly_hrv_rmssd"], 42)
        self.assertEqual(row["nightly_resting_hr"], 58)
        self.assertEqual(row["respiration_rate"], 14.2)
        connection.close()


if __name__ == "__main__":
    unittest.main()
