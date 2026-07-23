import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path

from src.pipeline import STEP_NAMES
from src.pipeline.history import SyncHistory
from src.pipeline.logger import PipelineLogger
from src.sync_pipeline import PipelineRunner


class LocalCoachPipelineTests(unittest.TestCase):
    def test_order_is_after_confidence_and_before_report(self):
        self.assertLess(STEP_NAMES.index("confidence"), STEP_NAMES.index("local-coach"))
        self.assertLess(STEP_NAMES.index("local-coach"), STEP_NAMES.index("report"))

    def test_selective_local_coach(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            steps = {name: (lambda context, dry_run=False, name=name: calls.append(name) or
                            ({"local_coach_records_updated": 2} if name == "local-coach" else {})) for name in STEP_NAMES}
            logger = PipelineLogger(Path(directory) / "sync.log")
            runner = PipelineRunner(
                steps=steps,
                history=SyncHistory(Path(directory) / "history.db"),
                logger=logger,
                lock_factory=lambda trigger_type: nullcontext(),
            )
            result = runner.run(only="local-coach")
            logger.close()
        self.assertEqual(calls, ["local-coach"])
        self.assertEqual(result["local_coach_records_updated"], 2)

    def test_history_schema_records_local_count(self):
        with tempfile.TemporaryDirectory() as directory:
            history = SyncHistory(Path(directory) / "history.db")
            history.record("r", "a", "b", 1, True, "local-coach", "completed", local_coach_records_updated=3)
            self.assertEqual(history.aggregate_run("r")["local_coach_records_updated"], 3)

    def test_history_records_prospective_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            history = SyncHistory(Path(directory) / "history.db")
            history.record("r", "a", "b", 1, True, "local-coach", "completed",
                           prospective_eligible_days=4)
            self.assertEqual(history.aggregate_run("r")["prospective_eligible_days"], 4)


if __name__ == "__main__":
    unittest.main()
