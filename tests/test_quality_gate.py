import unittest
from pathlib import Path


class QualityGateDocumentationTests(unittest.TestCase):
    def test_quality_gate_contains_required_sections_and_template(self):
        path = Path(__file__).resolve().parents[1] / "docs" / "QUALITY_GATE.md"
        self.assertTrue(path.is_file())
        document = path.read_text(encoding="utf-8")
        for heading in (
            "Scope Compliance",
            "Security",
            "Code Quality",
            "Tests",
            "State Governance",
            "Documentation",
            "Real Data Verification",
            "Release Readiness",
            "Approval",
            "Gate Result",
            "Reusable Quality Gate Template",
        ):
            self.assertIn(f"## {heading}", document)
        for result in ("PASS", "PASS WITH CONDITIONS", "FAIL"):
            self.assertIn(result, document)


if __name__ == "__main__":
    unittest.main()
