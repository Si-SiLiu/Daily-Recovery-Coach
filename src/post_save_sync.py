"""Start a canonical local sync after today's recovery data is saved."""

from __future__ import annotations

from pathlib import Path
import subprocess


BASE_DIR = Path(__file__).resolve().parents[1]


def start_recovery_post_save_sync() -> int:
    """Start the full post-recovery sync without blocking the UI."""
    python = BASE_DIR / ".venv" / "bin" / "python"
    runner = BASE_DIR / "scripts" / "run_scheduled_sync.py"
    if not python.is_file() or not runner.is_file():
        raise RuntimeError("同步运行环境不完整")
    process = subprocess.Popen(
        [str(python), str(runner), "--trigger-type", "manual"],
        cwd=BASE_DIR,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return process.pid
