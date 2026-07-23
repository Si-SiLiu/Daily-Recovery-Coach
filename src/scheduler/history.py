"""Scheduler-only trigger provenance and catch-up attempt ledger."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sqlite3
from uuid import uuid4

from . import TRIGGER_TYPES


BASE_DIR = Path(__file__).resolve().parents[2]
SCHEDULER_HISTORY_PATH = BASE_DIR / "data" / "scheduler_history.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS scheduler_runs (
    invocation_id TEXT PRIMARY KEY,
    pipeline_run_id TEXT,
    trigger_type TEXT NOT NULL CHECK (
        trigger_type IN ('manual', 'scheduled', 'catch_up')
    ),
    local_date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    dry_run INTEGER NOT NULL CHECK (dry_run IN (0, 1)),
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    warning_count INTEGER NOT NULL DEFAULT 0,
    result_code TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scheduler_runs_trigger_started
ON scheduler_runs (trigger_type, started_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scheduler_one_catch_up_per_day
ON scheduler_runs (local_date)
WHERE trigger_type = 'catch_up' AND dry_run = 0;
CREATE TABLE IF NOT EXISTS scheduler_catch_up_decisions (
    local_date TEXT PRIMARY KEY,
    decision TEXT NOT NULL CHECK (decision = 'deferred'),
    decided_at TEXT NOT NULL
);
"""


class CatchUpLimitReached(RuntimeError):
    pass


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("SCHEDULER_TIMESTAMP_MUST_BE_AWARE")
    return value.isoformat(timespec="seconds")


class SchedulerHistory:
    def __init__(self, path: Path | str = SCHEDULER_HISTORY_PATH):
        self.path = Path(path)

    def _connect(self, *, create: bool = False):
        if not create and not self.path.exists():
            return None
        if create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        if create:
            connection.executescript(SCHEMA)
        return connection

    def begin(
        self,
        trigger_type: str,
        started_at: datetime,
        *,
        dry_run: bool = False,
    ) -> str:
        if trigger_type not in TRIGGER_TYPES:
            raise ValueError("SCHEDULER_TRIGGER_TYPE_INVALID")
        invocation_id = uuid4().hex
        connection = self._connect(create=True)
        try:
            connection.execute(
                """
                INSERT INTO scheduler_runs (
                    invocation_id, trigger_type, local_date, started_at,
                    dry_run, status, result_code
                ) VALUES (?, ?, ?, ?, ?, 'running', 'RUNNING')
                """,
                (
                    invocation_id,
                    trigger_type,
                    started_at.date().isoformat(),
                    _iso(started_at),
                    int(bool(dry_run)),
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            if trigger_type == "catch_up" and not dry_run:
                raise CatchUpLimitReached("CATCH_UP_LIMIT_REACHED") from None
            raise exc
        finally:
            connection.close()
        return invocation_id

    def finish(
        self,
        invocation_id: str,
        finished_at: datetime,
        *,
        success: bool,
        pipeline_run_id: str | None,
        warning_count: int = 0,
        result_code: str,
    ) -> None:
        connection = self._connect(create=True)
        try:
            cursor = connection.execute(
                """
                UPDATE scheduler_runs
                SET pipeline_run_id = ?, finished_at = ?, status = ?,
                    warning_count = ?, result_code = ?
                WHERE invocation_id = ? AND status = 'running'
                """,
                (
                    pipeline_run_id,
                    _iso(finished_at),
                    "success" if success else "failed",
                    max(0, int(warning_count or 0)),
                    result_code,
                    invocation_id,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("SCHEDULER_INVOCATION_NOT_RUNNING")
            connection.commit()
        finally:
            connection.close()

    def catch_up_attempts_on(self, local_date: date) -> int:
        connection = self._connect()
        if connection is None:
            return 0
        try:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM scheduler_runs
                WHERE trigger_type = 'catch_up' AND dry_run = 0
                  AND local_date = ?
                """,
                (local_date.isoformat(),),
            ).fetchone()
            return int(row["count"])
        except sqlite3.OperationalError:
            return 0
        finally:
            connection.close()

    def latest(self, trigger_type: str) -> dict | None:
        if trigger_type not in TRIGGER_TYPES:
            raise ValueError("SCHEDULER_TRIGGER_TYPE_INVALID")
        connection = self._connect()
        if connection is None:
            return None
        try:
            row = connection.execute(
                """
                SELECT invocation_id, pipeline_run_id, trigger_type, local_date,
                       started_at, finished_at, dry_run, status, warning_count,
                       result_code
                FROM scheduler_runs
                WHERE trigger_type = ? AND dry_run = 0
                ORDER BY started_at DESC, rowid DESC
                LIMIT 1
                """,
                (trigger_type,),
            ).fetchone()
            return dict(row) if row else None
        except sqlite3.OperationalError:
            return None
        finally:
            connection.close()

    def defer_catch_up(self, when: datetime) -> None:
        connection = self._connect(create=True)
        try:
            connection.execute(
                """
                INSERT INTO scheduler_catch_up_decisions (
                    local_date, decision, decided_at
                ) VALUES (?, 'deferred', ?)
                ON CONFLICT(local_date) DO UPDATE SET
                    decision = excluded.decision,
                    decided_at = excluded.decided_at
                """,
                (when.date().isoformat(), _iso(when)),
            )
            connection.commit()
        finally:
            connection.close()

    def catch_up_deferred_on(self, local_date: date) -> bool:
        connection = self._connect()
        if connection is None:
            return False
        try:
            row = connection.execute(
                """
                SELECT 1 FROM scheduler_catch_up_decisions
                WHERE local_date = ? AND decision = 'deferred'
                """,
                (local_date.isoformat(),),
            ).fetchone()
            return row is not None
        except sqlite3.OperationalError:
            return False
        finally:
            connection.close()
