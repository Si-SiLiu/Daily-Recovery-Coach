import sqlite3
import tempfile
import unittest
from pathlib import Path

from src import db
from src.personal_logging.body import calculate_bmi, weight_change, weight_trend
from src.personal_logging.nutrition import summarize_nutrition_rows
from src.personal_logging.storage import (
    add_from_nutrition_template,
    copy_nutrition_date,
    create_batch_sets,
    create_body_measurement,
    create_exercise_set,
    create_nutrition_log,
    create_session_link,
    create_workout_session,
    delete_body_measurement,
    delete_nutrition_log,
    delete_workout_session,
    list_body_measurements,
    list_exercise_sets,
    list_nutrition_logs,
    list_workout_sessions,
    save_nutrition_template,
    update_body_measurement,
    update_nutrition_log,
    update_workout_session,
)
from src.personal_logging.summaries import rebuild_daily_summaries
from src.personal_logging.training import session_rpe_load, set_volume


class PersonalLoggingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.db"
        self.connection = db.connect(self.path)

    def tearDown(self):
        self.connection.close()
        self.temp.cleanup()

    def body(self, date="2026-07-01", weight=60.0, height=170.0, **extra):
        return create_body_measurement(self.connection, {
            "date": date, "weight_kg": weight, "height_cm": height, **extra,
        })

    def test_body_crud_primary_and_bmi(self):
        record_id = self.body(is_primary=True)
        self.assertEqual(len(list_body_measurements(self.connection)), 1)
        self.assertTrue(update_body_measurement(self.connection, record_id, {"weight_kg": 61.0}))
        self.assertEqual(calculate_bmi(61, 170), 21.1)
        self.assertTrue(delete_body_measurement(self.connection, record_id))

    def test_height_carries_forward_but_body_fat_does_not(self):
        self.body(body_fat_percent=20)
        second = create_body_measurement(self.connection, {"date": "2026-07-02", "weight_kg": 60.5})
        row = self.connection.execute("SELECT * FROM body_measurements WHERE id=?", (second,)).fetchone()
        self.assertEqual(row["height_cm"], 170)
        self.assertIsNone(row["body_fat_percent"])

    def test_invalid_weight_and_body_fat_fail(self):
        with self.assertRaises(ValueError):
            self.body(weight=-1)
        with self.assertRaises(ValueError):
            self.body(body_fat_percent=101)

    def test_weight_trends_and_changes(self):
        self.body("2026-07-01", 60)
        self.body("2026-07-07", 61)
        self.assertEqual(len(weight_trend(self.connection, 7, "2026-07-07")), 2)
        self.assertEqual(weight_change(self.connection, 7, "2026-07-07"), 1)

    def test_nutrition_crud_preserves_null_and_zero(self):
        item = create_nutrition_log(self.connection, {
            "date": "2026-07-01", "meal_type": "breakfast", "food_name": "synthetic oats",
            "calories": 0, "protein_g": None,
        })
        row = list_nutrition_logs(self.connection, "2026-07-01")[0]
        self.assertEqual(row["calories"], 0)
        self.assertIsNone(row["protein_g"])
        self.assertTrue(update_nutrition_log(self.connection, item, {"protein_g": 10}))
        self.assertTrue(delete_nutrition_log(self.connection, item))

    def test_nutrition_copy_and_template(self):
        source = {"meal_type": "lunch", "food_name": "synthetic meal", "amount": 1, "unit": "portion"}
        create_nutrition_log(self.connection, {"date": "2026-07-01", **source})
        self.assertEqual(copy_nutrition_date(self.connection, "2026-07-01", "2026-07-02"), 1)
        template_id = save_nutrition_template(self.connection, "synthetic", [source])
        self.assertEqual(add_from_nutrition_template(self.connection, template_id, "2026-07-03"), 1)

    def test_nutrition_summary_completeness(self):
        result = summarize_nutrition_rows([{
            "meal_type": "breakfast", "meal_time": None, "calories": 100,
            "protein_g": None, "carbohydrate_g": 20, "fat_g": 0,
            "fiber_g": None, "water_ml": None, "sodium_mg": None,
        }])
        self.assertEqual(result["calories"], 100)
        self.assertEqual(result["fat_g"], 0)
        self.assertIsNone(result["protein_g"])
        self.assertLess(result["data_completeness"], 100)

    def test_strength_batch_sets_volume_and_rpe_load(self):
        session = create_workout_session(self.connection, {
            "date": "2026-07-01", "session_type": "strength", "duration_minutes": 60, "session_rpe": 8,
        })
        ids = create_batch_sets(self.connection, session, "Synthetic Squat", 5, 5, 100)
        self.assertEqual(len(ids), 5)
        self.assertEqual(set_volume(list_exercise_sets(self.connection, session)[0]), 500)
        self.assertEqual(session_rpe_load(60, 8), 480)

    def test_session_types_metadata_and_crud(self):
        for kind in ("hiphop", "juggling"):
            session = create_workout_session(self.connection, {
                "date": "2026-07-01", "session_type": kind, "duration_minutes": 30,
                "metadata": {"synthetic": True},
            })
            self.assertTrue(update_workout_session(self.connection, session, {"session_rpe": 5}))
        self.assertEqual(len(list_workout_sessions(self.connection, "2026-07-01")), 2)

    def test_session_delete_cascades_sets(self):
        session = create_workout_session(self.connection, {"date": "2026-07-01", "session_type": "strength"})
        create_exercise_set(self.connection, session, {"exercise_name": "Synthetic", "set_number": 1})
        self.assertTrue(delete_workout_session(self.connection, session))
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM exercise_sets").fetchone()[0], 0)

    def test_daily_summary_is_idempotent_and_does_not_add_polar(self):
        self.body()
        session = create_workout_session(self.connection, {"date": "2026-07-01", "session_type": "strength", "duration_minutes": 30})
        create_batch_sets(self.connection, session, "Synthetic", 2, 10, 20)
        first = rebuild_daily_summaries(self.connection, "2026-07-01")
        second = rebuild_daily_summaries(self.connection, "2026-07-01")
        self.assertEqual(first, second)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM daily_training_summary").fetchone()[0], 1)
        self.assertEqual(second["training"]["total_volume_kg"], 400)

    def test_automatic_link_requires_user_confirmation(self):
        session = create_workout_session(self.connection, {"date": "2026-07-01", "session_type": "hiphop"})
        link = create_session_link(self.connection, "synthetic-polar", session, "date_time", .8)
        row = self.connection.execute("SELECT confirmed_by_user FROM polar_manual_session_links WHERE id=?", (link,)).fetchone()
        self.assertEqual(row[0], 0)
        with self.assertRaises(ValueError):
            create_session_link(self.connection, "other", session, "date_time", .9, True)

    def test_migration_is_idempotent_and_checksum_drift_fails(self):
        db.init_db(self.connection)
        count = self.connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version='0.5.0'").fetchone()[0]
        self.assertEqual(count, 1)
        self.connection.execute("UPDATE schema_migrations SET checksum='drift' WHERE version='0.5.0'")
        with self.assertRaises(db.DatabaseMigrationError):
            db.apply_migrations(self.connection)


if __name__ == "__main__":
    unittest.main()
