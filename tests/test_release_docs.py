import json
import re
import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


class ReleaseDocumentationTests(unittest.TestCase):
    def test_current_release_matches_version_source(self):
        versions = json.loads(
            (BASE_DIR / "config" / "versions.json").read_text(encoding="utf-8")
        )
        release_path = BASE_DIR / "releases" / f"{versions['app_version']}.md"
        self.assertTrue(release_path.is_file())
        document = release_path.read_text(encoding="utf-8")
        self.assertIn(f"- Version: {versions['app_version']}", document)
        for value in (
            versions["recovery_engine_version"],
            versions["baseline_engine_version"],
            versions["database_schema_version"],
            versions["dashboard_version"],
        ):
            self.assertIn(value, document)
        self.assertRegex(document, r"(?i)pre-1\.0")
        self.assertRegex(document, r"(?i)not a medical device|不是医疗器械")

    def test_release_readme_defines_filename_contract(self):
        document = (BASE_DIR / "releases" / "README.md").read_text(encoding="utf-8")
        self.assertIn("VERSION.md", document)
        self.assertIn("CHANGELOG", document)
        self.assertIsNotNone(re.search(r"formal release snapshot", document, re.I))


if __name__ == "__main__":
    unittest.main()
