import unittest

import pandas as pd

from src.ui_tables import centered_columns, centered_number, centered_table_html, centered_text


class CenteredTableTests(unittest.TestCase):
    def test_text_and_number_columns_are_centered(self):
        self.assertEqual(centered_text("Text")["alignment"], "center")
        self.assertEqual(centered_number("Number")["alignment"], "center")

    def test_read_only_config_centers_every_column(self):
        config = centered_columns(pd.DataFrame({"name": ["a"], "value": [1]}))
        self.assertEqual(set(config), {"name", "value"})
        self.assertTrue(all(value["alignment"] == "center" for value in config.values()))

    def test_read_only_html_centers_headers_and_escapes_values(self):
        markup = centered_table_html([{"日期": "2026-07-16", "名称": "<script>", "数值": 118.0}])
        self.assertIn("text-align: center !important", markup)
        self.assertIn("border-collapse: collapse", markup)
        self.assertIn("border: 1px solid", markup)
        self.assertIn("<th>日期</th>", markup)
        self.assertIn("&lt;script&gt;", markup)
        self.assertIn("<td>118</td>", markup)
        self.assertNotIn("<td><script></td>", markup)


if __name__ == "__main__":
    unittest.main()
