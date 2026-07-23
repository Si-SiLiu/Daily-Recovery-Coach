import tempfile
import unittest
from pathlib import Path

from src import baseline


class BaselineConfigTests(unittest.TestCase):
    def test_load_config_contains_required_fields(self):
        config = baseline.load_baseline_config()

        self.assertEqual(config["default_window_days"], 28)
        self.assertEqual(config["minimum_valid_days"], 7)
        self.assertEqual(config["outlier_method"], "median_mad")
        self.assertIn("robust_z_thresholds", config)

        metric_names = {metric["name"] for metric in config["metrics"]}
        for metric_name in (
            "nightly_hrv_rmssd",
            "nightly_resting_hr",
            "respiration_rate",
            "morning_rmssd",
            "morning_mean_hr",
            "kubios_readiness",
            "sleep_duration",
            "sleep_score",
            "active_calories",
            "training_duration",
            "training_calories",
            "steps",
        ):
            self.assertIn(metric_name, metric_names)

    def test_load_config_rejects_missing_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline_config.json"
            path.write_text('{"default_window_days": 28}', encoding="utf-8")

            with self.assertRaises(ValueError):
                baseline.load_baseline_config(path)


if __name__ == "__main__":
    unittest.main()
