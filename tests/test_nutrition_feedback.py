import sqlite3
import unittest

from src import db
from src.nutrition_logging import (
    create_meal_record, food_catalog_by_name, get_meal_record, list_meal_records,
)
from src.nutrition_logging.feedback import (
    NutritionFeedbackService, is_day_nutrition_confirmed,
    set_day_nutrition_confirmed, summarize_draft_food_items, summarize_food_items,
)


class NutritionFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        db.init_db(self.connection)
        self.catalog = food_catalog_by_name(self.connection)
        self.day = "2026-07-22"

    def tearDown(self):
        self.connection.close()

    def _meal(self, meal_type="breakfast", eaten_at="08:00"):
        return {
            "date": self.day, "meal_type": meal_type, "eaten_at": eaten_at,
            "status": "completed", "source": "manual",
        }

    def _create_food_meal(self, meal_type="breakfast", eaten_at="08:00", items=None, supplements=None):
        return create_meal_record(
            self.connection, self._meal(meal_type, eaten_at), items or [], supplements or [],
        )

    def test_current_meal_summary_uses_catalog_nutrients(self):
        summary = summarize_draft_food_items(self.connection, [
            {"food_catalog_id": self.catalog["oats"]["id"], "quantity": 50, "unit": "g"},
            {"food_catalog_id": self.catalog["water"]["id"], "quantity": 350, "unit": "ml"},
        ])
        self.assertEqual(summary["calories_kcal"], 189.5)
        self.assertEqual(summary["protein_g"], 6.58)
        self.assertEqual(summary["water_ml"], 355.42)

    def test_day_summary_accumulates_multiple_meals(self):
        self._create_food_meal(items=[
            {"food_catalog_id": self.catalog["oats"]["id"], "quantity": 50, "unit": "g"},
        ])
        self._create_food_meal("lunch", "12:30", [{
            "food_catalog_id": self.catalog["egg"]["id"], "quantity": 2, "unit": "piece",
        }])
        service = NutritionFeedbackService(list_meal_records(self.connection), self.day)
        summary = service.today_summary()
        self.assertEqual(summary["recorded_meals"], 2)
        self.assertEqual(summary["calories_kcal"], 332.5)
        self.assertEqual(summary["protein_g"], 19.14)

    def test_unrecognised_food_is_not_treated_as_zero(self):
        unknown_only = summarize_food_items([{"custom_food_name": "home dish"}])
        self.assertIsNone(unknown_only["calories_kcal"])
        mixed = summarize_food_items([
            {"food_catalog_id": 1, "calories_kcal": 100, "protein_g": 5},
            {"custom_food_name": "home dish"},
        ])
        self.assertEqual(mixed["calories_kcal"], 100)
        self.assertEqual(mixed["unidentified_food_count"], 1)

    def test_live_feedback_ignores_new_row_without_quantity(self):
        summary = summarize_draft_food_items(self.connection, [
            {"food_catalog_id": self.catalog["tea"]["id"], "quantity": None, "unit": "cup"},
        ])
        self.assertEqual(summary["food_count"], 0)
        self.assertIsNone(summary["calories_kcal"])

    def test_partial_day_does_not_generate_final_evaluation(self):
        self._create_food_meal(items=[
            {"food_catalog_id": self.catalog["egg"]["id"], "quantity": 1, "unit": "piece"},
        ])
        evaluation = NutritionFeedbackService(
            list_meal_records(self.connection), self.day,
        ).daily_evaluation(confirmed=False)
        self.assertEqual(evaluation["completeness"], "partial")
        self.assertIn("当前为已记录摄入", evaluation["summary"])
        self.assertNotIn("今日记录已完成", evaluation["summary"])

    def test_confirmed_day_can_generate_completed_evaluation(self):
        self._create_food_meal(items=[
            {"food_catalog_id": self.catalog["egg"]["id"], "quantity": 1, "unit": "piece"},
        ])
        set_day_nutrition_confirmed(self.connection, self.day, True)
        self.assertTrue(is_day_nutrition_confirmed(self.connection, self.day))
        evaluation = NutritionFeedbackService(
            list_meal_records(self.connection), self.day,
        ).daily_evaluation(confirmed=True)
        self.assertEqual(evaluation["completeness"], "complete")
        self.assertIn("今日记录已完成", evaluation["summary"])
        set_day_nutrition_confirmed(self.connection, self.day, False)
        self.assertFalse(is_day_nutrition_confirmed(self.connection, self.day))

    def test_missing_baseline_and_target_are_explicit(self):
        self._create_food_meal(items=[
            {"food_catalog_id": self.catalog["egg"]["id"], "quantity": 1, "unit": "piece"},
        ])
        protein = NutritionFeedbackService(
            list_meal_records(self.connection), self.day,
        ).daily_metrics()["protein_g"]
        self.assertEqual(protein["baseline_status"], "insufficient_data")
        self.assertIsNone(protein["baseline"])
        self.assertIsNone(protein["target"])

    def test_evaluation_has_at_most_three_suggestions(self):
        for day in ("2026-07-19", "2026-07-20", "2026-07-21"):
            create_meal_record(self.connection, {
                "date": day, "meal_type": "breakfast", "eaten_at": "08:00",
                "status": "completed", "source": "manual",
            }, [
                {"food_catalog_id": self.catalog["oats"]["id"], "quantity": 300, "unit": "g"},
                {"food_catalog_id": self.catalog["water"]["id"], "quantity": 2000, "unit": "ml"},
            ])
        self._create_food_meal(items=[
            {"food_catalog_id": self.catalog["egg"]["id"], "quantity": 1, "unit": "piece"},
        ])
        evaluation = NutritionFeedbackService(
            list_meal_records(self.connection), self.day,
        ).daily_evaluation(confirmed=False)
        self.assertLessEqual(len(evaluation["suggestions"]), 3)

    def test_supplements_and_medications_do_not_add_food_calories(self):
        self._create_food_meal(supplements=[
            {"custom_product_name": "Protein powder", "quantity": 30, "unit": "g"},
            {"custom_product_name": "Finasteride", "quantity": 1, "unit": "tablet"},
        ])
        summary = NutritionFeedbackService(list_meal_records(self.connection), self.day).today_summary()
        self.assertEqual(summary["food_count"], 0)
        self.assertIsNone(summary["calories_kcal"])


if __name__ == "__main__":
    unittest.main()
