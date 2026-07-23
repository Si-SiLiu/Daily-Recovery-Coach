import json
import tempfile
import unittest
from pathlib import Path

from src import db, report
from src.ai_context.builder import build_ai_context
from src.domain_dashboard_data import get_latest_training
from src.manual_logging import (
    create_activity_link,
    create_activity_session,
    create_recovery_log,
    create_sleep_log,
)
from src.pipeline.resolution import rebuild_resolved_daily_fields


class ManualResolutionIntegrationTests(unittest.TestCase):
    DATE = "2026-07-15"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.db"
        self.connection = db.connect(self.path)
        activity_raw = json.dumps({
            "sport": {"id": "OTHER"}, "hrAvg": 128, "hrMax": 166,
            "fatPercentage": 31, "distance": 4200,
        })
        self.connection.execute(
            """INSERT INTO polar_training_sessions_raw (
                   source,external_id,date,raw_json,sport,start_time,duration,calories
               ) VALUES ('polar','p1',?,?, 'OTHER','07:00','PT1H',430)""",
            (self.DATE, activity_raw),
        )
        manual_id = create_activity_session(self.connection, {
            "date": self.DATE, "activity_type": "strength",
            "duration_minutes": 90, "average_hr_bpm": 155,
            "max_hr_bpm": 190, "calories_kcal": 700,
            "confirmed_by_user": True, "linked_polar_session_id": "p1",
        })
        create_activity_link(
            self.connection, "p1", manual_id, match_method="manual",
            match_confidence=1.0, confirmed_by_user=True,
        )
        sleep_raw = json.dumps({
            "sleepResult": {"hypnogram": {
                "sleepStart": "2026-07-14T23:00:00+08:00",
                "sleepEnd": "2026-07-15T06:00:00+08:00",
            }},
            "sleepEvaluation": {"asleepDuration": "PT6H30M"},
        })
        self.connection.execute(
            """INSERT INTO polar_sleep_raw (
                   source,external_id,date,raw_json,sleep_duration,sleep_score
               ) VALUES ('polar','s1',?,?, 'PT6H30M',80)""",
            (self.DATE, sleep_raw),
        )
        create_sleep_log(self.connection, {
            "sleep_date": self.DATE, "sleep_duration_minutes": 480,
            "subjective_sleep_quality": 6, "awakenings": 2,
        })
        create_recovery_log(self.connection, {
            "date": self.DATE, "subjective_recovery": 5, "fatigue": 7,
        })
        self.connection.execute(
            """INSERT INTO daily_recovery_metrics (
                   date,training_count,training_duration,training_calories,
                   sleep_duration,sleep_score
               ) VALUES (?,1,'PT1H',430,'PT6H30M',80)""",
            (self.DATE,),
        )
        self.connection.execute(
            """INSERT INTO recovery_scores (
                   date,recovery_score,activity_load_score,training_load_score,
                   score_version,recommendation
               ) VALUES (?,72,50,55,'v1.0','moderate_training')""",
            (self.DATE,),
        )
        self.connection.execute(
            """INSERT INTO recovery_confidence (
                   date,data_completeness_score,baseline_maturity_score,
                   confidence_score,confidence_level,group_scores_json,
                   available_groups_json,missing_groups_json,confidence_version
               ) VALUES (?,80,70,75,'moderate','{}','[]','[]','1.0.0')""",
            (self.DATE,),
        )
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.temp.cleanup()

    def test_resolution_is_field_level_idempotent_and_raw_safe(self):
        before = dict(self.connection.execute(
            "SELECT * FROM polar_training_sessions_raw WHERE external_id='p1'"
        ).fetchone())
        first = rebuild_resolved_daily_fields(self.connection)
        count = self.connection.execute(
            "SELECT COUNT(*) FROM resolved_daily_fields"
        ).fetchone()[0]
        second = rebuild_resolved_daily_fields(self.connection)
        self.assertEqual(first, second)
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM resolved_daily_fields").fetchone()[0],
            count,
        )
        after = dict(self.connection.execute(
            "SELECT * FROM polar_training_sessions_raw WHERE external_id='p1'"
        ).fetchone())
        self.assertEqual(before, after)
        activity_type = self.connection.execute(
            "SELECT * FROM resolved_daily_fields WHERE date=? AND domain='activity' AND field_name='activity_type'",
            (self.DATE,),
        ).fetchone()
        duration = self.connection.execute(
            "SELECT * FROM resolved_daily_fields WHERE date=? AND domain='activity' AND field_name='duration_minutes'",
            (self.DATE,),
        ).fetchone()
        self.assertEqual(json.loads(activity_type["resolved_value_json"]), "strength")
        self.assertEqual(activity_type["value_source"], "manual")
        self.assertEqual(activity_type["is_manual_override"], 1)
        self.assertEqual(json.loads(duration["resolved_value_json"]), 90)
        self.assertEqual(duration["value_source"], "manual")

    def test_dashboard_projection_exposes_sources(self):
        result = get_latest_training(self.path)
        self.assertEqual(result["sports"], ["strength"])
        self.assertEqual(result["duration_minutes"], 90)
        self.assertEqual(
            result["resolved_fields"]["activity_type"]["value_source"], "manual"
        )
        self.assertTrue(
            result["resolved_fields"]["activity_type"]["is_manual_override"]
        )
        self.assertEqual(
            result["resolved_fields"]["duration_minutes"]["value_source"], "manual"
        )

    def test_report_and_ai_context_include_provenance_without_notes(self):
        rebuild_resolved_daily_fields(self.connection)
        data = report.load_report_data(self.connection, self.DATE)
        content = report.render_report(data, "en")
        self.assertIn("Source: User correction", content)
        self.assertIn("Source: Manual entry", content)
        payload = build_ai_context(self.connection, self.DATE)
        activity = payload["training_summary"]["resolved_activity"]
        self.assertEqual(activity["activity_type"]["value_source"], "manual")
        self.assertTrue(activity["activity_type"]["is_manual_override"])
        self.assertEqual(
            payload["sleep_summary"]["subjective_sleep_quality"]["value_source"],
            "manual",
        )
        serialized = json.dumps(payload).lower()
        self.assertNotIn('"notes"', serialized)

    def test_manual_subjective_data_does_not_change_recovery_or_confidence(self):
        before_recovery = dict(self.connection.execute(
            "SELECT * FROM recovery_scores WHERE date=?", (self.DATE,)
        ).fetchone())
        before_confidence = dict(self.connection.execute(
            "SELECT * FROM recovery_confidence WHERE date=?", (self.DATE,)
        ).fetchone())
        rebuild_resolved_daily_fields(self.connection)
        self.assertEqual(before_recovery, dict(self.connection.execute(
            "SELECT * FROM recovery_scores WHERE date=?", (self.DATE,)
        ).fetchone()))
        self.assertEqual(before_confidence, dict(self.connection.execute(
            "SELECT * FROM recovery_confidence WHERE date=?", (self.DATE,)
        ).fetchone()))


if __name__ == "__main__":
    unittest.main()
