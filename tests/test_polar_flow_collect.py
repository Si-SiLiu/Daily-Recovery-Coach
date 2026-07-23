import sqlite3
import tempfile
import unittest
from pathlib import Path

from src import db, polar_flow_collect


class PolarFlowCollectTests(unittest.TestCase):
    def make_connection(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        db.init_db(connection)
        return connection

    def test_scan_finds_supported_polar_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            polar_file = source / "polar_flow_training.csv"
            unrelated_file = source / "bank_statement.csv"
            temp_file = source / "polar_flow_training.csv.crdownload"
            polar_file.write_text("date,steps\n", encoding="utf-8")
            unrelated_file.write_text("hello\n", encoding="utf-8")
            temp_file.write_text("partial\n", encoding="utf-8")

            results = polar_flow_collect.scan_for_polar_exports(
                source,
                min_age_seconds=0,
            )

        self.assertEqual(results, [polar_file])

    def test_collect_file_copies_and_records_manifest(self):
        connection = self.make_connection()
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as import_dir:
            source_path = Path(source_dir) / "polar_activity.csv"
            source_path.write_text("date,steps\n2026-07-10,1000\n", encoding="utf-8")

            result = polar_flow_collect.collect_file(
                connection,
                source_path,
                import_dir=Path(import_dir),
            )
            stored_path_exists = result["stored_path"].exists()
            row = connection.execute("SELECT * FROM polar_flow_import_files").fetchone()

        self.assertEqual(result["status"], "collected")
        self.assertTrue(stored_path_exists)
        self.assertEqual(row["status"], "collected")
        self.assertEqual(row["file_type"], "csv")
        self.assertEqual(row["sha256"], result["sha256"])
        connection.close()

    def test_collect_file_skips_duplicates(self):
        connection = self.make_connection()
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as import_dir:
            first = Path(source_dir) / "polar_activity.csv"
            second = Path(source_dir) / "polar_activity_copy.csv"
            content = "date,steps\n2026-07-10,1000\n"
            first.write_text(content, encoding="utf-8")
            second.write_text(content, encoding="utf-8")

            first_result = polar_flow_collect.collect_file(
                connection,
                first,
                import_dir=Path(import_dir),
            )
            second_result = polar_flow_collect.collect_file(
                connection,
                second,
                import_dir=Path(import_dir),
            )
            row_count = connection.execute(
                "SELECT COUNT(*) FROM polar_flow_import_files"
            ).fetchone()[0]

        self.assertEqual(first_result["status"], "collected")
        self.assertEqual(second_result["status"], "skipped_duplicate")
        self.assertEqual(row_count, 1)
        connection.close()

    def test_collect_polar_flow_exports_scans_and_collects(self):
        connection = self.make_connection()
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as import_dir:
            source = Path(source_dir)
            export = source / "polar_flow_activity.gpx"
            export.write_text("<gpx></gpx>\n", encoding="utf-8")
            export.touch()
            # touch resets time to now on some platforms; min_age_seconds=0 keeps test stable.

            results = polar_flow_collect.collect_polar_flow_exports(
                source_dir=source,
                import_dir=Path(import_dir),
                connection=connection,
                min_age_seconds=0,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "collected")
        connection.close()


if __name__ == "__main__":
    unittest.main()
