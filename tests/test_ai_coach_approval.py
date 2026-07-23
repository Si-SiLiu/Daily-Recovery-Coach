import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src import ai_coach_approval


BASE_DIR = Path(__file__).resolve().parents[1]
NOW = datetime.fromisoformat("2030-06-01T00:00:00+00:00")


def approved_record():
    record = {
        "approval_record_version": "1.0.0",
        "status": "approved",
        "implementation_authorization": True,
        "provider_id": "synthetic-provider",
        "model_snapshot": "synthetic-model-2030-01-01",
        "endpoint": "https://api.synthetic.example/v1/responses",
        "processing_region": "synthetic-region",
        "region_supported": True,
        "zdr_verified": True,
        "no_training_verified": True,
        "human_review_disabled": True,
        "subprocessors_accepted": True,
        "retention_terms_accepted": True,
        "product_owner_approval": "approved",
        "chief_architect_review": "approved",
        "evidence_effective_at": "2030-01-01T00:00:00+00:00",
        "evidence_expires_at": "2031-01-01T00:00:00+00:00",
        "configuration_fingerprint": None,
        "blocked_reason": None,
    }
    record["configuration_fingerprint"] = ai_coach_approval.configuration_fingerprint(record)
    return record


def write_record(directory, record):
    path = Path(directory) / "approval.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


class AICoachApprovalTests(unittest.TestCase):
    def test_committed_record_is_strictly_blocked(self):
        record = ai_coach_approval.load_provider_approval()
        self.assertEqual(record["status"], "blocked")
        self.assertFalse(record["implementation_authorization"])
        self.assertIsNone(record["provider_id"])
        self.assertFalse(ai_coach_approval.cloud_call_allowed(now=NOW))

    def test_partial_blocked_record_is_rejected(self):
        record = ai_coach_approval.load_provider_approval()
        record["provider_id"] = "partial-provider"
        with tempfile.TemporaryDirectory() as directory:
            path = write_record(directory, record)
            with self.assertRaises(ai_coach_approval.AIApprovalError):
                ai_coach_approval.load_provider_approval(path)

    def test_complete_synthetic_approval_passes(self):
        record = approved_record()
        with tempfile.TemporaryDirectory() as directory:
            path = write_record(directory, record)
            result = ai_coach_approval.require_cloud_call_approval(now=NOW, path=path)
            self.assertEqual(result, record)
            self.assertIsNot(result, record)
            self.assertTrue(ai_coach_approval.cloud_call_allowed(now=NOW, path=path))

    def test_expired_or_not_yet_effective_evidence_fails(self):
        for now in (
            datetime.fromisoformat("2029-12-31T23:59:59+00:00"),
            datetime.fromisoformat("2031-01-01T00:00:00+00:00"),
        ):
            record = approved_record()
            with tempfile.TemporaryDirectory() as directory:
                path = write_record(directory, record)
                self.assertFalse(ai_coach_approval.cloud_call_allowed(now=now, path=path))

    def test_endpoint_must_be_exact_https_without_redirect_material(self):
        for endpoint in (
            "http://api.synthetic.example/v1/responses",
            "https://user:pass@api.synthetic.example/v1/responses",
            "https://api.synthetic.example/v1/responses?region=other",
            "https://api.synthetic.example/v1/responses#fragment",
        ):
            record = approved_record()
            record["endpoint"] = endpoint
            record["configuration_fingerprint"] = ai_coach_approval.configuration_fingerprint(record)
            with tempfile.TemporaryDirectory() as directory:
                path = write_record(directory, record)
                self.assertFalse(ai_coach_approval.cloud_call_allowed(now=NOW, path=path))

    def test_configuration_drift_fails(self):
        record = approved_record()
        record["model_snapshot"] = "changed-after-approval"
        with tempfile.TemporaryDirectory() as directory:
            path = write_record(directory, record)
            self.assertFalse(ai_coach_approval.cloud_call_allowed(now=NOW, path=path))

    def test_every_control_and_both_reviews_are_required(self):
        fields = list(ai_coach_approval.CONTROL_FIELDS) + [
            "product_owner_approval",
            "chief_architect_review",
        ]
        for field in fields:
            record = approved_record()
            record[field] = False if field in ai_coach_approval.CONTROL_FIELDS else "pending"
            record["configuration_fingerprint"] = ai_coach_approval.configuration_fingerprint(record)
            with tempfile.TemporaryDirectory() as directory:
                path = write_record(directory, record)
                self.assertFalse(ai_coach_approval.cloud_call_allowed(now=NOW, path=path))

    def test_naive_now_is_rejected(self):
        record = approved_record()
        with tempfile.TemporaryDirectory() as directory:
            path = write_record(directory, record)
            with self.assertRaises(ai_coach_approval.AIApprovalError):
                ai_coach_approval.require_cloud_call_approval(
                    now=datetime.fromisoformat("2030-06-01T00:00:00"),
                    path=path,
                )

    def test_error_never_exposes_provider_or_endpoint(self):
        record = approved_record()
        record["configuration_fingerprint"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = write_record(directory, record)
            try:
                ai_coach_approval.require_cloud_call_approval(now=NOW, path=path)
            except ai_coach_approval.AIApprovalError as exc:
                self.assertEqual(str(exc), "AI cloud call is not authorized")
                self.assertNotIn(record["provider_id"], str(exc))
                self.assertNotIn(record["endpoint"], str(exc))
            else:
                self.fail("Drifted approval was not rejected")

    def test_gate_has_no_network_database_or_secret_dependency(self):
        source = (BASE_DIR / "src" / "ai_coach_approval.py").read_text(encoding="utf-8")
        for forbidden in ("requests", "sqlite3", "polar_client", "recovery_score", "streamlit", "os.environ"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
