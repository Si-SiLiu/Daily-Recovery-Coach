import json
import tempfile
import unittest
from pathlib import Path

from src.sport_catalog import load_sport_catalog, resolve_sport_name


class SportCatalogTests(unittest.TestCase):
    def test_numeric_identifier_uses_localized_cached_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sports.json"
            path.write_text(json.dumps({"sports": [{
                "id": {"id": "121"},
                "name": "Running",
                "localizedNames": {"zh": {"longName": "跑步"}},
            }]}), encoding="utf-8")
            self.assertEqual(load_sport_catalog(path)["121"], "跑步")
            self.assertEqual(resolve_sport_name("121", path=path), "表演舞")

    def test_user_confirmed_identifiers_override_cached_catalog(self):
        self.assertEqual(resolve_sport_name(121), "表演舞")
        self.assertEqual(resolve_sport_name(36), "田径运动")
        self.assertEqual(resolve_sport_name(83), "室内活动")
        self.assertEqual(resolve_sport_name(15), "力量训练")

    def test_unknown_numeric_identifier_is_not_rendered_as_bare_number(self):
        with tempfile.TemporaryDirectory() as directory:
            value = resolve_sport_name("999", path=Path(directory) / "missing.json")
        self.assertEqual(value, "未知运动（ID 999）")


if __name__ == "__main__":
    unittest.main()
