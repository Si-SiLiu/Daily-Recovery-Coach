import json
import sqlite3
import unittest
from datetime import date, datetime, timezone

from src import db
from src.training_baseline import (
    CALCULATION_WINDOW_DAYS,
    build_training_baseline_view,
    classify_comparison,
    maturity_for_count,
)


class TrainingBaselineTests(unittest.TestCase):
    def test_duration_and_calorie_baselines_use_28_day_window(self):
        self.assertEqual(CALCULATION_WINDOW_DAYS, 28)

    def setUp(self):
        self.connection = db.connect(":memory:")
        self.now = datetime(2026, 7, 22, 14, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.connection.close()

    def add_session(self, day, external_id, duration="PT1H", calories=500, sport="running"):
        self.connection.execute(
            """INSERT INTO polar_training_sessions_raw
               (source,external_id,date,raw_json,sport,start_time,duration,calories)
               VALUES('polar',?,?,?,?,?,?,?)""",
            (external_id, day, json.dumps({"sport": sport}), sport,
             f"{day}T08:00:00", duration, calories),
        )
        self.connection.commit()

    def view(self, sync_status="ok", last_synced_at="2026-07-22T14:00:00+00:00", **kwargs):
        return build_training_baseline_view(
            self.connection, "2026-07-22", now=self.now,
            sync_context={"status": sync_status, "last_synced_at": last_synced_at},
            **kwargs,
        )

    def test_not_synced_does_not_create_zero(self):
        result = self.view(sync_status="not_synced", last_synced_at=None)
        self.assertEqual(result["today"]["status"], "not_synced")
        self.assertIsNone(result["today"]["total_training_calories_kcal"])
        self.assertIsNone(result["calorie_baseline"]["percent_difference"])

    def test_sync_error_does_not_create_negative_delta(self):
        result = self.view(sync_status="sync_error")
        self.assertEqual(result["today"]["status"], "sync_error")
        self.assertIsNone(result["today"]["total_training_calories_kcal"])

    def test_open_day_without_training_is_no_training_yet(self):
        result = self.view()
        self.assertEqual(result["today"]["status"], "no_training_yet")
        self.assertIsNone(result["today"]["total_duration_minutes"])

    def test_planned_rest_is_distinct(self):
        result = self.view(planned_rest_dates={"2026-07-22"})
        self.assertEqual(result["today"]["status"], "planned_rest")

    def test_training_sums_duration_calories_and_preserves_real_zero(self):
        self.add_session("2026-07-22", "a", "PT30M", 0)
        result = self.view()
        self.assertEqual(result["today"]["status"], "partial")
        self.assertEqual(result["today"]["session_count"], 1)
        self.assertEqual(result["today"]["total_duration_minutes"], 30)
        self.assertEqual(result["today"]["total_training_calories_kcal"], 0)

    def test_multiple_sessions_are_accumulated(self):
        self.add_session("2026-07-22", "a", "PT30M", 200)
        self.add_session("2026-07-22", "b", "PT45M", 300)
        result = self.view()
        self.assertEqual(result["today"]["session_count"], 2)
        self.assertEqual(result["today"]["total_duration_minutes"], 75)
        self.assertEqual(result["today"]["total_training_calories_kcal"], 500)

    def test_duplicate_external_record_not_counted_twice(self):
        self.add_session("2026-07-22", "a", "PT30M", 200)
        # The source table's unique key models an update, not a second session.
        self.connection.execute(
            "UPDATE polar_training_sessions_raw SET duration='PT60M', calories=400 WHERE external_id='a'"
        )
        self.connection.commit()
        result = self.view()
        self.assertEqual(result["today"]["session_count"], 1)
        self.assertEqual(result["today"]["total_duration_minutes"], 60)

    def test_duration_and_calorie_samples_are_independent(self):
        self.add_session("2026-07-21", "duration-only", "PT30M", None)
        self.add_session("2026-07-20", "calorie-only", None, 450)
        result = self.view()
        self.assertEqual(result["duration_baseline"]["valid_days"], 1)
        self.assertEqual(result["calorie_baseline"]["valid_days"], 1)

    def test_negative_calories_are_excluded(self):
        self.add_session("2026-07-21", "bad", "PT30M", -1)
        result = self.view()
        self.assertEqual(result["calorie_baseline"]["valid_days"], 0)

    def test_typical_baseline_uses_training_days_only(self):
        for index, value in enumerate((60, 70, 80, 90, 100), start=1):
            self.add_session(f"2026-07-{index:02d}", f"s{index}", f"PT{value}M", value * 5)
        result = self.view()
        self.assertEqual(result["duration_baseline"]["valid_days"], 5)
        self.assertEqual(result["duration_baseline"]["center"], 80)
        self.assertEqual(result["duration_baseline"]["lower_bound"], 70)
        self.assertEqual(result["duration_baseline"]["upper_bound"], 90)

    def test_maturity_thresholds(self):
        self.assertEqual(maturity_for_count(4)["status"], "collecting")
        self.assertEqual(maturity_for_count(5)["status"], "provisional")
        self.assertEqual(maturity_for_count(10)["status"], "reliable")
        self.assertEqual(maturity_for_count(20)["status"], "stable")
        self.assertEqual(maturity_for_count(18)["days_to_next"], 2)

    def test_recent_seven_day_load(self):
        self.add_session("2026-07-20", "a", "PT30M", 200)
        self.add_session("2026-07-21", "b", "PT45M", 300)
        result = self.view()
        self.assertEqual(result["weekly_load"]["session_count"], 2)
        self.assertEqual(result["weekly_load"]["duration_minutes"], 75)
        self.assertEqual(result["weekly_load"]["calories_kcal"], 500)
        self.assertEqual(result["weekly_load"]["valid_training_days"], 2)

    def test_distribution_distinguishes_missing_and_no_training(self):
        result = self.view()
        states = {item["date"]: item["status"] for item in result["distribution_14d"]}
        self.assertEqual(states["2026-07-22"], "no_training_yet")
        self.assertIn("missing", states.values())

    def test_comparison_labels_use_range(self):
        baseline = {"center": 80, "lower_bound": 70, "upper_bound": 90}
        self.assertEqual(classify_comparison(80, baseline), "near_typical")
        self.assertEqual(classify_comparison(50, baseline), "markedly_low")
        self.assertEqual(classify_comparison(120, baseline), "markedly_high")


if __name__ == "__main__":
    unittest.main()
