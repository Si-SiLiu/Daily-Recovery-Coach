import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


class AICoachCloudGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = (BASE_DIR / "docs" / "AI_COACH.md").read_text(encoding="utf-8")
        cls.decisions = (BASE_DIR / "docs" / "DECISIONS.md").read_text(encoding="utf-8")

    def test_cloud_contract_is_closed_and_minimized(self):
        for field in ("`analysis_date`", "`recovery`", "`confidence`", "`daily_metrics`", "`baseline_context`", "`user_question`", "`presentation`", "`contract_versions`"):
            self.assertIn(field, self.design)
        self.assertIn("reject unknown fields", self.design)
        self.assertIn("no historical series", self.design)

    def test_provider_retention_is_fail_closed(self):
        self.assertIn("Zero Data Retention is required", self.design)
        self.assertIn("adapter fails", self.design)
        self.assertIn("no request is sent", self.design)
        self.assertIn("never persisted verbatim", self.design)

    def test_local_retention_has_content_and_metadata_expiry(self):
        self.assertIn("90 days", self.design)
        self.assertIn("365 days", self.design)
        for field in ("content_expires_at", "metadata_expires_at", "deleted_at"):
            self.assertIn(f"`{field}`", self.design)

    def test_migration_plan_is_not_executed(self):
        self.assertIn("migration `0.4.0`", self.design)
        self.assertIn("This design does not execute that migration", self.design)
        self.assertIn("`ai_coach_audit`", self.design)

    def test_safety_thresholds_are_hard_release_gates(self):
        self.assertIn("at least 200 synthetic cases", self.design)
        self.assertIn("three consecutive runs", self.design)
        self.assertIn("at least 98%", self.design)
        self.assertIn("at least 95%", self.design)
        self.assertIn("0 unsupported numeric health claims", self.design)
        self.assertIn("Any critical-category failure blocks release", self.design)

    def test_governance_adrs_are_accepted(self):
        for adr in ("ADR-023", "ADR-024", "ADR-025"):
            self.assertIn(f"## {adr}", self.decisions)
        self.assertGreaterEqual(self.decisions.count("- 状态：Accepted。"), 7)


if __name__ == "__main__":
    unittest.main()
