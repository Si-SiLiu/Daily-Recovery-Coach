"""Streamlit page wrapper for the existing training business page."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / "src" / "dashboard.py"), run_name="__main__")
