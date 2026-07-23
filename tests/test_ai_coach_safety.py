import copy
import unittest
from pathlib import Path

from src import ai_coach_safety
from tests.test_ai_coach_contract import valid_input, valid_output


BASE_DIR = Path(__file__).resolve().parents[1]
DIGEST_KEY = b"synthetic-test-key-not-a-real-secret-32bytes"
GENERATED_AT = "2026-07-11T10:00:00+08:00"


class AICoachSafetyTests(unittest.TestCase):
    def test_policy_version_matches_contract(self):
        policy = ai_coach_safety.load_safety_policy()
        self.assertEqual(policy["safety_policy_version"], "1.0.0")
        self.assertIn("safety_blocked", policy["fallback_reason_codes"])

    def test_valid_grounded_high_confidence_output_passes(self):
        result = ai_coach_safety.validate_semantic_safety(valid_input(), valid_output())
        self.assertEqual(result, valid_output())
        self.assertIsNot(result, valid_output())

    def test_unknown_evidence_and_numeric_claim_fail(self):
        payload = valid_output()
        payload["evidence"][0]["fact_id"] = "invented_metric"
        with self.assertRaises(ai_coach_safety.AISafetyError):
            ai_coach_safety.validate_semantic_safety(valid_input(), payload)

        payload = valid_output()
        payload["summary"] = "建议恢复分数提高到八十分以外的 80。"
        with self.assertRaises(ai_coach_safety.AISafetyError):
            ai_coach_safety.validate_semantic_safety(valid_input(), payload)

    def test_diagnosis_and_medication_directives_fail(self):
        for unsafe in ("你患有某种疾病。", "建议开始服用某种药物。"):
            payload = valid_output()
            payload["summary"] = unsafe
            with self.assertRaises(ai_coach_safety.AISafetyError):
                ai_coach_safety.validate_semantic_safety(valid_input(), payload)

    def test_confidence_language_rules_fail_closed(self):
        input_payload = valid_input()
        input_payload["confidence"]["level"] = "medium"
        output_payload = valid_output()
        output_payload["limitations"] = []
        with self.assertRaises(ai_coach_safety.AISafetyError):
            ai_coach_safety.validate_semantic_safety(input_payload, output_payload)

        input_payload["confidence"]["level"] = "very_low"
        output_payload["limitations"] = ["当前证据有限。"]
        with self.assertRaises(ai_coach_safety.AISafetyError):
            ai_coach_safety.validate_semantic_safety(input_payload, output_payload)

    def test_urgent_question_requires_escalation_and_no_actions(self):
        input_payload = valid_input()
        input_payload["user_question"] = "我现在胸痛并且呼吸困难，怎么办？"
        with self.assertRaises(ai_coach_safety.AISafetyError):
            ai_coach_safety.validate_semantic_safety(input_payload, valid_output())

        output_payload = valid_output()
        output_payload["suggested_actions"] = []
        output_payload["safety_notice"] = "请立即联系当地急救服务。"
        result = ai_coach_safety.validate_semantic_safety(input_payload, output_payload)
        self.assertEqual(result["suggested_actions"], [])

    def test_keyed_digest_is_stable_and_key_sensitive(self):
        first = ai_coach_safety.input_snapshot_digest(valid_input(), DIGEST_KEY)
        second = ai_coach_safety.input_snapshot_digest(valid_input(), DIGEST_KEY)
        other = ai_coach_safety.input_snapshot_digest(valid_input(), b"another-synthetic-key-with-32-bytes-minimum")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertEqual(len(first), 64)
        with self.assertRaises(ai_coach_safety.AISafetyError):
            ai_coach_safety.input_snapshot_digest(valid_input(), b"short")

    def test_deterministic_fallback_is_schema_and_semantic_valid(self):
        input_payload = valid_input()
        input_payload["confidence"]["level"] = "low"
        input_payload["confidence"]["missing_groups"] = ["sleep"]
        result = ai_coach_safety.build_deterministic_fallback(
            input_payload,
            "provider_unavailable",
            GENERATED_AT,
            DIGEST_KEY,
        )
        self.assertEqual(result["audit"]["model_version"], "deterministic-fallback")
        self.assertEqual(result["suggested_actions"], [])
        self.assertGreaterEqual(len(result["limitations"]), 2)

    def test_safe_wrapper_replaces_invalid_model_output(self):
        output_payload = valid_output()
        output_payload["evidence"][0]["fact_id"] = "invented_metric"
        result, is_fallback = ai_coach_safety.safe_output_or_fallback(
            valid_input(), output_payload, GENERATED_AT, DIGEST_KEY
        )
        self.assertTrue(is_fallback)
        self.assertEqual(result["audit"]["model_version"], "deterministic-fallback")

    def test_safety_module_has_no_network_or_database_dependency(self):
        source = (BASE_DIR / "src" / "ai_coach_safety.py").read_text(encoding="utf-8")
        for forbidden in ("requests", "sqlite3", "polar_client", "recovery_score", "streamlit"):
            self.assertNotIn(f"import {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
