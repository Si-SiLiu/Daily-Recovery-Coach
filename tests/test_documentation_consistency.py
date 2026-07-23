import json
import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


class DocumentationConsistencyTests(unittest.TestCase):
    def test_governance_documents_exist(self):
        for relative in (
            "docs/CURRENT_STATE.md",
            "docs/HANDOFF.md",
            "docs/QUALITY_GATE.md",
            "docs/VERSIONING.md",
            "releases/README.md",
        ):
            path = BASE_DIR / relative
            self.assertTrue(path.is_file(), relative)
            self.assertTrue(path.read_text(encoding="utf-8").strip(), relative)

    def test_project_state_excludes_sensitive_fields(self):
        state = json.loads((BASE_DIR / "project_state.json").read_text(encoding="utf-8"))
        serialized = json.dumps(state, ensure_ascii=False).lower()
        for forbidden in ("access_token", "refresh_token", "client_secret"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
