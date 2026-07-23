import json
import sqlite3
import unittest

from src.data_resolution import (
    ResolutionPolicyError,
    resolve_activity_session,
    resolve_field,
    resolve_recovery_date,
    resolve_sleep_date,
)
from src.manual_logging import (
    ManualLoggingValidationError,
    create_activity_session,
    create_recovery_log,
    create_sleep_log,
    delete_activity_session,
    delete_recovery_log,
    delete_sleep_log,
    get_activity_session,
    list_recovery_logs,
    list_sleep_logs,
    update_activity_session,
    update_recovery_log,
    update_sleep_log,
)


SCHEMA = """
CREATE TABLE manual_activity_sessions (
 id INTEGER PRIMARY KEY, date TEXT NOT NULL, start_time TEXT, end_time TEXT,
 duration_minutes REAL, activity_type TEXT, activity_name TEXT,
 average_hr_bpm REAL, max_hr_bpm REAL, calories_kcal REAL,
 fat_burn_percentage REAL, distance_m REAL, session_rpe REAL, notes TEXT,
 linked_polar_session_id TEXT, confirmed_by_user INTEGER DEFAULT 0,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE manual_sleep_logs (
 id INTEGER PRIMARY KEY, sleep_date TEXT NOT NULL, bed_time TEXT,
 sleep_start_time TEXT, wake_time TEXT, get_up_time TEXT,
 sleep_duration_minutes REAL, nap_duration_minutes REAL,
 subjective_sleep_quality INTEGER, awakenings INTEGER, notes TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE manual_recovery_logs (
 id INTEGER PRIMARY KEY, date TEXT NOT NULL, measurement_time TEXT,
 subjective_recovery INTEGER, fatigue INTEGER, muscle_soreness INTEGER,
 mental_energy INTEGER, training_motivation INTEGER, stress_level INTEGER,
 pain_present INTEGER DEFAULT 0, pain_location TEXT, notes TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE polar_training_sessions_raw (
 id INTEGER PRIMARY KEY, external_id TEXT, date TEXT, raw_json TEXT,
 sport TEXT, start_time TEXT, duration TEXT, calories INTEGER
);
CREATE TABLE polar_sleep_raw (
 id INTEGER PRIMARY KEY, external_id TEXT, date TEXT, raw_json TEXT,
 sleep_duration TEXT, sleep_score INTEGER
);
CREATE TABLE polar_nightly_recharge_raw (
 id INTEGER PRIMARY KEY, external_id TEXT, date TEXT, raw_json TEXT,
 hrv_rmssd REAL, resting_hr REAL, respiration_rate REAL
);
CREATE TABLE kubios_morning_hrv_raw (
 id INTEGER PRIMARY KEY, external_id TEXT, date TEXT, raw_json TEXT,
 rmssd REAL, mean_hr REAL, readiness TEXT
);
CREATE TABLE polar_manual_session_links (
 id INTEGER PRIMARY KEY, polar_session_external_id TEXT,
 workout_session_id INTEGER, manual_activity_session_id INTEGER,
 match_method TEXT, confidence REAL, match_confidence REAL,
 confirmed_by_user INTEGER DEFAULT 0,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class ManualHealthLoggingTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def tearDown(self):
        self.connection.close()

    def test_activity_crud_and_zero_values(self):
        record_id = create_activity_session(self.connection, {
            "date": "2026-07-15", "activity_type": "strength",
            "duration_minutes": 0, "calories_kcal": 0, "session_rpe": 6,
        })
        self.assertEqual(get_activity_session(self.connection, record_id)["calories_kcal"], 0)
        self.assertTrue(update_activity_session(self.connection, record_id, {"duration_minutes": 45}))
        self.assertEqual(get_activity_session(self.connection, record_id)["duration_minutes"], 45)
        self.assertTrue(delete_activity_session(self.connection, record_id))
        self.assertIsNone(get_activity_session(self.connection, record_id))

    def test_activity_ranges_and_hr_relationship(self):
        with self.assertRaises(ManualLoggingValidationError):
            create_activity_session(self.connection, {"date": "2026-07-15", "session_rpe": 11})
        with self.assertRaises(ManualLoggingValidationError):
            create_activity_session(self.connection, {
                "date": "2026-07-15", "average_hr_bpm": 180, "max_hr_bpm": 160,
            })

    def test_sleep_crud_and_ranges(self):
        record_id = create_sleep_log(self.connection, {
            "sleep_date": "2026-07-15", "sleep_duration_minutes": 430,
            "subjective_sleep_quality": 7, "awakenings": 2,
        })
        self.assertEqual(list_sleep_logs(self.connection, "2026-07-15")[0]["awakenings"], 2)
        self.assertTrue(update_sleep_log(self.connection, record_id, {"subjective_sleep_quality": 8}))
        self.assertTrue(delete_sleep_log(self.connection, record_id))
        with self.assertRaises(ManualLoggingValidationError):
            create_sleep_log(self.connection, {
                "sleep_date": "2026-07-15", "subjective_sleep_quality": 0,
            })

    def test_recovery_crud_scale_and_notes_are_stored_verbatim(self):
        record_id = create_recovery_log(self.connection, {
            "date": "2026-07-15", "fatigue": 7, "pain_present": True,
            "pain_location": "synthetic left knee", "notes": "synthetic note",
        })
        row = list_recovery_logs(self.connection, "2026-07-15")[0]
        self.assertEqual(row["pain_location"], "synthetic left knee")
        self.assertNotIn("diagnosis", row)
        self.assertTrue(update_recovery_log(self.connection, record_id, {"fatigue": 6}))
        self.assertTrue(delete_recovery_log(self.connection, record_id))
        with self.assertRaises(ManualLoggingValidationError):
            create_recovery_log(self.connection, {"date": "2026-07-15", "stress_level": 12})


class FieldResolutionTests(unittest.TestCase):
    NOW = "2026-07-15T06:00:00Z"

    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def tearDown(self):
        self.connection.close()

    def test_polar_measured_activity_fields_win(self):
        result = resolve_field(
            "activity", "duration_minutes", polar=(50, 1), manual=(60, 2),
            resolved_at=self.NOW,
        )
        self.assertEqual(result, {
            "field_name": "duration_minutes", "value": 50,
            "value_source": "polar", "source_record_id": 1,
            "is_fallback": False, "is_manual_override": False,
            "resolution_reason": "polar_value_available", "resolved_at": self.NOW,
        })

    def test_manual_is_fallback_only_when_polar_missing(self):
        result = resolve_field(
            "activity", "calories_kcal", polar=(None, 1), manual=(300, 2),
            resolved_at=self.NOW,
        )
        self.assertEqual(result["value"], 300)
        self.assertEqual(result["value_source"], "manual")
        self.assertTrue(result["is_fallback"])
        self.assertEqual(result["resolution_reason"], "polar_unavailable_manual_fallback")

    def test_confirmed_activity_type_is_the_only_manual_override(self):
        result = resolve_field(
            "activity", "activity_type", polar=("OTHER", 10),
            manual={"value": "strength", "record_id": 20, "confirmed": True},
            resolved_at=self.NOW,
        )
        self.assertEqual(result["value"], "strength")
        self.assertEqual(result["source_record_id"], 20)
        self.assertTrue(result["is_manual_override"])
        self.assertFalse(result["is_fallback"])

    def test_unconfirmed_activity_type_does_not_override_polar(self):
        result = resolve_field(
            "activity", "activity_type", polar=("RUNNING", 10),
            manual={"value": "strength", "record_id": 20, "confirmed": False},
            resolved_at=self.NOW,
        )
        self.assertEqual(result["value"], "RUNNING")
        self.assertEqual(result["value_source"], "polar")

    def test_unknown_recovery_field_fails_closed(self):
        with self.assertRaises(ResolutionPolicyError):
            resolve_field("recovery", "unapproved_metric", manual=9)

    def _activity_pair(self, confirmed=True):
        manual_id = create_activity_session(self.connection, {
            "date": "2026-07-15", "activity_type": "strength",
            "duration_minutes": 70, "average_hr_bpm": 150,
            "calories_kcal": 500, "linked_polar_session_id": "polar-1",
            "confirmed_by_user": confirmed,
        })
        raw = json.dumps({"sport": {"id": "OTHER"}, "hrAvg": 130, "hrMax": 165})
        self.connection.execute(
            """INSERT INTO polar_training_sessions_raw
               (external_id,date,raw_json,sport,start_time,duration,calories)
               VALUES ('polar-1','2026-07-15',?,'OTHER','06:30','PT1H',420)""",
            (raw,),
        )
        self.connection.execute(
            """INSERT INTO polar_manual_session_links (
                   polar_session_external_id,manual_activity_session_id,
                   match_method,confidence,match_confidence,confirmed_by_user
               ) VALUES ('polar-1',?,'manual',1.0,1.0,?)""",
            (manual_id, int(confirmed)),
        )
        self.connection.commit()
        return manual_id

    def test_confirmed_link_resolves_field_by_field_without_raw_mutation(self):
        manual_id = self._activity_pair(True)
        before = dict(self.connection.execute(
            "SELECT * FROM polar_training_sessions_raw WHERE external_id='polar-1'"
        ).fetchone())
        result = resolve_activity_session(self.connection, manual_id, resolved_at=self.NOW)
        after = dict(self.connection.execute(
            "SELECT * FROM polar_training_sessions_raw WHERE external_id='polar-1'"
        ).fetchone())
        self.assertEqual(result["duration_minutes"]["value"], 70)
        self.assertEqual(result["average_hr_bpm"]["value"], 150)
        self.assertEqual(result["calories_kcal"]["value"], 500)
        self.assertEqual(result["activity_type"]["value"], "strength")
        self.assertTrue(result["activity_type"]["is_manual_override"])
        self.assertEqual(before, after)

    def test_unconfirmed_activity_is_not_merged_with_polar(self):
        manual_id = self._activity_pair(False)
        result = resolve_activity_session(self.connection, manual_id, resolved_at=self.NOW)
        self.assertEqual(result["duration_minutes"]["value"], 70)
        self.assertEqual(result["duration_minutes"]["value_source"], "manual")
        self.assertFalse(result["activity_type"]["is_manual_override"])

    def test_sleep_polar_priority_manual_subjective_and_no_fake_stages(self):
        create_sleep_log(self.connection, {
            "sleep_date": "2026-07-15", "sleep_duration_minutes": 480,
            "subjective_sleep_quality": 6,
        })
        raw = json.dumps({
            "sleepResult": {"hypnogram": {
                "sleepStart": "2026-07-14T23:00:00+08:00",
                "sleepEnd": "2026-07-15T06:00:00+08:00",
            }},
            "sleepEvaluation": {"asleepDuration": "25200s"},
        })
        self.connection.execute(
            "INSERT INTO polar_sleep_raw(external_id,date,raw_json,sleep_duration,sleep_score) VALUES('s','2026-07-15',?,'PT7H',82)",
            (raw,),
        )
        self.connection.commit()
        result = resolve_sleep_date(self.connection, "2026-07-15", resolved_at=self.NOW)
        self.assertEqual(result["actual_sleep_duration_minutes"]["value"], 480)
        self.assertEqual(result["actual_sleep_duration_minutes"]["value_source"], "manual")
        self.assertEqual(result["subjective_sleep_quality"]["value_source"], "manual")
        self.assertIsNone(result["deep_sleep_duration_minutes"]["value"])
        self.assertEqual(result["deep_sleep_duration_minutes"]["value_source"], "missing")

    def test_sleep_duration_uses_manual_fallback_when_polar_null(self):
        create_sleep_log(self.connection, {
            "sleep_date": "2026-07-15", "sleep_duration_minutes": 390,
        })
        self.connection.execute(
            "INSERT INTO polar_sleep_raw(external_id,date,raw_json) VALUES('s','2026-07-15','{}')"
        )
        self.connection.commit()
        result = resolve_sleep_date(self.connection, "2026-07-15", resolved_at=self.NOW)
        field = result["actual_sleep_duration_minutes"]
        self.assertEqual(field["value"], 390)
        self.assertFalse(field["is_fallback"])

    def test_kubios_morning_and_polar_nightly_remain_distinct(self):
        self.connection.execute(
            "INSERT INTO kubios_morning_hrv_raw(external_id,date,raw_json,rmssd,mean_hr) VALUES('k','2026-07-15','{}',26,62)"
        )
        self.connection.execute(
            "INSERT INTO polar_nightly_recharge_raw(external_id,date,raw_json,hrv_rmssd,resting_hr) VALUES('p','2026-07-15','{}',41,54)"
        )
        create_recovery_log(self.connection, {"date": "2026-07-15", "fatigue": 7})
        result = resolve_recovery_date(self.connection, "2026-07-15", resolved_at=self.NOW)
        self.assertEqual(result["morning_rmssd"]["value"], 26)
        self.assertEqual(result["morning_rmssd"]["value_source"], "kubios")
        self.assertEqual(result["nightly_hrv_rmssd"]["value"], 41)
        self.assertEqual(result["nightly_hrv_rmssd"]["value_source"], "polar")
        self.assertEqual(result["fatigue"]["value_source"], "manual")


if __name__ == "__main__":
    unittest.main()
