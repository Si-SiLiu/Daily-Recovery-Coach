import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path

from src.pipeline import STEP_NAMES
from src.pipeline.history import SyncHistory
from src.pipeline.logger import PipelineLogger
from src.pipeline.token import run as run_token_step
from src.sync_pipeline import PipelineRunner


class DryRunTests(unittest.TestCase):
    def test_dry_run_executes_checks_without_history_database_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history_path = root / "history.db"
            calls = []

            def make_step(name):
                def step(context, dry_run=False):
                    self.assertTrue(dry_run)
                    calls.append(name)
                    return {}

                return step

            logger = PipelineLogger(root / "sync.log")
            runner = PipelineRunner(
                steps={name: make_step(name) for name in STEP_NAMES},
                history=SyncHistory(history_path),
                logger=logger,
                lock_factory=lambda trigger_type: nullcontext(),
            )
            summary = runner.run(dry_run=True)
            logger.close()

            self.assertEqual(calls, list(STEP_NAMES))
            self.assertTrue(summary["dry_run"])
            self.assertFalse(history_path.exists())

    def test_token_dry_run_checks_existence_without_loading_token(self):
        with tempfile.TemporaryDirectory() as directory:
            token_path = Path(directory) / "tokens.json"
            token_path.write_text("not-read", encoding="utf-8")

            def forbidden_client():
                raise AssertionError("client must not be created during dry run")

            result = run_token_step(
                {},
                dry_run=True,
                client_factory=forbidden_client,
                token_file=token_path,
            )
            self.assertTrue(result["token_available"])


if __name__ == "__main__":
    unittest.main()
