import sqlite3
import unittest

from src import db
from src.kubios_morning_input import upsert_manual_morning_measurement


class KubiosMorningInputTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        db.init_db(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_upsert_stores_complete_measurement_and_is_idempotent(self):
        values = {
            "rmssd": 26, "mean_hr": 62, "stress_index": 14.52,
            "respiratory_rate": 21.38, "measurement_quality": "good",
        }
        upsert_manual_morning_measurement(self.connection, "2026-07-17", values)
        values["stress_index"] = 15.0
        row = upsert_manual_morning_measurement(self.connection, "2026-07-17", values)
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM kubios_morning_hrv_raw"
        ).fetchone()[0], 1)
        self.assertEqual(row["stress_index"], 15.0)
        self.assertEqual(row["respiratory_rate"], 21.38)
        self.assertEqual(row["measurement_quality"], "GOOD")

    def test_quality_constraint_and_integrity(self):
        with self.assertRaises(ValueError):
            upsert_manual_morning_measurement(
                self.connection, "2026-07-17", {"measurement_quality": "UNKNOWN"}
            )
        self.assertEqual(self.connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")


if __name__ == "__main__":
    unittest.main()
