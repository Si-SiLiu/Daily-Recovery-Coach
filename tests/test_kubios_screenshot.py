import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from src import db, kubios_import
from src.kubios_screenshot import audit, confidence, importer, parser, service, storage, validation
from src.kubios_screenshot.image_preprocess import UnsupportedImageError, preprocess_image, validate_image_bytes
from src.kubios_screenshot.models import OCRResult, TextBlock
from src.kubios_screenshot.ocr_adapter import LocalOCRError, VisionOCRAdapter


def image_bytes(fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", (800, 1600), "white").save(buffer, format=fmt)
    return buffer.getvalue()


def ocr_result(lines=None, score=0.98):
    lines = lines or ["Date 2026-07-08", "Time 06:30", "RMSSD 54 ms", "Mean HR 58 bpm", "Readiness 82"]
    blocks = [TextBlock(line, score, {"x": 0.1, "y": 0.8 - index * 0.1, "width": 0.7, "height": 0.08}) for index, line in enumerate(lines)]
    return OCRResult("synthetic_test_adapter", "1.0", {"width": 800, "height": 1600}, blocks, "\n".join(lines), [])


class FakeAdapter:
    engine = "synthetic_test_adapter"

    def __init__(self, result=None, error=None):
        self.result = result or ocr_result()
        self.error = error

    def readiness(self):
        return {"ready": True, "network_required": False}

    def recognize(self, path):
        if self.error:
            raise LocalOCRError(self.error)
        return self.result


class KubiosScreenshotTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        db.init_db(self.connection)

    def tearDown(self):
        self.connection.close()

    def storage_context(self, directory):
        root = Path(directory)
        return patch.multiple(
            storage,
            BASE_DIR=root,
            IMPORT_ROOT=root / "data/imports/kubios_screenshots",
            ORIGINAL_DIR=root / "data/imports/kubios_screenshots/original",
            PROCESSED_DIR=root / "data/imports/kubios_screenshots/processed",
        )

    def insert_audit(self, digest="a" * 64, confidence_value=0.91):
        cursor = self.connection.execute(
            """
            INSERT INTO kubios_screenshot_imports (
                file_sha256,original_relative_path,processed_relative_path,
                import_status,ocr_engine,ocr_engine_version,parser_version,
                ocr_text_summary,overall_ocr_confidence,required_fields_found
            ) VALUES (?, 'data/imports/kubios_screenshots/original/a.png',
                      'data/imports/kubios_screenshots/processed/a.png',
                      'review_required','test','1','1.0.0','fields=date,mean_hr,rmssd',?,1)
            """,
            (digest, confidence_value),
        )
        self.connection.commit()
        return cursor.lastrowid

    def test_png_is_accepted(self):
        self.assertEqual(validate_image_bytes(image_bytes(), "sample.png"), ".png")

    def test_jpg_is_accepted(self):
        self.assertEqual(validate_image_bytes(image_bytes("JPEG"), "sample.jpg"), ".jpg")

    def test_unsupported_format_is_rejected(self):
        with self.assertRaises(UnsupportedImageError):
            validate_image_bytes(image_bytes(), "sample.gif")

    def test_sha256_is_stable(self):
        data = image_bytes()
        self.assertEqual(storage.sha256_bytes(data), storage.sha256_bytes(data))

    def test_original_and_processed_images_are_saved_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, self.storage_context(directory):
            first = storage.store_image_bytes(image_bytes(), "sample.png", self.connection)
            second = storage.store_image_bytes(image_bytes(), "sample.png", self.connection)
            self.assertTrue((Path(directory) / first.original_relative_path).is_file())
            self.assertTrue((Path(directory) / first.processed_relative_path).is_file())
            self.assertEqual(first.sha256, second.sha256)

    def test_preprocessing_generates_grayscale_png(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.jpg"
            output = Path(directory) / "processed.png"
            source.write_bytes(image_bytes("JPEG"))
            info = preprocess_image(source, output)
            self.assertEqual(info["mode"], "L")
            self.assertTrue(output.is_file())

    def test_duplicate_upload_is_detected_by_database_hash(self):
        with tempfile.TemporaryDirectory() as directory, self.storage_context(directory):
            first = service.process_upload(self.connection, image_bytes(), "one.png", FakeAdapter())
            second = service.process_upload(self.connection, image_bytes(), "renamed.png", FakeAdapter())
            self.assertFalse(first["duplicate"])
            self.assertTrue(second["duplicate"])

    def test_ocr_adapter_has_no_network_dependency(self):
        source = Path("src/kubios_screenshot/ocr_adapter.py").read_text(encoding="utf-8")
        for forbidden in ("requests", "urllib", "socket", "http://", "https://"):
            self.assertNotIn(forbidden, source)

    def test_ocr_unavailable_fails_safely(self):
        adapter = VisionOCRAdapter(helper_path="/missing/local/helper")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            path.write_bytes(image_bytes())
            with self.assertRaisesRegex(LocalOCRError, "local_ocr_unavailable"):
                adapter.recognize(path)

    def test_rmssd_is_parsed_same_line(self):
        result = parser.parse_ocr_result(ocr_result(["RMSSD 54 ms", "Date 2026-07-08", "Mean HR 58 bpm"]))
        self.assertEqual(result.fields["rmssd"].value, 54.0)

    def test_rmssd_is_parsed_next_line(self):
        result = parser.parse_ocr_result(ocr_result(["RMSSD", "54 ms", "Date 2026-07-08", "Mean HR 58 bpm"]))
        self.assertEqual(result.fields["rmssd"].value, 54.0)

    def test_mean_hr_alias_is_parsed(self):
        result = parser.parse_ocr_result(ocr_result(["Average Heart Rate: 61 bpm", "Date 2026-07-08", "RMSSD 44 ms"]))
        self.assertEqual(result.fields["mean_hr"].value, 61.0)

    def test_readiness_is_parsed(self):
        result = parser.parse_ocr_result(ocr_result())
        self.assertEqual(result.fields["readiness"].value, 82.0)

    def test_date_is_parsed(self):
        self.assertEqual(parser.parse_ocr_result(ocr_result()).fields["date"].value, "2026-07-08")

    def test_time_is_parsed(self):
        self.assertEqual(parser.parse_ocr_result(ocr_result()).fields["measurement_time"].value, "06:30:00")

    def test_units_increase_field_confidence(self):
        with_unit = parser.parse_ocr_result(ocr_result(["RMSSD 54 ms", "Date 2026-07-08", "Mean HR 58 bpm"]))
        without = parser.parse_ocr_result(ocr_result(["RMSSD 54", "Date 2026-07-08", "Mean HR 58"]))
        self.assertGreater(with_unit.fields["rmssd"].confidence, without.fields["rmssd"].confidence)

    def test_missing_required_fields_are_reported(self):
        result = parser.parse_ocr_result(ocr_result(["Readiness 80"]))
        self.assertEqual(set(result.missing_required_fields), {"date", "rmssd", "mean_hr"})

    def test_obviously_invalid_value_is_rejected_not_medically_interpreted(self):
        result = parser.parse_ocr_result(ocr_result(["Date 2026-07-08", "RMSSD -5 ms", "Mean HR 58 bpm"]))
        self.assertNotIn("rmssd", result.fields)
        self.assertIn("rmssd:outside_recognition_range", result.warnings)

    def test_confidence_band_thresholds(self):
        self.assertEqual(confidence.confidence_band(0.95), "high")
        self.assertEqual(confidence.confidence_band(0.70), "medium")
        self.assertEqual(confidence.confidence_band(0.40), "low")

    def test_every_parse_requires_review_even_at_high_confidence(self):
        result = parser.parse_ocr_result(ocr_result(score=1.0))
        self.assertTrue(result.review_required)

    def test_unconfirmed_result_never_writes_raw_table(self):
        audit_id = self.insert_audit()
        outcome = importer.import_reviewed_result(self.connection, audit_id, {"date": "2026-07-08", "rmssd": 54, "mean_hr": 58}, False)
        self.assertFalse(outcome.success)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM kubios_morning_hrv_raw").fetchone()[0], 0)

    def test_user_modified_values_are_imported_as_reviewed_screenshot(self):
        audit_id = self.insert_audit()
        outcome = importer.import_reviewed_result(self.connection, audit_id, {"date": "2026-07-08", "rmssd": 55, "mean_hr": 59}, True, "keep_both")
        row = self.connection.execute("SELECT * FROM kubios_morning_hrv_raw").fetchone()
        self.assertTrue(outcome.success)
        self.assertEqual(row["rmssd"], 55)
        self.assertEqual(row["source_type"], "screenshot_ocr")
        self.assertEqual(row["import_method"], "screenshot_ocr")
        self.assertEqual(row["reviewed"], 1)

    def test_duplicate_confirmed_import_is_idempotent(self):
        audit_id = self.insert_audit()
        fields = {"date": "2026-07-08", "rmssd": 55, "mean_hr": 59}
        first = importer.import_reviewed_result(self.connection, audit_id, fields, True, "keep_both")
        second = importer.import_reviewed_result(self.connection, audit_id, fields, True, "keep_both")
        self.assertEqual(first.raw_record_id, second.raw_record_id)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM kubios_morning_hrv_raw").fetchone()[0], 1)

    def test_csv_conflict_requires_explicit_resolution(self):
        kubios_import.upsert_kubios_rows(self.connection, [{"date": "2026-07-08", "measurement_time": "2026-07-08T06:00:00", "rmssd": 40, "mean_hr": 60, "readiness": "Good", "raw": {}}])
        audit_id = self.insert_audit()
        outcome = importer.import_reviewed_result(self.connection, audit_id, {"date": "2026-07-08", "rmssd": 55, "mean_hr": 59}, True)
        self.assertEqual(outcome.status, "conflict_review_required")

    def test_csv_remains_priority_when_both_are_kept(self):
        csv_row = {"date": "2026-07-08", "measurement_time": "2026-07-08T06:00:00", "rmssd": 40, "mean_hr": 60, "readiness": "Good", "raw": {}}
        kubios_import.upsert_kubios_rows(self.connection, [csv_row])
        audit_id = self.insert_audit()
        importer.import_reviewed_result(self.connection, audit_id, {"date": "2026-07-08", "rmssd": 55, "mean_hr": 59}, True, "keep_both")
        metric = self.connection.execute("SELECT morning_rmssd FROM daily_recovery_metrics WHERE date='2026-07-08'").fetchone()
        self.assertEqual(metric[0], 40)

    def test_explicit_screenshot_priority_is_persisted(self):
        kubios_import.upsert_kubios_rows(self.connection, [{"date": "2026-07-08", "measurement_time": "2026-07-08T06:00:00", "rmssd": 40, "mean_hr": 60, "readiness": None, "raw": {}}])
        audit_id = self.insert_audit()
        importer.import_reviewed_result(self.connection, audit_id, {"date": "2026-07-08", "rmssd": 55, "mean_hr": 59}, True, "use_screenshot")
        metric = self.connection.execute("SELECT morning_rmssd FROM daily_recovery_metrics WHERE date='2026-07-08'").fetchone()
        self.assertEqual(metric[0], 55)

    def test_batch_partial_failure_does_not_stop_other_images(self):
        with tempfile.TemporaryDirectory() as directory, self.storage_context(directory):
            results = service.process_batch(self.connection, [("ok.png", image_bytes()), ("bad.gif", b"bad")], FakeAdapter())
            self.assertEqual(results[0]["status"], "template_selection_required")
            self.assertEqual(results[1]["status"], "unsupported")

    def test_ocr_failure_creates_safe_audit_without_raw_text(self):
        with tempfile.TemporaryDirectory() as directory, self.storage_context(directory):
            result = service.process_upload(self.connection, image_bytes(), "fail.png", FakeAdapter(error="local_ocr_failed"))
            row = self.connection.execute("SELECT * FROM kubios_screenshot_imports WHERE id=?", (result["audit_id"],)).fetchone()
            self.assertEqual(row["ocr_text_summary"], "")
            self.assertNotIn("RMSSD", row["safe_error_message"])

    def test_audit_summary_contains_only_field_names(self):
        with tempfile.TemporaryDirectory() as directory, self.storage_context(directory):
            stored = storage.store_image_bytes(image_bytes(), "safe.png", self.connection)
            ocr = ocr_result()
            parsed = parser.parse_ocr_result(ocr)
            audit_id = audit.create_audit(self.connection, stored, ocr, parsed)
            summary = self.connection.execute("SELECT ocr_text_summary FROM kubios_screenshot_imports WHERE id=?", (audit_id,)).fetchone()[0]
            self.assertEqual(summary, "fields=date,mean_hr,measurement_time,readiness,rmssd")
            self.assertNotIn("54", summary)

    def test_delete_audit_preserves_formal_record_by_default(self):
        audit_id = self.insert_audit()
        imported = importer.import_reviewed_result(self.connection, audit_id, {"date": "2026-07-08", "rmssd": 55, "mean_hr": 59}, True, "keep_both")
        with tempfile.TemporaryDirectory() as directory, self.storage_context(directory):
            outcome = storage.delete_import(self.connection, audit_id, False, False)
        self.assertTrue(outcome["formal_record_preserved"])
        self.assertIsNotNone(self.connection.execute("SELECT id FROM kubios_morning_hrv_raw WHERE id=?", (imported.raw_record_id,)).fetchone())

    def test_downstream_runs_only_after_confirmed_import(self):
        audit_id = self.insert_audit()
        runner = Mock(return_value={"success": True})
        importer.import_reviewed_result(self.connection, audit_id, {"date": "2026-07-08", "rmssd": 55, "mean_hr": 59}, True, "keep_both", True, runner)
        runner.assert_called_once_with("2026-07-08")

    def test_migration_is_idempotent(self):
        db.apply_migrations(self.connection)
        db.apply_migrations(self.connection)
        self.assertEqual(db.current_schema_version(self.connection), "0.15.0")

    def test_migration_checksum_drift_fails(self):
        self.connection.execute("UPDATE schema_migrations SET checksum='drift' WHERE version='0.6.0'")
        with self.assertRaises(db.DatabaseMigrationError):
            db.apply_migrations(self.connection)

    def test_screenshot_table_and_raw_extensions_exist(self):
        tables = {row[0] for row in self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(kubios_morning_hrv_raw)")}
        self.assertIn("kubios_screenshot_imports", tables)
        self.assertTrue({"source_type", "source_file_sha256", "ocr_confidence", "reviewed", "import_method"}.issubset(columns))

    def test_pipeline_dry_run_does_not_modify_database(self):
        from src.pipeline.kubios_screenshot import run
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            connection = db.connect(path)
            before = connection.total_changes
            connection.close()
            result = run({}, dry_run=True, db_path=path)
            check = sqlite3.connect(path)
            self.assertEqual(result["metrics_updated"], 0)
            self.assertEqual(check.execute("SELECT COUNT(*) FROM kubios_screenshot_imports").fetchone()[0], 0)
            check.close()

    def test_ai_context_allowlist_excludes_screenshot_paths(self):
        source = Path("src/ai_context/whitelist.py").read_text(encoding="utf-8")
        self.assertNotIn("original_relative_path", source)
        self.assertNotIn("processed_relative_path", source)

    def test_cloud_ai_is_not_imported_by_screenshot_modules(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/kubios_screenshot").glob("*.py"))
        self.assertNotIn("openai", combined.lower())
        self.assertNotIn("api_key", combined.lower())

    def test_locales_have_matching_screenshot_keys(self):
        resources = [json.loads(Path(f"locales/{language}.json").read_text(encoding="utf-8"))["kubios_screenshot"] for language in ("zh-CN", "en")]
        self.assertEqual(set(resources[0]), set(resources[1]))

    def test_dashboard_page_degrades_when_audit_table_missing(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        self.assertEqual(audit.list_recent(connection), [])
        connection.close()


if __name__ == "__main__":
    unittest.main()
