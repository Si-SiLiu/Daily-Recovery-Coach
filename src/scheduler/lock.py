"""Crash-safe cross-process exclusion for all sync trigger types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import errno
import fcntl
import json
import os
from pathlib import Path
import socket
import time


BASE_DIR = Path(__file__).resolve().parents[2]
LOCK_PATH = BASE_DIR / "data" / "sync_pipeline.lock"


class PipelineLockBusy(RuntimeError):
    """Raised when another process still owns the pipeline lock."""


@dataclass(frozen=True)
class LockOwner:
    pid: int | None
    acquired_at: str | None
    trigger_type: str | None
    metadata_present: bool = False


def _read_owner(handle) -> LockOwner:
    try:
        handle.seek(0)
        raw = handle.read()
        if not raw.strip():
            return LockOwner(None, None, None, False)
        value = json.loads(raw)
        pid = value.get("pid")
        return LockOwner(
            pid=pid if type(pid) is int and pid > 0 else None,
            acquired_at=(
                value.get("acquired_at")
                if isinstance(value.get("acquired_at"), str)
                else None
            ),
            trigger_type=(
                value.get("trigger_type")
                if isinstance(value.get("trigger_type"), str)
                else None
            ),
            metadata_present=True,
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return LockOwner(None, None, None, True)


def _metadata_is_abandoned(owner: LockOwner, now: datetime, stale_after: float) -> bool:
    if not owner.metadata_present:
        return False
    if not owner.acquired_at:
        return True
    try:
        acquired = datetime.fromisoformat(owner.acquired_at)
        if acquired.tzinfo is None:
            acquired = acquired.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return (now.astimezone(timezone.utc) - acquired.astimezone(timezone.utc)).total_seconds() > stale_after


class PipelineLock:
    """Use kernel flock so an abnormal process exit releases the lock automatically.

    The on-disk metadata is diagnostic only. It may survive a crash; the next owner
    safely replaces it after acquiring the kernel lock.
    """

    def __init__(
        self,
        path: Path | str = LOCK_PATH,
        *,
        acquire_timeout_seconds: float = 0.0,
        stale_metadata_seconds: float = 6 * 60 * 60,
        poll_interval_seconds: float = 0.05,
        trigger_type: str = "unknown",
    ):
        if acquire_timeout_seconds < 0 or stale_metadata_seconds <= 0:
            raise ValueError("SCHEDULER_LOCK_TIMEOUT_INVALID")
        self.path = Path(path)
        self.acquire_timeout_seconds = float(acquire_timeout_seconds)
        self.stale_metadata_seconds = float(stale_metadata_seconds)
        self.poll_interval_seconds = max(0.001, float(poll_interval_seconds))
        self.trigger_type = trigger_type
        self._handle = None
        self.recovered_abandoned_metadata = False

    @property
    def acquired(self) -> bool:
        return self._handle is not None

    def acquire(self) -> "PipelineLock":
        if self.acquired:
            raise RuntimeError("SCHEDULER_LOCK_ALREADY_ACQUIRED")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        deadline = time.monotonic() + self.acquire_timeout_seconds
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    handle.close()
                    raise
                if time.monotonic() >= deadline:
                    owner = _read_owner(handle)
                    handle.close()
                    raise PipelineLockBusy(
                        f"SYNC_ALREADY_RUNNING:pid={owner.pid or 'unknown'}"
                    ) from None
                time.sleep(self.poll_interval_seconds)

        now = datetime.now(timezone.utc)
        old_owner = _read_owner(handle)
        self.recovered_abandoned_metadata = _metadata_is_abandoned(
            old_owner, now, self.stale_metadata_seconds
        )
        metadata = {
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "acquired_at": now.isoformat(timespec="seconds"),
            "trigger_type": self.trigger_type,
        }
        handle.seek(0)
        handle.truncate()
        json.dump(metadata, handle, ensure_ascii=True, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
        self._handle = handle
        return self

    def release(self) -> None:
        handle, self._handle = self._handle, None
        if handle is None:
            return
        try:
            handle.seek(0)
            handle.truncate()
            handle.flush()
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def __enter__(self) -> "PipelineLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


def pipeline_is_running(path: Path | str = LOCK_PATH) -> bool:
    """Inspect lock ownership without trusting stale metadata."""
    lock_path = Path(path)
    if not lock_path.exists():
        return False
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                return True
            raise
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return False
    finally:
        handle.close()
