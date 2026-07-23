import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path

from src.pipeline import STEP_NAMES
from src.pipeline.history import SyncHistory
from src.pipeline.logger import PipelineLogger
from src.sync_pipeline import PipelineError, PipelineRunner


class ResumeTests(unittest.TestCase):
    def test_resume_skips_completed_steps_and_continues_failed_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history = SyncHistory(root / "history.db")
            calls = []
            fail_once = {"metrics": True}

            def make_step(name):
                def step(context, dry_run=False):
                    calls.append(name)
                    if name == "metrics" and fail_once["metrics"]:
                        fail_once["metrics"] = False
                        raise RuntimeError("synthetic failure")
                    return {"reports_generated": 1} if name == "report" else {}

                return step

            steps = {name: make_step(name) for name in STEP_NAMES}
            first_logger = PipelineLogger(root / "first.log")
            first = PipelineRunner(
                steps=steps,
                history=history,
                logger=first_logger,
                lock_factory=lambda trigger_type: nullcontext(),
            )
            with self.assertRaises(PipelineError):
                first.run()
            first_logger.close()
            failed_run_id = history.latest_failed_run_id()
            self.assertIsNotNone(failed_run_id)
            self.assertEqual(calls, ["token", "fetch", "import", "manual-summary", "metrics"])

            calls.clear()
            second_logger = PipelineLogger(root / "second.log")
            second = PipelineRunner(
                steps=steps,
                history=history,
                logger=second_logger,
                lock_factory=lambda trigger_type: nullcontext(),
            )
            summary = second.run(resume=True)
            second_logger.close()

            self.assertEqual(
                calls,
                ["metrics", "resolution", "baseline", "recovery", "confidence", "local-coach", "report", "governance"],
            )
            self.assertEqual(summary["run_id"], failed_run_id)
            self.assertTrue(summary["resumed"])
            self.assertTrue(summary["success"])
            self.assertIsNone(history.latest_failed_run_id())

    def test_resume_requires_interrupted_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logger = PipelineLogger(root / "sync.log")
            runner = PipelineRunner(
                steps={name: (lambda context, dry_run=False: {}) for name in STEP_NAMES},
                history=SyncHistory(root / "history.db"),
                logger=logger,
                lock_factory=lambda trigger_type: nullcontext(),
            )
            with self.assertRaises(ValueError):
                runner.run(resume=True)
            logger.close()


if __name__ == "__main__":
    unittest.main()
