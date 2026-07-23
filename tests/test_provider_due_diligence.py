import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


class ProviderDueDiligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = (BASE_DIR / "docs" / "PROVIDER_DUE_DILIGENCE.md").read_text(encoding="utf-8")

    def test_questionnaire_has_all_stable_ids(self):
        for number in range(1, 25):
            self.assertIn(f"`DD-{number:02d}`", self.document)

    def test_gate_is_conjunctive_and_unknown_does_not_pass(self):
        self.assertIn("conjunctive gate", self.document)
        self.assertIn("Every mandatory control must", self.document)
        for result in ("`UNKNOWN`", "`PARTIAL`", "`EXCEPTION`"):
            self.assertIn(result, self.document)

    def test_contract_red_lines_cover_retention_and_reuse(self):
        for phrase in ("beyond transient inference", "model improvement", "routine human review", "cross-customer reuse", "unspecified processing locations"):
            self.assertIn(phrase, self.document)

    def test_evidence_record_keeps_authorization_off_by_default(self):
        self.assertIn("Implementation authorization: NO / YES", self.document)
        self.assertIn("remains `NO` unless every mandatory gate passes", self.document)
        self.assertIn("does not cover another", self.document)

    def test_revalidation_and_expiry_fail_closed(self):
        self.assertIn("at least annually", self.document)
        self.assertIn("evidence older than 12 months", self.document)
        self.assertIn("fail closed", self.document)

    def test_package_prohibits_real_data_and_secrets(self):
        self.assertIn("Use synthetic examples only", self.document)
        self.assertIn("Do not put API keys", self.document)
        self.assertIn("does not accept contracts", self.document)
        self.assertNotIn("sk-", self.document)


if __name__ == "__main__":
    unittest.main()
