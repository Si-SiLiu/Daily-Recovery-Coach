import sqlite3
import unittest
from datetime import date, timedelta

from src import baseline, db


class BaselineTests(unittest.TestCase):
    def make_connection(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        db.init_db(connection)
        return connection

    def metric(self, name):
        config = baseline.load_baseline_config()
        return next(metric for metric in config["metrics"] if metric["name"] == name)

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

    def insert_series(self, connection, start_day, count, column, start_value):
        current = date.fromisoformat(start_day)
        for index in range(count):
            self.insert_day(
                connection,
                (current + timedelta(days=index)).isoformat(),
                **{column: start_value + index},
            )

    def test_normal_28_day_baseline(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 28, "nightly_hrv_rmssd", 50)
        self.insert_day(connection, "2026-01-29", nightly_hrv_rmssd=65)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-29",
            self.metric("nightly_hrv_rmssd"),
        )

        self.assertEqual(result["valid_days"], 28)
        self.assertEqual(result["latest_value"], 65)
        self.assertEqual(result["status"], "within_baseline")
        connection.close()

    def test_exactly_7_days_is_sufficient(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 7, "steps", 1000)
        self.insert_day(connection, "2026-01-08", steps=1200)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-08",
            self.metric("steps"),
        )

        self.assertEqual(result["valid_days"], 7)
        self.assertNotEqual(result["status"], "insufficient_data")
        connection.close()

    def test_less_than_7_days_is_insufficient(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 6, "steps", 1000)
        self.insert_day(connection, "2026-01-07", steps=1200)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-07",
            self.metric("steps"),
        )

        self.assertEqual(result["valid_days"], 6)
        self.assertEqual(result["status"], "insufficient_data")
        connection.close()

    def test_target_day_does_not_enter_own_baseline(self):
        connection = self.make_connection()
        for index in range(7):
            self.insert_day(
                connection,
                (date(2026, 1, 1) + timedelta(days=index)).isoformat(),
                nightly_hrv_rmssd=50,
            )
        self.insert_day(connection, "2026-01-08", nightly_hrv_rmssd=100)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-08",
            self.metric("nightly_hrv_rmssd"),
        )

        self.assertEqual(result["median_value"], 50)
        self.assertEqual(result["latest_value"], 100)
        connection.close()

    def test_missing_hrv_is_insufficient(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 7, "nightly_hrv_rmssd", 50)
        self.insert_day(connection, "2026-01-08")

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-08",
            self.metric("nightly_hrv_rmssd"),
        )

        self.assertIsNone(result["latest_value"])
        self.assertEqual(result["status"], "insufficient_data")
        connection.close()

    def test_hrv_below_baseline(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 14, "nightly_hrv_rmssd", 58)
        self.insert_day(connection, "2026-01-15", nightly_hrv_rmssd=40)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-15",
            self.metric("nightly_hrv_rmssd"),
        )

        self.assertEqual(result["status"], "below_baseline")
        connection.close()

    def test_resting_hr_above_baseline(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 14, "nightly_resting_hr", 55)
        self.insert_day(connection, "2026-01-15", nightly_resting_hr=75)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-15",
            self.metric("nightly_resting_hr"),
        )

        self.assertEqual(result["status"], "above_baseline")
        connection.close()

    def test_mad_zero_and_std_zero(self):
        connection = self.make_connection()
        for index in range(7):
            self.insert_day(
                connection,
                (date(2026, 1, 1) + timedelta(days=index)).isoformat(),
                sleep_score=80,
            )
        self.insert_day(connection, "2026-01-08", sleep_score=80)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-08",
            self.metric("sleep_score"),
        )

        self.assertEqual(result["mad_value"], 0)
        self.assertEqual(result["std_value"], 0)
        self.assertEqual(result["robust_z_score"], 0)
        self.assertEqual(result["z_score"], 0)
        self.assertEqual(result["status"], "within_baseline")
        connection.close()

    def test_outlier_filter_does_not_reduce_observed_valid_days(self):
        connection = self.make_connection()
        for index, value in enumerate((20, 21, 22, 23, 24, 25, 80)):
            self.insert_day(
                connection,
                (date(2026, 1, 1) + timedelta(days=index)).isoformat(),
                morning_rmssd=value,
            )
        self.insert_day(connection, "2026-01-08", morning_rmssd=20)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-08",
            self.metric("morning_rmssd"),
        )

        self.assertEqual(result["valid_days"], 7)
        self.assertEqual(result["max_value"], 25)
        self.assertNotEqual(result["status"], "insufficient_data")
        connection.close()

    def test_iso_8601_duration_conversion(self):
        connection = self.make_connection()
        for index in range(7):
            self.insert_day(
                connection,
                (date(2026, 1, 1) + timedelta(days=index)).isoformat(),
                training_duration="PT1H30M",
            )
        self.insert_day(connection, "2026-01-08", training_duration="PT2H")

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-08",
            self.metric("training_duration"),
        )

        self.assertEqual(result["median_value"], 90)
        self.assertEqual(result["latest_value"], 120)
        connection.close()

    def test_negative_values_are_ignored(self):
        connection = self.make_connection()
        for index in range(8):
            value = -1 if index == 0 else 1000 + index
            self.insert_day(
                connection,
                (date(2026, 1, 1) + timedelta(days=index)).isoformat(),
                active_calories=value,
            )
        self.insert_day(connection, "2026-01-09", active_calories=-100)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-09",
            self.metric("active_calories"),
        )

        self.assertEqual(result["valid_days"], 7)
        self.assertIsNone(result["latest_value"])
        self.assertEqual(result["status"], "insufficient_data")
        connection.close()

    def test_only_polar_night_hrv_can_compute_that_metric(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 7, "nightly_hrv_rmssd", 50)
        self.insert_day(connection, "2026-01-08", nightly_hrv_rmssd=55)

        results = baseline.calculate_baseline_for_date(connection, "2026-01-08")
        by_name = {result["metric_name"]: result for result in results}

        self.assertNotEqual(by_name["nightly_hrv_rmssd"]["status"], "insufficient_data")
        self.assertEqual(by_name["morning_rmssd"]["status"], "insufficient_data")
        connection.close()

    def test_only_kubios_morning_hrv_can_compute_that_metric(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 7, "morning_rmssd", 70)
        self.insert_day(connection, "2026-01-08", morning_rmssd=72)

        results = baseline.calculate_baseline_for_date(connection, "2026-01-08")
        by_name = {result["metric_name"]: result for result in results}

        self.assertNotEqual(by_name["morning_rmssd"]["status"], "insufficient_data")
        self.assertEqual(by_name["nightly_hrv_rmssd"]["status"], "insufficient_data")
        connection.close()

    def test_sleep_fields_empty(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 7, "sleep_score", 80)
        self.insert_day(connection, "2026-01-08", sleep_score=None)

        result = baseline.calculate_baseline_for_metric(
            connection,
            "2026-01-08",
            self.metric("sleep_score"),
        )

        self.assertEqual(result["status"], "insufficient_data")
        connection.close()

    def test_repeated_run_upserts_without_duplicates(self):
        connection = self.make_connection()
        self.insert_series(connection, "2026-01-01", 7, "steps", 1000)
        self.insert_day(connection, "2026-01-08", steps=1200)

        first = baseline.calculate_baseline_for_date(connection, "2026-01-08")
        baseline.calculate_baseline_for_date(connection, "2026-01-08")
        count = connection.execute("SELECT COUNT(*) FROM baseline_metrics").fetchone()[0]

        self.assertEqual(count, len(first))
        connection.close()


if __name__ == "__main__":
    unittest.main()
