"""Read-only scheduling and catch-up state calculations for the UI boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

from src.pipeline.history import HISTORY_PATH, SyncHistory

from .config import SchedulerConfig
from .history import SchedulerHistory
from .lock import LOCK_PATH, pipeline_is_running


@dataclass(frozen=True)
class CatchUpState:
    state: str
    eligible: bool
    should_prompt: bool
    today_synced: bool
    attempts_today: int
    reason_code: str


@dataclass(frozen=True)
class DailySchedulerStatus:
    enabled: bool
    sync_time: str
    timezone_mode: str
    today_synced: bool
    pipeline_running: bool
    next_scheduled_at: str | None
    latest_scheduled_at: str | None
    latest_scheduled_result: str | None
    latest_scheduled_warning_count: int | None


def _local_now(now: datetime | None = None) -> datetime:
    value = now or datetime.now().astimezone()
    if value.tzinfo is None:
        raise ValueError("SCHEDULER_TIMESTAMP_MUST_BE_AWARE")
    return value


def _parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else parsed.astimezone()


def has_successful_sync_today(
    history_path: Path | str = HISTORY_PATH,
    *,
    now: datetime | None = None,
) -> bool:
    """Read the canonical pipeline history; never infer success from scheduler state."""
    local_now = _local_now(now)
    path = Path(history_path)
    if not path.exists():
        return False
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute(
            """
            SELECT finish_time FROM sync_history
            WHERE step = 'pipeline' AND success = 1
              AND message NOT LIKE 'completed_selective:%'
            ORDER BY id DESC
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()
    for (finished_at,) in rows:
        parsed = _parse_timestamp(finished_at)
        if parsed and parsed.astimezone(local_now.tzinfo).date() == local_now.date():
            return True
    return False


def scheduled_datetime(config: SchedulerConfig, *, now: datetime | None = None) -> datetime:
    local_now = _local_now(now)
    return local_now.replace(
        hour=config.hour,
        minute=config.minute,
        second=0,
        microsecond=0,
    )


def next_scheduled_datetime(
    config: SchedulerConfig,
    *,
    now: datetime | None = None,
) -> datetime | None:
    if not config.enabled:
        return None
    local_now = _local_now(now)
    candidate = scheduled_datetime(config, now=local_now)
    return candidate if candidate > local_now else candidate + timedelta(days=1)


def evaluate_catch_up(
    config: SchedulerConfig,
    *,
    scheduler_history: SchedulerHistory,
    sync_history_path: Path | str = HISTORY_PATH,
    lock_path: Path | str = LOCK_PATH,
    now: datetime | None = None,
) -> CatchUpState:
    """Calculate UI state only; this function never starts a sync."""
    local_now = _local_now(now)
    today_synced = has_successful_sync_today(sync_history_path, now=local_now)
    attempts = scheduler_history.catch_up_attempts_on(local_now.date())
    if not config.enabled or not config.catch_up_on_app_start:
        return CatchUpState(
            "disabled", False, False, today_synced, attempts, "CATCH_UP_DISABLED"
        )
    if today_synced:
        return CatchUpState(
            "already_synced", False, False, True, attempts, "TODAY_ALREADY_SYNCED"
        )
    if local_now < scheduled_datetime(config, now=local_now):
        return CatchUpState(
            "not_due", False, False, False, attempts, "SCHEDULE_NOT_REACHED"
        )
    if config.max_catch_up_runs_per_day == 0 or attempts >= config.max_catch_up_runs_per_day:
        return CatchUpState(
            "limit_reached", False, False, False, attempts, "CATCH_UP_LIMIT_REACHED"
        )
    if scheduler_history.catch_up_deferred_on(local_now.date()):
        return CatchUpState(
            "deferred", False, False, False, attempts, "CATCH_UP_DEFERRED"
        )
    if pipeline_is_running(lock_path):
        return CatchUpState(
            "sync_running", False, False, False, attempts, "SYNC_ALREADY_RUNNING"
        )
    return CatchUpState(
        "prompt_required" if config.prompt_before_catch_up else "eligible",
        True,
        config.prompt_before_catch_up,
        False,
        attempts,
        "TODAY_SYNC_MISSING",
    )


def get_daily_scheduler_status(
    config: SchedulerConfig,
    *,
    scheduler_history: SchedulerHistory,
    sync_history_path: Path | str = HISTORY_PATH,
    lock_path: Path | str = LOCK_PATH,
    now: datetime | None = None,
) -> DailySchedulerStatus:
    local_now = _local_now(now)
    latest = SyncHistory(sync_history_path).last_sync_by_trigger("scheduled")
    next_run = next_scheduled_datetime(config, now=local_now)
    return DailySchedulerStatus(
        enabled=config.enabled,
        sync_time=config.sync_time,
        timezone_mode=config.timezone_mode,
        today_synced=has_successful_sync_today(sync_history_path, now=local_now),
        pipeline_running=pipeline_is_running(lock_path),
        next_scheduled_at=(next_run.isoformat(timespec="minutes") if next_run else None),
        latest_scheduled_at=(latest.get("finish_time") if latest else None),
        latest_scheduled_result=(
            "success" if latest and latest.get("success") else "failed" if latest else None
        ),
        latest_scheduled_warning_count=(
            int(latest.get("warning_count", 0)) if latest else None
        ),
    )
