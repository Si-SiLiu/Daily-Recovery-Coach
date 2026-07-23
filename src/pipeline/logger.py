import logging
from pathlib import Path
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = BASE_DIR / "logs" / "sync.log"


class PipelineLogger:
    def __init__(self, path=LOG_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"sync_pipeline.{uuid4().hex}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        handler = logging.FileHandler(self.path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        self.logger.addHandler(handler)

    def pipeline_started(self, run_id, dry_run=False, only=None, resume=False):
        self.logger.info(
            "pipeline_started run_id=%s dry_run=%s only=%s resume=%s",
            run_id,
            dry_run,
            only or "all",
            resume,
        )

    def step_started(self, run_id, step):
        self.logger.info("step_started run_id=%s step=%s", run_id, step)

    def step_finished(self, run_id, step, duration):
        self.logger.info(
            "step_finished run_id=%s step=%s success=true duration=%.3f",
            run_id,
            step,
            duration,
        )

    def step_failed(self, run_id, step, duration, error_code):
        self.logger.error(
            "step_finished run_id=%s step=%s success=false duration=%.3f error_code=%s",
            run_id,
            step,
            duration,
            error_code,
        )

    def pipeline_finished(self, run_id, duration, success):
        self.logger.info(
            "pipeline_finished run_id=%s success=%s duration=%.3f",
            run_id,
            str(bool(success)).lower(),
            duration,
        )

    def close(self):
        for handler in list(self.logger.handlers):
            handler.close()
            self.logger.removeHandler(handler)
