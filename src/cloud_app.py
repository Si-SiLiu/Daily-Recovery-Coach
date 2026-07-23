"""Streamlit Community Cloud entry point for the public, synthetic-data demo."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path


# Streamlit Community Cloud may execute this file with ``src`` as the script
# directory rather than the repository root as the import base. Add the
# project root dynamically so both Cloud and local launches resolve ``src``.
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.pages._bootstrap import ensure_project_root

ensure_project_root()


# Never point the public demo at the developer's local data directory.
demo_dir = Path(tempfile.gettempdir()) / "daily-recovery-coach-demo"
demo_dir.mkdir(parents=True, exist_ok=True)
demo_db = demo_dir / "demo.db"
os.environ["DRC_DB_PATH"] = str(demo_db)
os.environ["DRC_STREAMLIT_ENTRYPOINT"] = "cloud_app.py"

from src.db import connect  # noqa: E402


def seed_demo_database() -> None:
    """Create a small, clearly synthetic dataset for first-load usability."""
    with connect(demo_db) as connection:
        existing = connection.execute("SELECT COUNT(*) FROM daily_recovery_metrics").fetchone()[0]
        if existing:
            return
        start = date.today() - timedelta(days=13)
        for offset in range(14):
            day = (start + timedelta(days=offset)).isoformat()
            sleep_score = 68 + (offset % 5) * 4
            hrv = 43 + (offset % 4) * 3
            connection.execute(
                """INSERT INTO daily_recovery_metrics
                (date, steps, calories, active_calories, activity_duration,
                 training_count, training_duration, training_calories,
                 sleep_duration, sleep_score, nightly_hrv_rmssd,
                 nightly_resting_hr, respiration_rate, morning_rmssd,
                 morning_mean_hr, kubios_readiness)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (day, 7200 + offset * 180, 2100 + offset * 12,
                 430 + offset * 8, "PT1H", 1 if offset % 3 else 0,
                 "PT45M" if offset % 3 else "PT0M", 320 if offset % 3 else 0,
                 "PT7H30M", sleep_score, hrv, 57 - (offset % 3),
                 14.2, hrv + 2, 58, "good" if sleep_score >= 76 else "fair"),
            )
            connection.execute(
                """INSERT INTO recovery_scores
                (date, recovery_score, activity_load_score, training_load_score,
                 hrv_score, morning_hr_score, readiness_score, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (day, min(92, 66 + offset), 70, 64, 74, 78, 72,
                 "Demo guidance: adjust today's load according to how you feel."),
            )
        connection.commit()


seed_demo_database()

import streamlit as st  # noqa: E402

st.set_page_config(
    page_title="Daily Recovery Coach Demo",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.info("这是公开体验版，页面使用合成数据。请勿输入真实姓名、健康数据或 Polar 账号。")
st.markdown("反馈入口：请在此处替换为你的问卷链接（Google Form / Tally / 飞书表单）。")

import src.dashboard  # noqa: E402,F401
