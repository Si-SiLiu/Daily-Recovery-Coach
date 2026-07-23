import json
import sqlite3
import unittest

from src import db
from src.data_resolution import resolve_recovery_date, resolve_sleep_date
from src.domain_dashboard_data import get_sleep_history, get_training_history
from src.manual_logging import create_recovery_log, create_sleep_log


class InlineHealthEditingTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        db.init_db(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_sleep_correction_can_override_each_requested_device_field(self):
        self.connection.execute(
            "INSERT INTO polar_sleep_raw(source,external_id,date,raw_json,sleep_duration) VALUES('polar','s','2026-07-16',?,'PT7H')",
            (json.dumps({"deepSleepDuration": "PT1H"}),),
        )
        self.connection.execute(
            "INSERT INTO polar_nightly_recharge_raw(source,external_id,date,raw_json,hrv_rmssd,resting_hr,respiration_rate) VALUES('polar','n','2026-07-16','{}',35,52,15)",
        )
        create_sleep_log(self.connection, {
            "sleep_date": "2026-07-16", "total_sleep_duration_minutes": 450,
            "actual_sleep_duration_minutes": 420, "deep_sleep_duration_minutes": 80,
            "rem_sleep_duration_minutes": 90, "average_sleep_hr_bpm": 54,
            "minimum_sleep_hr_bpm": 45, "nightly_hrv_rmssd": 40,
            "respiration_rate": 14,
        })
        resolved = resolve_sleep_date(self.connection, "2026-07-16")
        self.assertEqual(resolved["deep_sleep_duration_minutes"]["value"], 80)
        self.assertEqual(resolved["nightly_hrv_rmssd"]["value"], 40)
        self.assertEqual(resolved["respiration_rate"]["value_source"], "manual")

    def test_recovery_editor_fields_override_kubios_without_mutating_raw(self):
        self.connection.execute(
            "INSERT INTO kubios_morning_hrv_raw(source,external_id,date,raw_json,rmssd,mean_hr,measurement_time) VALUES('kubios','k','2026-07-16','{}',30,60,'06:10')"
        )
        create_recovery_log(self.connection, {
            "date": "2026-07-16", "measurement_time": "06:20",
            "morning_rmssd_ms": 36, "morning_resting_hr_bpm": 57,
        })
        resolved = resolve_recovery_date(self.connection, "2026-07-16")
        self.assertEqual(resolved["measurement_time"]["value"], "06:20")
        self.assertEqual(resolved["morning_rmssd"]["value"], 36)
        self.assertEqual(resolved["morning_mean_hr"]["value"], 57)
        raw = self.connection.execute("SELECT rmssd,mean_hr FROM kubios_morning_hrv_raw").fetchone()
        self.assertEqual(tuple(raw), (30, 60))


if __name__ == "__main__": unittest.main()
