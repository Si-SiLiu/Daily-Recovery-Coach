import unittest
import json
from pathlib import Path

from src.exercise_format import hms_to_minutes, hours_to_hms, minutes_to_hms, time_to_hms


class ExerciseFormatTests(unittest.TestCase):
    def test_minutes_render_as_hh_mm_ss(self):
        self.assertEqual(minutes_to_hms(85 + 23 / 60), "01:25:23")

    def test_hh_mm_ss_round_trips_to_minutes(self):
        self.assertAlmostEqual(hms_to_minutes("01:25:23"), 85 + 23 / 60)

    def test_invalid_duration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "HH:MM:SS"):
            hms_to_minutes("1:85")

    def test_numeric_hours_render_with_seconds(self):
        self.assertEqual(hours_to_hms(7.5), "07:30:00")

    def test_clock_and_iso_times_render_with_seconds(self):
        self.assertEqual(time_to_hms("23:15"), "23:15:00")
        self.assertEqual(time_to_hms("2026-07-16T06:05:09+08:00"), "06:05:09")

    def test_domain_pages_do_not_use_canvas_data_editors(self):
        root = Path(__file__).resolve().parents[1]
        exercise = (root / "src" / "dashboard.py").read_text(encoding="utf-8")
        sleep = (root / "src" / "pages" / "1_Sleep.py").read_text(encoding="utf-8")
        recovery = (root / "src" / "pages" / "2_Recovery.py").read_text(encoding="utf-8")
        for source in (exercise, sleep, recovery):
            self.assertNotIn("st.data_editor", source)
            self.assertNotIn("_inline_editor", source)
        self.assertIn("st.form", recovery)

    def test_nutrition_editor_has_dynamic_supplement_units(self):
        root = Path(__file__).resolve().parents[1]
        nutrition = (root / "src" / "pages" / "3_Nutrition.py").read_text(encoding="utf-8")
        zh = json.loads((root / "locales" / "zh-CN.json").read_text(encoding="utf-8"))
        self.assertNotIn("st.data_editor", nutrition)
        self.assertIn("_supplement_editor", nutrition)
        self.assertIn("selectbox", nutrition)
        self.assertIn("supplement_unit_", nutrition)
        self.assertIn('drc-nutrition-column-title', nutrition)
        self.assertIn('text-align: center !important', nutrition)
        self.assertIn('div[data-testid="stSelectbox"]', nutrition)
        self.assertIn('div[value]', nutrition)
        self.assertEqual(zh["nutrition_entry"]["quantity"], "剂量（克）")
        self.assertEqual(zh["nutrition_entry"]["intake_quantity"], "摄入量")

    def test_today_nutrition_includes_polar_resting_calories_before_activity(self):
        root = Path(__file__).resolve().parents[1]
        nutrition = (root / "src" / "pages" / "3_Nutrition.py").read_text(encoding="utf-8")
        resting = nutrition.index('"静息消耗估计（kcal）"')
        activity = nutrition.index('"活动消耗（kcal）"')
        self.assertLess(resting, activity)
        self.assertIn('float(total) - float(active)', nutrition)
        self.assertIn('metrics.get("calories")', nutrition)
        self.assertIn('metrics.get("active_calories")', nutrition)


if __name__ == "__main__":
    unittest.main()
