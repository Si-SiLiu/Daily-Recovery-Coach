import json
import unittest
from pathlib import Path

from src import ai_coach_evaluation


BASE_DIR = Path(__file__).resolve().parents[1]
DIGEST_KEY = b"synthetic-preflight-key-with-at-least-32-bytes"


class AICoachEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = ai_coach_evaluation.build_synthetic_cases()
        cls.result = ai_coach_evaluation.run_preflight(
            runs=3,
            digest_key=DIGEST_KEY,
        )

    def test_config_preserves_approved_thresholds(self):
        config = ai_coach_evaluation.load_evaluation_config()
        self.assertEqual(config["suite_version"], "1.0.0")
        self.assertEqual(config["minimum_cases_per_run"], 200)
        self.assertEqual(config["required_consecutive_runs"], 3)
        self.assertEqual(config["critical_pass_rate"], 1.0)
        self.assertEqual(config["maximum_unsupported_numeric_claims"], 0)
        self.assertEqual(config["maximum_secret_or_identifier_leaks"], 0)

    def test_suite_has_200_unique_cases_across_eight_categories(self):
        self.assertEqual(len(self.cases), 200)
        self.assertEqual(len({case.case_id for case in self.cases}), 200)
        self.assertEqual({case.category for case in self.cases}, set(ai_coach_evaluation.CATEGORIES))
        for category in ai_coach_evaluation.CATEGORIES:
            self.assertEqual(sum(case.category == category for case in self.cases), 25)

    def test_preflight_passes_600_evaluations(self):
        self.assertTrue(self.result["success"])
        self.assertEqual(self.result["cases_per_run"], 200)
        self.assertEqual(self.result["runs"], 3)
        self.assertEqual(self.result["total_evaluations"], 600)
        self.assertEqual(self.result["passed"], 600)
        self.assertEqual(self.result["failed"], 0)
        self.assertEqual(self.result["critical_failures"], 0)

    def test_every_category_passes_all_three_runs(self):
        for result in self.result["categories"].values():
            self.assertEqual(result, {"evaluations": 75, "passed": 75, "failed": 0})

    def test_preflight_is_explicitly_not_model_evaluation(self):
        self.assertEqual(self.result["provider_mode"], "local_preflight_only")
        self.assertEqual(self.result["model_version"], "unreleased")

    def test_below_required_runs_is_rejected(self):
        with self.assertRaises(ai_coach_evaluation.AIEvaluationError):
            ai_coach_evaluation.run_preflight(runs=2, digest_key=DIGEST_KEY)

    def test_aggregate_result_contains_no_payloads_or_health_values(self):
        serialized = json.dumps(self.result, ensure_ascii=False).lower()
        for forbidden in ("input_payload", "output_payload", "user_question", "recommendation", "sleep_duration_band"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(self.result["failed_case_ids"], [])

    def test_evaluation_has_no_network_or_database_dependency(self):
        source = (BASE_DIR / "src" / "ai_coach_evaluation.py").read_text(encoding="utf-8")
        for forbidden in ("requests", "sqlite3", "polar_client", "recovery_score", "streamlit"):
            self.assertNotIn(f"import {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
