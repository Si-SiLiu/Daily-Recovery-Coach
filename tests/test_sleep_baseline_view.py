import unittest
from datetime import date, timedelta

from src.sleep_baseline_view import (
    build_sleep_baseline_summary,
    build_sleep_regularity_baseline,
    build_sleep_regularity_points,
)


class SleepBaselineViewTests(unittest.TestCase):
    def test_calendar_series_preserves_missing_dates_and_excludes_target(self):
        summary = build_sleep_baseline_summary(
            [("2026-07-01", 10), ("2026-07-03", 30), ("2026-07-04", 99)],
            "2026-07-04",
            window_days=3,
        )

        self.assertEqual(summary["dates"], ["2026-07-01", "2026-07-02", "2026-07-03"])
        self.assertEqual(summary["series"], [10.0, None, 30.0])
        self.assertEqual(summary["valid_nights"], 2)

    def test_summary_contains_range_period_comparison_and_anomalies(self):
        target = date(2026, 7, 15)
        points = [
            ((target - timedelta(days=14 - index)).isoformat(), value)
            for index, value in enumerate([10, 10, 10, 10, 10, 10, 1, 20, 20, 20, 20, 20, 20, 40])
        ]

        summary = build_sleep_baseline_summary(points, target)

        self.assertEqual(summary["valid_nights"], 14)
        self.assertEqual(summary["recent_average"], 160 / 7)
        self.assertEqual(summary["previous_average"], 61 / 7)
        self.assertGreater(summary["difference"], 0)
        self.assertIn((target - timedelta(days=1)).isoformat(), summary["anomaly_dates"])

    def test_period_comparison_uses_valid_nights_across_calendar_gaps(self):
        target = date(2026, 7, 29)
        points = []
        for offset, value in zip(range(28, 14, -1), [10] * 7 + [20] * 7):
            points.append(((target - timedelta(days=offset)).isoformat(), value))

        summary = build_sleep_baseline_summary(points, target)

        self.assertEqual(summary["previous_average"], 10)
        self.assertEqual(summary["recent_average"], 20)
        self.assertEqual(summary["difference"], 10)

    def test_regularity_points_are_rolling_scores_not_copied_static_values(self):
        records = []
        for index in range(15):
            day = date(2026, 7, 1) + timedelta(days=index)
            records.append({
                "date": day.isoformat(),
                "resolved_fields": {
                    "sleep_start_time": {"value": "23:00"},
                    "wake_time": {"value": "07:00"},
                    "actual_sleep_duration_minutes": {"value": 450},
                },
            })

        points = build_sleep_regularity_points(records, "2026-07-16")

        self.assertEqual(points[0][0], "2026-07-07")
        self.assertEqual(points[-1][0], "2026-07-15")
        self.assertTrue(all(score >= 99 for _, score in points))

        current, baseline = build_sleep_regularity_baseline(records, "2026-07-15")
        self.assertGreaterEqual(current, 99)
        self.assertEqual(baseline["metric_name"], "sleep_regularity")
        self.assertEqual(baseline["latest_value"], current)


if __name__ == "__main__":
    unittest.main()
