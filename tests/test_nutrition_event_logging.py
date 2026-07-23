import sqlite3
import unittest

from src import db
from src.nutrition_logging import (
    NutritionEventValidationError,
    create_meal_event,
    delete_meal_event,
    get_meal_event,
    list_meal_events,
    save_meal_event,
)


class NutritionEventLoggingTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        db.init_db(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_full_meal_event_crud_preserves_items_and_units(self):
        event_id = create_meal_event(self.connection, {
            "date": "2026-07-16", "meal_type": "breakfast",
            "actual_meal_time": "07:30", "notes": "morning",
        }, [
            {"category": "carbohydrate", "position": 1, "item_name": "oats", "quantity": 60, "unit": "g"},
            {"category": "dairy", "position": 1, "item_name": "milk", "quantity": 250, "unit": "g"},
            {"category": "hydration", "position": 1, "item_name": None, "quantity": 300, "unit": "ml"},
        ])
        event = get_meal_event(self.connection, event_id)
        self.assertEqual(event["meal_type"], "breakfast")
        self.assertEqual(len(event["items"]), 3)
        self.assertEqual(list_meal_events(self.connection)[0]["item_count"], 3)
        summary = list_meal_events(self.connection)[0]
        self.assertEqual(summary["estimated_calories_kcal"], 252.5)
        self.assertEqual(summary["balance_score"], 30)
        self.assertEqual(summary["balance_level"], "needs_improvement")

        save_meal_event(self.connection, {
            "date": "2026-07-16", "meal_type": "lunch",
            "actual_meal_time": "12:15", "notes": "updated",
        }, [{"category": "protein", "position": 1, "item_name": "fish", "quantity": 150, "unit": "g"}], event_id)
        updated = get_meal_event(self.connection, event_id)
        self.assertEqual(updated["meal_type"], "lunch")
        self.assertEqual([item["item_name"] for item in updated["items"]], ["fish"])
        self.assertTrue(delete_meal_event(self.connection, event_id))
        self.assertIsNone(get_meal_event(self.connection, event_id))

    def test_snack_rejects_extended_categories(self):
        with self.assertRaises(NutritionEventValidationError):
            create_meal_event(self.connection, {
                "date": "2026-07-16", "meal_type": "training_fuel",
                "actual_meal_time": "18:00",
            }, [{"category": "caffeine", "position": 1, "quantity": 1, "unit": "g"}])

    def test_maximum_five_items_per_category_is_enforced(self):
        items = [
            {"category": "protein", "position": index, "item_name": f"p{index}", "quantity": 10, "unit": "g"}
            for index in range(1, 7)
        ]
        with self.assertRaises(NutritionEventValidationError):
            create_meal_event(self.connection, {
                "date": "2026-07-16", "meal_type": "dinner",
                "actual_meal_time": "19:00",
            }, items)

    def test_item_name_and_category_units_are_validated(self):
        event = {"date": "2026-07-16", "meal_type": "breakfast", "actual_meal_time": "08:00"}
        with self.assertRaises(NutritionEventValidationError):
            create_meal_event(self.connection, event, [
                {"category": "protein", "position": 1, "item_name": "", "quantity": 20, "unit": "g"},
            ])
        hydration_id = create_meal_event(self.connection, event, [
            {"category": "hydration", "position": 1, "quantity": 300, "unit": "ml"},
        ])
        self.assertEqual(get_meal_event(self.connection, hydration_id)["items"][0]["unit"], "ml")
        with self.assertRaises(NutritionEventValidationError):
            create_meal_event(self.connection, event, [
                {"category": "hydration", "position": 1, "quantity": 300, "unit": "g"},
            ])


if __name__ == "__main__":
    unittest.main()
