import sqlite3
import tempfile
import unittest
from pathlib import Path

from src import db, kubios_import


class KubiosImportTests(unittest.TestCase):
    def make_connection(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        db.init_db(connection)
        return connection

    def write_csv(self, directory, content):
        path = Path(directory) / "kubios_morning_hrv.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_build_column_map_accepts_common_headers(self):
        column_map = kubios_import.build_column_map(
            ["Date", "Time", "RMSSD (ms)", "Mean HR", "Readiness"]
        )

        self.assertEqual(column_map["date"], "Date")
        self.assertEqual(column_map["measurement_time"], "Time")
        self.assertEqual(column_map["rmssd"], "RMSSD (ms)")
        self.assertEqual(column_map["mean_hr"], "Mean HR")
        self.assertEqual(column_map["readiness"], "Readiness")

    def test_read_kubios_csv_parses_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = self.write_csv(
                directory,
                "Date,Time,RMSSD (ms),Mean HR,Readiness,Stress Index,Respiratory Rate,Measurement Quality\n"
                "2026-07-10,07:15:00,48.5,58,Good,14.52,21.38,GOOD\n",
            )

            rows = kubios_import.read_kubios_csv(csv_path)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["date"], "2026-07-10")
        self.assertEqual(row["measurement_time"], "2026-07-10T07:15:00")
        self.assertEqual(row["rmssd"], 48.5)
        self.assertEqual(row["mean_hr"], 58.0)
        self.assertEqual(row["readiness"], "Good")
        self.assertEqual(row["stress_index"], 14.52)
        self.assertEqual(row["respiratory_rate_bpm"], 21.38)
        self.assertEqual(row["measurement_quality"], "GOOD")

    def test_import_kubios_csv_upserts_raw_and_daily_metrics(self):
        connection = self.make_connection()
        with tempfile.TemporaryDirectory() as directory:
            csv_path = self.write_csv(
                directory,
                "Date,Time,RMSSD (ms),Mean HR,Readiness\n"
                "2026-07-10,07:15:00,48.5,58,Good\n",
            )

            first = kubios_import.import_kubios_csv(csv_path, connection)
            csv_path.write_text(
                "Date,Time,RMSSD (ms),Mean HR,Readiness\n"
                "2026-07-10,07:15:00,52.0,56,Excellent\n",
                encoding="utf-8",
            )
            second = kubios_import.import_kubios_csv(csv_path, connection)

        raw_count = connection.execute(
            "SELECT COUNT(*) FROM kubios_morning_hrv_raw"
        ).fetchone()[0]
        raw_row = connection.execute(
            "SELECT * FROM kubios_morning_hrv_raw"
        ).fetchone()
        metric_row = connection.execute(
            "SELECT morning_rmssd, morning_mean_hr, kubios_readiness FROM daily_recovery_metrics WHERE date = '2026-07-10'"
        ).fetchone()

        self.assertEqual(first["raw_rows"], 1)
        self.assertEqual(first["daily_metrics"], 1)
        self.assertEqual(second["raw_rows"], 1)
        self.assertEqual(second["daily_metrics"], 1)
        self.assertEqual(raw_count, 1)
        self.assertEqual(raw_row["rmssd"], 52.0)
        self.assertEqual(raw_row["mean_hr"], 56.0)
        self.assertEqual(raw_row["readiness"], "Excellent")
        self.assertEqual(metric_row["morning_rmssd"], 52.0)
        self.assertEqual(metric_row["morning_mean_hr"], 56.0)
        self.assertEqual(metric_row["kubios_readiness"], "Excellent")
        connection.close()

    def test_missing_csv_raises_error(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.csv"

            with self.assertRaises(kubios_import.KubiosImportError):
                kubios_import.read_kubios_csv(missing)


if __name__ == "__main__":
    unittest.main()
