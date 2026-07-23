import json
import unittest

from scripts import update_project_state


class VersioningTests(unittest.TestCase):
    def test_unified_version_source_is_valid(self):
        versions = update_project_state.load_versions()
        self.assertEqual(
            set(versions),
            {
                "app_version",
                "recovery_engine_version",
                "baseline_engine_version",
                "confidence_engine_version",
                "local_coach_engine_version",
                "personal_logging_version",
                "nutrition_logging_engine_version",
                "food_catalog_version",
                "training_logging_version",
                "training_entry_ui_version",
                "exercise_catalog_version",
                "supplement_unit_system_version",
                "supplement_catalog_version",
                "supplement_product_enrichment_version",
                "manual_logging_engine_version",
                "data_resolution_version",
                "scheduler_version",
                "ai_context_export_version",
                "i18n_engine_version",
                "kubios_screenshot_import_version",
                "kubios_data_model_version",
                "database_schema_version",
                "dashboard_version",
                "model_version",
            },
        )

    def test_project_state_versions_match_version_source(self):
        versions = update_project_state.load_versions()
        state = json.loads(update_project_state.STATE_PATH.read_text(encoding="utf-8"))
        for key, value in versions.items():
            self.assertEqual(state.get(key), value)


if __name__ == "__main__":
    unittest.main()
