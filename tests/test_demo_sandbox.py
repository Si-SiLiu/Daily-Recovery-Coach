import os
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import demo_sandbox
from src.db import DB_PATH, connect, get_current_db_path, set_current_db_path


class DemoSandboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.sessions_root = Path(self.temp.name) / "sessions"
        self.patch_root = patch.object(demo_sandbox, "SESSIONS_ROOT", self.sessions_root)
        self.patch_root.start()
        self.demo_mode = patch.dict(os.environ, {"DRC_DEMO_MODE": "1"}, clear=False)
        self.demo_mode.start()

    def tearDown(self):
        set_current_db_path(None)
        self.demo_mode.stop()
        self.patch_root.stop()
        self.temp.cleanup()

    def test_sessions_have_stable_private_paths(self):
        first, second = {}, {}
        first_path = demo_sandbox.ensure_demo_sandbox(first)
        second_path = demo_sandbox.ensure_demo_sandbox(second)
        self.assertNotEqual(first[demo_sandbox.SANDBOX_ID_KEY], second[demo_sandbox.SANDBOX_ID_KEY])
        self.assertNotEqual(first_path, second_path)
        root = self.sessions_root.resolve()
        self.assertTrue(first_path.is_relative_to(root))
        self.assertTrue(second_path.is_relative_to(root))

    def test_rerun_is_idempotent_and_does_not_reseed(self):
        state = {}
        first_path = demo_sandbox.ensure_demo_sandbox(state)
        first_id = state[demo_sandbox.SANDBOX_ID_KEY]
        with connect(first_path) as connection:
            first_count = connection.execute("SELECT COUNT(*) FROM daily_recovery_metrics").fetchone()[0]
        second_path = demo_sandbox.ensure_demo_sandbox(state)
        with connect(second_path) as connection:
            second_count = connection.execute("SELECT COUNT(*) FROM daily_recovery_metrics").fetchone()[0]
        self.assertEqual(first_id, state[demo_sandbox.SANDBOX_ID_KEY])
        self.assertEqual(first_path, second_path)
        self.assertEqual(first_count, second_count)

    def test_data_written_by_one_session_is_invisible_to_another(self):
        state_a, state_b = {}, {}
        path_a = demo_sandbox.ensure_demo_sandbox(state_a)
        path_b = demo_sandbox.ensure_demo_sandbox(state_b)
        set_current_db_path(path_a)
        with connect() as connection:
            connection.execute(
                "INSERT INTO workout_sessions (date, session_type, notes) VALUES (?, ?, ?)",
                ("2099-01-01", "other", "SESSION_A_ONLY"),
            )
            connection.commit()
        set_current_db_path(path_b)
        with connect() as connection:
            found = connection.execute(
                "SELECT 1 FROM workout_sessions WHERE notes = ?", ("SESSION_A_ONLY",)
            ).fetchone()
        self.assertIsNone(found)

    def test_domain_updates_stay_in_the_originating_session(self):
        state_a, state_b = {}, {}
        path_a = demo_sandbox.ensure_demo_sandbox(state_a)
        path_b = demo_sandbox.ensure_demo_sandbox(state_b)

        with connect(path_a) as connection:
            seed_date = connection.execute(
                "SELECT MAX(date) FROM daily_recovery_metrics"
            ).fetchone()[0]
            connection.execute(
                "UPDATE daily_recovery_metrics SET sleep_score = ? WHERE date = ?",
                (99, seed_date),
            )
            connection.execute(
                """INSERT INTO nutrition_logs
                (date, meal_type, food_name, calories, data_source)
                VALUES (?, ?, ?, ?, ?)""",
                (date.today().isoformat(), "other", "SESSION_A_ONLY", 123, "manual"),
            )
            connection.execute(
                """INSERT INTO body_measurements
                (date, height_cm, weight_kg, is_primary)
                VALUES (?, ?, ?, ?)""",
                (date.today().isoformat(), 180, 80, 1),
            )
            connection.commit()

        with connect(path_b) as connection:
            recovery = connection.execute(
                "SELECT sleep_score FROM daily_recovery_metrics WHERE date = ?",
                (seed_date,),
            ).fetchone()
            nutrition = connection.execute(
                "SELECT 1 FROM nutrition_logs WHERE food_name = ?",
                ("SESSION_A_ONLY",),
            ).fetchone()
            measurement = connection.execute(
                "SELECT 1 FROM body_measurements WHERE date = ?",
                (date.today().isoformat(),),
            ).fetchone()

        self.assertNotEqual(recovery[0], 99)
        self.assertIsNone(nutrition)
        self.assertIsNone(measurement)

    def test_reset_replaces_only_current_session(self):
        state_a, state_b = {}, {}
        path_a = demo_sandbox.ensure_demo_sandbox(state_a)
        path_b = demo_sandbox.ensure_demo_sandbox(state_b)
        set_current_db_path(path_b)
        with connect() as connection:
            connection.execute(
                "INSERT INTO workout_sessions (date, session_type, notes) VALUES (?, ?, ?)",
                ("2099-01-02", "other", "SESSION_B_ONLY"),
            )
            connection.commit()
        old_id = state_a[demo_sandbox.SANDBOX_ID_KEY]
        new_path = demo_sandbox.reset_demo_sandbox(state_a)
        self.assertNotEqual(old_id, state_a[demo_sandbox.SANDBOX_ID_KEY])
        self.assertNotEqual(path_a, new_path)
        with connect(path_b) as connection:
            found = connection.execute(
                "SELECT 1 FROM workout_sessions WHERE notes = ?", ("SESSION_B_ONLY",)
            ).fetchone()
        self.assertIsNotNone(found)
        with connect(new_path) as connection:
            found = connection.execute(
                "SELECT 1 FROM workout_sessions WHERE notes = ?", ("SESSION_B_ONLY",)
            ).fetchone()
        self.assertIsNone(found)

    def test_local_mode_keeps_formal_database(self):
        state = {}
        with patch.dict(os.environ, {}, clear=True):
            resolved = demo_sandbox.configure_demo_runtime(state)
        self.assertEqual(resolved, DB_PATH)
        self.assertEqual(get_current_db_path(), DB_PATH)
        self.assertFalse(state)
        self.assertFalse(self.sessions_root.exists())

    def test_invalid_sandbox_id_cannot_escape_sessions_root(self):
        with self.assertRaises(ValueError):
            demo_sandbox._sandbox_path("../outside")
        with self.assertRaises(ValueError):
            demo_sandbox._sandbox_path("a" * 31 + "!")

    def test_cleanup_does_not_remove_current_sandbox(self):
        state = {}
        current_path = demo_sandbox.ensure_demo_sandbox(state)
        current_id = state[demo_sandbox.SANDBOX_ID_KEY]
        stale_marker = current_path.parent / demo_sandbox.LAST_ACCESS_FILENAME
        stale_marker.touch()
        old_time = 1
        os.utime(stale_marker, (old_time, old_time))

        demo_sandbox.cleanup_expired_sandboxes(
            current_sandbox_id=current_id,
            now=old_time + demo_sandbox.SANDBOX_TTL_SECONDS + 1,
        )

        self.assertTrue(current_path.exists())


if __name__ == "__main__":
    unittest.main()
