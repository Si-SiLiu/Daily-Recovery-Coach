import unittest

from src import recovery_explain


class RecoveryExplainTests(unittest.TestCase):
    def baseline(self, status, percent, robust_z, latest=50, median=50):
        return {
            "valid_days": 14,
            "status": status,
            "latest_value": latest,
            "median_value": median,
            "percent_change": percent,
            "robust_z_score": robust_z,
            "z_score": None,
        }

    def latest(self):
        return {
            "recovery_score": 59,
            "score_version": "v1.0",
            "recommendation": "减量训练",
        }

    def test_higher_is_better_metric_below_baseline_is_negative(self):
        result = recovery_explain.generate_recovery_explanation(
            self.latest(),
            {
                "nightly_hrv_rmssd": self.baseline(
                    "below_baseline", -20, -1.5, latest=40, median=50
                )
            },
        )

        self.assertEqual(result["negative"][0]["metric_name"], "nightly_hrv_rmssd")
        self.assertIn("-20.0%", result["negative"][0]["message"])

    def test_higher_resting_hr_and_training_load_are_negative(self):
        result = recovery_explain.generate_recovery_explanation(
            self.latest(),
            {
                "nightly_resting_hr": self.baseline(
                    "above_baseline", 10, 1.2, latest=66, median=60
                ),
                "training_duration": self.baseline(
                    "above_baseline", 50, 2.0, latest=90, median=60
                ),
            },
        )

        self.assertEqual(
            [factor["metric_name"] for factor in result["negative"]],
            ["training_duration", "nightly_resting_hr"],
        )

    def test_below_baseline_load_is_positive(self):
        result = recovery_explain.generate_recovery_explanation(
            self.latest(),
            {
                "active_calories": self.baseline(
                    "below_baseline", -30, -1.4, latest=700, median=1000
                )
            },
        )

        self.assertEqual(result["positive"][0]["metric_name"], "active_calories")

    def test_within_baseline_is_neutral(self):
        result = recovery_explain.generate_recovery_explanation(
            self.latest(),
            {"sleep_score": self.baseline("within_baseline", 2, 0.1)},
        )

        self.assertEqual(result["neutral"][0]["metric_name"], "sleep_score")

    def test_insufficient_and_missing_baselines_are_reported(self):
        insufficient = self.baseline("insufficient_data", None, None)
        insufficient["valid_days"] = 6
        result = recovery_explain.generate_recovery_explanation(
            self.latest(), {"morning_rmssd": insufficient}
        )

        self.assertIn("morning_rmssd", result["missing"])
        self.assertIn("sleep_score", result["missing"])

    def test_empty_latest_returns_safe_result(self):
        result = recovery_explain.generate_recovery_explanation(None, {})

        self.assertEqual(result["summary"], "暂无评分数据")
        self.assertEqual(result["positive"], [])
        self.assertEqual(len(result["missing"]), len(recovery_explain.METRIC_RULES))


if __name__ == "__main__":
    unittest.main()
