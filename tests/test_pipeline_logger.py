import tempfile
import unittest
from pathlib import Path

from src.pipeline.logger import PipelineLogger


class PipelineLoggerTests(unittest.TestCase):
    def test_logger_records_lifecycle_without_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sync.log"
            logger = PipelineLogger(path)
            logger.pipeline_started("run-1", dry_run=True)
            logger.step_started("run-1", "fetch")
            logger.step_finished("run-1", "fetch", 0.25)
            logger.pipeline_finished("run-1", 0.5, True)
            logger.close()
            document = path.read_text(encoding="utf-8")

        self.assertIn("pipeline_started", document)
        self.assertIn("step_started", document)
        self.assertIn("step_finished", document)
        self.assertIn("success=true", document)
        self.assertNotIn("access_token", document.lower())
        self.assertNotIn("refresh_token", document.lower())

    def test_logger_records_safe_failure_type(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sync.log"
            logger = PipelineLogger(path)
            logger.step_failed("run-2", "token", 0.1, "RuntimeError")
            logger.close()
            document = path.read_text(encoding="utf-8")
        self.assertIn("success=false", document)
        self.assertIn("error_code=RuntimeError", document)


if __name__ == "__main__":
    unittest.main()
