import json
import tempfile
import unittest
from pathlib import Path

from src import db
from src.ai_context.builder import build_ai_context
from src.ai_context.exporter import export_ai_context, render_csv, render_markdown
from src.ai_context.schemas import validate_export
from src.personal_logging.storage import create_body_measurement, create_nutrition_log, create_workout_session
from src.personal_logging.summaries import rebuild_daily_summaries


class AIContextExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.connection = db.connect(Path(self.temp.name) / "test.db")
        create_body_measurement(self.connection, {
            "date": "2026-07-01", "height_cm": 170, "weight_kg": 60,
            "notes": "synthetic private note",
        })
        create_nutrition_log(self.connection, {
            "date": "2026-07-01", "meal_type": "lunch", "food_name": "synthetic food",
            "calories": 500, "protein_g": None,
        })
        create_workout_session(self.connection, {
            "date": "2026-07-01", "session_type": "hiphop", "duration_minutes": 60,
            "session_rpe": 7, "notes": "synthetic workout note",
        })
        rebuild_daily_summaries(self.connection, "2026-07-01")

    def tearDown(self):
        self.connection.close()
        self.temp.cleanup()

    def test_whitelist_schema_missing_and_status(self):
        payload = build_ai_context(self.connection, "2026-07-01")
        self.assertIs(validate_export(payload), payload)
        self.assertEqual(payload["nutrition_summary"]["protein_g"]["value"], None)
        self.assertEqual(payload["nutrition_summary"]["protein_g"]["status"], "missing")

    def test_forbidden_fields_and_notes_are_absent(self):
        serialized = json.dumps(build_ai_context(self.connection, "2026-07-01"), ensure_ascii=False).lower()
        for forbidden in ("token", "secret", "raw_json", "/users/", "synthetic private note", "database_path"):
            self.assertNotIn(forbidden, serialized)
        self.assertNotIn("nightly_hrv_rmssd", serialized)

    def test_free_text_requires_two_confirmations_and_remains_excluded(self):
        with self.assertRaises(ValueError):
            build_ai_context(self.connection, "2026-07-01", include_free_text=True, first_confirmation=True)
        payload = build_ai_context(self.connection, "2026-07-01", include_free_text=True,
                                   first_confirmation=True, second_confirmation=True)
        self.assertNotIn("notes", json.dumps(payload).lower())

    def test_sensitive_question_is_rejected(self):
        with self.assertRaises(ValueError):
            build_ai_context(self.connection, "2026-07-01", questions=["token abc"])

    def test_supported_ranges_and_invalid_range(self):
        for days in (1, 7, 14, 30):
            self.assertEqual(build_ai_context(self.connection, "2026-07-01", days)["range_days"], days)
        with self.assertRaises(ValueError):
            build_ai_context(self.connection, "2026-07-01", 2)

    def test_json_markdown_and_csv_render(self):
        payload = build_ai_context(self.connection, "2026-07-01", questions=["今天训练量合理吗？"])
        self.assertIn("AI Context", render_markdown(payload))
        self.assertIn("schema_version", render_csv(payload))

    def test_dry_run_does_not_write(self):
        output = Path(self.temp.name) / "exports"
        result = export_ai_context(self.connection, "2026-07-01", output_dir=output, dry_run=True)
        self.assertFalse(result["written"])
        self.assertFalse(output.exists())

    def test_write_requires_confirmation_and_creates_three_formats(self):
        output = Path(self.temp.name) / "exports"
        with self.assertRaises(ValueError):
            export_ai_context(self.connection, "2026-07-01", output_dir=output, dry_run=False)
        result = export_ai_context(self.connection, "2026-07-01", output_dir=output,
                                   dry_run=False, confirmed=True)
        self.assertEqual(set(result["paths"]), {"json", "md", "csv"})
        self.assertTrue(all(path.is_file() for path in result["paths"].values()))

    def test_module_has_no_network_dependency(self):
        for relative in ("src/ai_context/builder.py", "src/ai_context/exporter.py", "src/ai_context/safety.py"):
            source = (db.BASE_DIR / relative).read_text(encoding="utf-8")
            for forbidden in ("requests", "urllib", "httpx", "openai"):
                self.assertNotIn(f"import {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
