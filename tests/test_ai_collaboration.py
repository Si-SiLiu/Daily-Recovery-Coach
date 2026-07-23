import json
import tempfile
import unittest
from pathlib import Path

from scripts import update_project_state, verify_ai_collaboration


class AICollaborationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = json.loads(
            update_project_state.STATE_PATH.read_text(encoding="utf-8")
        )

    def test_handoff_has_required_sections_in_order(self):
        _, sections = verify_ai_collaboration.parse_handoff()
        self.assertEqual(
            list(sections),
            verify_ai_collaboration.REQUIRED_HANDOFF_SECTIONS,
        )

    def test_handoff_matches_project_state(self):
        sections = verify_ai_collaboration.validate_handoff(self.state)
        self.assertIn(
            self.state["next_goal"],
            sections["Recommended Next Phase"],
        )

    def test_handoff_rejects_placeholders_and_sensitive_assignments(self):
        source = verify_ai_collaboration.HANDOFF_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            placeholder_path = Path(directory) / "placeholder.md"
            placeholder_path.write_text(
                source.replace("## Status\n", "## Status\n\n<fill this in>\n", 1),
                encoding="utf-8",
            )
            with self.assertRaises(
                verify_ai_collaboration.CollaborationVerificationError
            ):
                verify_ai_collaboration.parse_handoff(placeholder_path)

            secret_path = Path(directory) / "secret.md"
            secret_path.write_text(
                source + "\nclient_secret = forbidden-value\n",
                encoding="utf-8",
            )
            with self.assertRaises(
                verify_ai_collaboration.CollaborationVerificationError
            ):
                verify_ai_collaboration.validate_handoff(
                    self.state,
                    document_path=secret_path,
                )

    def test_architecture_boundaries_are_enforced(self):
        verify_ai_collaboration.validate_architecture_boundaries()

        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "dashboard.py"
            source_path.write_text("import src.polar_client\n", encoding="utf-8")
            imports = verify_ai_collaboration.imported_modules(source_path)
            self.assertIn("src.polar_client", imports)

            original_rules = verify_ai_collaboration.ARCHITECTURE_IMPORT_RULES
            verify_ai_collaboration.ARCHITECTURE_IMPORT_RULES = {
                source_path: {"polar_client"}
            }
            try:
                with self.assertRaises(
                    verify_ai_collaboration.CollaborationVerificationError
                ):
                    verify_ai_collaboration.validate_architecture_boundaries()
            finally:
                verify_ai_collaboration.ARCHITECTURE_IMPORT_RULES = original_rules

    def test_authority_map_is_complete(self):
        verify_ai_collaboration.validate_authority_map()
        for path in verify_ai_collaboration.AUTHORITATIVE_FILES.values():
            self.assertTrue(path.exists())

    def test_full_collaboration_verification_passes(self):
        verified = verify_ai_collaboration.verify_all()
        self.assertEqual(verified["current_phase"], self.state["current_phase"])


if __name__ == "__main__":
    unittest.main()
