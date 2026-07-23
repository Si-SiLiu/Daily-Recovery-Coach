import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src import db, polar_import


class PolarImportTests(unittest.TestCase):
    def make_connection(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        db.init_db(connection)
        return connection

    def test_import_daily_activity_parses_common_fields(self):
        connection = self.make_connection()
        count = polar_import.import_daily_activities(
            connection,
            [
                {
                    "start_time": "2026-07-10T00:00:00",
                    "steps": 1234,
                    "calories": 2100,
                    "active_calories": 600,
                    "active_duration": "PT1H",
                }
            ],
        )

        row = connection.execute("SELECT * FROM polar_daily_activity_raw").fetchone()

        self.assertEqual(count, 1)
        self.assertEqual(row["source"], "polar")
        self.assertEqual(row["external_id"], "2026-07-10T00:00:00")
        self.assertEqual(row["date"], "2026-07-10")
        self.assertEqual(row["steps"], 1234)
        self.assertEqual(row["calories"], 2100)
        self.assertEqual(row["active_calories"], 600)
        self.assertEqual(row["duration"], "PT1H")
        self.assertEqual(json.loads(row["raw_json"])["steps"], 1234)
        connection.close()

    def test_import_daily_activity_updates_duplicates(self):
        connection = self.make_connection()
        first = {
            "start_time": "2026-07-10T00:00:00",
            "steps": 100,
            "calories": 1000,
        }
        second = {
            "start_time": "2026-07-10T00:00:00",
            "steps": 200,
            "calories": 1200,
        }

        polar_import.import_daily_activities(connection, [first])
        polar_import.import_daily_activities(connection, [second])

        row_count = connection.execute(
            "SELECT COUNT(*) FROM polar_daily_activity_raw"
        ).fetchone()[0]
        row = connection.execute("SELECT * FROM polar_daily_activity_raw").fetchone()

        self.assertEqual(row_count, 1)
        self.assertEqual(row["steps"], 200)
        self.assertEqual(row["calories"], 1200)
        connection.close()

    def test_import_training_sessions_parses_common_fields(self):
        connection = self.make_connection()
        count = polar_import.import_training_sessions(
            connection,
            [
                {
                    "id": "session-1",
                    "start_time": "2026-07-09T07:30:00",
                    "sport": "RUNNING",
                    "duration": "PT45M",
                    "calories": 450,
                }
            ],
        )

        row = connection.execute("SELECT * FROM polar_training_sessions_raw").fetchone()

        self.assertEqual(count, 1)
        self.assertEqual(row["external_id"], "session-1")
        self.assertEqual(row["date"], "2026-07-09")
        self.assertEqual(row["sport"], "RUNNING")
        self.assertEqual(row["start_time"], "2026-07-09T07:30:00")
        self.assertEqual(row["duration"], "PT45M")
        self.assertEqual(row["calories"], 450)
        connection.close()

    def test_import_raw_polar_data_reads_raw_files(self):
        connection = self.make_connection()
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            (raw_dir / "polar_daily_activity.json").write_text(
                json.dumps([{"start_time": "2026-07-10T00:00:00", "steps": 1}]),
                encoding="utf-8",
            )
            (raw_dir / "polar_training_sessions.json").write_text(
                json.dumps([{"id": "s1", "start_time": "2026-07-09T07:30:00"}]),
                encoding="utf-8",
            )

            result = polar_import.import_raw_polar_data(connection, raw_dir)

        self.assertEqual(result["daily_activity"], 1)
        self.assertEqual(result["training_sessions"], 1)
        connection.close()

    def test_import_raw_polar_data_reads_v4_containers(self):
        connection = self.make_connection()
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            (raw_dir / "polar_daily_activity.json").write_text(
                json.dumps(
                    {
                        "activities": {
                            "activityDays": [
                                {
                                    "date": "2026-07-10",
                                    "steps": 2000,
                                    "activeCalories": 700,
                                    "activeDuration": "PT2H",
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            (raw_dir / "polar_training_sessions.json").write_text(
                json.dumps(
                    {
                        "trainingSessions": [
                            {
                                "id": "v4-session-1",
                                "startTime": "2026-07-09T07:30:00",
                                "sport": "RUNNING",
                                "duration": "PT45M",
                                "calories": 450,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = polar_import.import_raw_polar_data(connection, raw_dir)

        activity = connection.execute("SELECT * FROM polar_daily_activity_raw").fetchone()
        session = connection.execute("SELECT * FROM polar_training_sessions_raw").fetchone()

        self.assertEqual(result["daily_activity"], 1)
        self.assertEqual(result["training_sessions"], 1)
        self.assertEqual(activity["date"], "2026-07-10")
        self.assertEqual(activity["active_calories"], 700)
        self.assertEqual(activity["duration"], "PT2H")
        self.assertEqual(session["external_id"], "v4-session-1")
        self.assertEqual(session["start_time"], "2026-07-09T07:30:00")
        connection.close()

    def test_import_sleep_and_nightly_recharge_parse_common_fields(self):
        connection = self.make_connection()

        sleep_count = polar_import.import_sleep(
            connection,
            [{"date": "2026-07-10", "sleep_duration": "PT7H30M", "sleep_score": 82}],
        )
        nightly_count = polar_import.import_nightly_recharges(
            connection,
            [
                {
                    "date": "2026-07-10",
                    "ans_charge_status": 3,
                    "heart_rate_variability_avg": 42,
                    "heart_rate_avg": 58,
                    "breathing_rate_avg": 14.2,
                }
            ],
        )

        sleep = connection.execute("SELECT * FROM polar_sleep_raw").fetchone()
        nightly = connection.execute("SELECT * FROM polar_nightly_recharge_raw").fetchone()

        self.assertEqual(sleep_count, 1)
        self.assertEqual(sleep["sleep_duration"], "PT7H30M")
        self.assertEqual(sleep["sleep_score"], 82)
        self.assertEqual(nightly_count, 1)
        self.assertEqual(nightly["ans_status"], "3")
        self.assertEqual(nightly["hrv_rmssd"], 42)
        self.assertEqual(nightly["resting_hr"], 58)
        self.assertEqual(nightly["respiration_rate"], 14.2)
        connection.close()

    def test_import_v4_sleep_and_nightly_recharge_nested_fields(self):
        connection = self.make_connection()

        polar_import.import_sleep(
            connection,
            [
                {
                    "sleepDate": "2026-07-10",
                    "sleepScore": {"sleepScore": 84},
                    "sleepEvaluation": {
                        "sleepSpan": "28800s",
                        "asleepDuration": "27000s",
                    },
                }
            ],
        )
        polar_import.import_nightly_recharges(
            connection,
            [
                {
                    "sleepResultDate": "2026-07-10",
                    "ansStatus": 2,
                    "meanNightlyRecoveryRri": 1000,
                    "meanNightlyRecoveryRmssd": 45,
                    "meanNightlyRecoveryRespirationInterval": 4000,
                }
            ],
        )

        sleep = connection.execute("SELECT * FROM polar_sleep_raw").fetchone()
        nightly = connection.execute("SELECT * FROM polar_nightly_recharge_raw").fetchone()
        self.assertEqual(sleep["sleep_duration"], "PT7H30M")
        self.assertEqual(sleep["sleep_score"], 84)
        self.assertEqual(nightly["hrv_rmssd"], 45)
        self.assertEqual(nightly["resting_hr"], 60)
        self.assertEqual(nightly["respiration_rate"], 15)
        connection.close()

    def test_import_nightly_recharge_averages_breathing_samples_when_summary_is_zero(self):
        connection = self.make_connection()
        polar_import.import_nightly_recharges(connection, [{
            "sleepResultDate": "2026-07-10",
            "meanNightlyRecoveryRespirationInterval": 0,
            "breathingRateSamples": [
                {"breathingRateValues": [14.0, 15.0]},
                {"breathingRateValues": [16.0, None, 0.0]},
            ],
        }])

        value = connection.execute(
            "SELECT respiration_rate FROM polar_nightly_recharge_raw"
        ).fetchone()[0]
        self.assertEqual(value, 15.0)
        connection.close()

    def test_import_cardio_and_continuous_hr_parse_raw(self):
        connection = self.make_connection()

        cardio_count = polar_import.import_cardio_loads(
            connection,
            [{"date": "2026-07-10", "cardio_load": 80, "strain": 50, "tolerance": 60, "status": "productive"}],
        )
        hr_count = polar_import.import_continuous_heart_rates(
            connection,
            [{"date": "2026-07-10", "samples": [{"time": "12:00", "heart_rate": 70}]}],
        )

        cardio = connection.execute("SELECT * FROM polar_cardio_load_raw").fetchone()
        hr = connection.execute("SELECT * FROM polar_continuous_hr_raw").fetchone()

        self.assertEqual(cardio_count, 1)
        self.assertEqual(cardio["cardio_load"], 80)
        self.assertEqual(cardio["status"], "productive")
        self.assertEqual(hr_count, 1)
        self.assertEqual(hr["date"], "2026-07-10")
        connection.close()


if __name__ == "__main__":
    unittest.main()
