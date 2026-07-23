import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts import update_project_state


class ProjectStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = json.loads(
            update_project_state.STATE_PATH.read_text(encoding="utf-8")
        )

    def test_json_schema_is_complete_and_typed(self):
        self.assertEqual(
            update_project_state.REQUIRED_FIELDS - set(self.state),
            set(),
        )
        for key in (
            "app_version",
            "current_phase",
            "phase_status",
            "recovery_engine_version",
            "database_schema_version",
            "dashboard_version",
            "baseline_engine_version",
            "personal_logging_version",
            "nutrition_logging_engine_version",
            "food_catalog_version",
            "training_logging_version",
            "exercise_catalog_version",
            "training_entry_ui_version",
            "training_entry_default_mode",
            "supplement_unit_system_version",
            "supplement_catalog_version",
            "supplement_product_enrichment_version",
            "supplement_enrichment_runtime_status",
            "manual_logging_engine_version",
            "data_resolution_version",
            "scheduler_version",
            "scheduled_sync_time",
            "ai_context_export_version",
            "i18n_engine_version",
            "kubios_screenshot_import_version",
            "kubios_data_model_version",
            "default_language",
            "current_language",
            "translation_coverage",
            "next_goal",
            "updated_at",
            "generated_by",
        ):
            self.assertIsInstance(self.state[key], str)
            self.assertTrue(self.state[key])
        for key in (
            "test_total",
            "test_passed",
            "test_failed",
            "baseline_record_count",
            "scored_day_count",
            "recovery_v1_day_count",
            "daily_metric_day_count",
            "schema_migration_count",
            "body_measurement_count",
            "nutrition_log_count",
            "workout_session_count",
            "exercise_set_count",
            "ai_context_export_count",
            "translation_key_count",
            "kubios_screenshot_count",
            "kubios_screenshot_imported_count",
            "kubios_screenshot_review_pending_count",
            "kubios_raw_measurement_count",
            "kubios_normalized_count",
            "kubios_derived_count",
            "manual_activity_count",
            "manual_sleep_count",
            "manual_recovery_count",
            "resolved_field_count",
            "supplement_catalog_count",
            "food_catalog_count",
            "meal_record_count",
            "meal_item_count",
            "meal_template_count",
            "training_session_count",
            "training_exercise_count",
            "training_set_count",
            "supplement_product_count",
            "verified_supplement_product_count",
            "unverified_supplement_product_count",
            "supplement_ingredient_count",
        ):
            self.assertIsInstance(self.state[key], int)
            self.assertGreaterEqual(self.state[key], 0)
        self.assertIsInstance(self.state["latest_schema_migration"], str)
        self.assertEqual(
            self.state["latest_schema_migration"],
            self.state["database_schema_version"],
        )
        self.assertIsInstance(self.state["test_success"], bool)
        self.assertIsInstance(self.state["simple_nutrition_input_ready"], bool)
        self.assertIsInstance(self.state["structured_training_ready"], bool)
        self.assertIsInstance(self.state["conditional_training_fields_ready"], bool)
        self.assertIsInstance(self.state["rpe_rir_preference_supported"], bool)
        self.assertIsInstance(self.state["simplified_training_entry_ready"], bool)
        self.assertIsInstance(self.state["brand_based_supplement_logging_ready"], bool)
        datetime.fromisoformat(self.state["updated_at"])
        self.assertEqual(
            self.state["generated_by"],
            "scripts/update_project_state.py",
        )

    def test_database_counts_and_dates_match_read_only_database(self):
        uri = f"file:{update_project_state.DB_PATH.resolve()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            expected_counts = {
                table: connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                for table in update_project_state.COUNTED_TABLES
            }
            dates = connection.execute(
                "SELECT MIN(date), MAX(date), COUNT(*) FROM daily_recovery_metrics"
            ).fetchone()
            recovery_v1 = connection.execute(
                """
                SELECT COUNT(*) FROM recovery_scores
                WHERE score_version IN ('v1.0', '1.0.0')
                """
            ).fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(self.state["table_record_counts"], expected_counts)
        self.assertEqual(
            self.state["baseline_record_count"],
            expected_counts["baseline_metrics"],
        )
        self.assertEqual(
            self.state["scored_day_count"],
            expected_counts["recovery_scores"],
        )
        self.assertEqual(self.state["recovery_v1_day_count"], recovery_v1)
        self.assertEqual(self.state["earliest_data_date"], dates[0])
        self.assertEqual(self.state["latest_data_date"], dates[1])
        self.assertEqual(self.state["daily_metric_day_count"], dates[2])
        migration = sqlite3.connect(uri, uri=True)
        try:
            migration.row_factory = sqlite3.Row
            row = migration.execute(
                "SELECT COUNT(*) AS count, (SELECT version FROM schema_migrations ORDER BY sequence DESC LIMIT 1) AS version FROM schema_migrations"
            ).fetchone()
        finally:
            migration.close()
        self.assertEqual(self.state["schema_migration_count"], row["count"])
        self.assertEqual(self.state["latest_schema_migration"], row["version"])

    def test_unittest_counts_are_valid_and_current(self):
        self.assertEqual(
            self.state["test_total"],
            self.state["test_passed"]
            + self.state["test_failed"],
        )
        self.assertEqual(self.state["test_failed"], 0)
        self.assertEqual(
            self.state["test_success"],
            self.state["test_failed"] == 0,
        )
        self.assertEqual(
            self.state["test_total"],
            update_project_state.discover_test_total(),
        )

        parsed_ok = update_project_state.parse_unittest_result(
            "Ran 5 tests in 0.1s\n\nOK\n"
        )
        self.assertEqual(parsed_ok["test_passed"], 5)
        self.assertEqual(parsed_ok["test_failed"], 0)
        self.assertTrue(parsed_ok["test_success"])

        parsed_failed = update_project_state.parse_unittest_result(
            "Ran 5 tests in 0.1s\n\nFAILED (failures=1, errors=1)\n"
        )
        self.assertEqual(parsed_failed["test_passed"], 3)
        self.assertEqual(parsed_failed["test_failed"], 2)
        self.assertFalse(parsed_failed["test_success"])

    def test_current_state_matches_and_auto_sync_repairs_drift(self):
        update_project_state.validate_current_state(self.state)

        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "CURRENT_STATE.md"
            output_path = Path(directory) / "UPDATED.md"
            source = update_project_state.CURRENT_STATE_PATH.read_text(
                encoding="utf-8"
            ).replace(
                f"- Test Total: {self.state['test_total']}",
                "- Test Total: 999999",
            )
            source_path.write_text(source, encoding="utf-8")

            with self.assertRaises(update_project_state.ProjectStateError):
                update_project_state.validate_current_state(
                    self.state,
                    document_path=source_path,
                )

            update_project_state.sync_current_state(
                self.state,
                document_path=source_path,
                output_path=output_path,
            )
            update_project_state.validate_current_state(
                self.state,
                document_path=output_path,
            )

    def test_prioritized_issues_and_state_are_secret_safe(self):
        update_project_state.validate_prioritized_issues(
            self.state["prioritized_issues"]
        )
        self.assertEqual(
            self.state["known_issues"],
            [
                issue["description"]
                for issue in self.state["prioritized_issues"]
            ],
        )
        serialized = json.dumps(self.state, ensure_ascii=False).lower()
        for forbidden in ("access_token", "refresh_token", "client_secret"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
