"""Streamlit page wrapper for the existing training business page."""

from pathlib import Path
import runpy
import sys

source_pages = Path(__file__).resolve().parents[1] / "src" / "pages"
if str(source_pages) not in sys.path:
    sys.path.insert(0, str(source_pages))

runpy.run_path(str(Path(__file__).resolve().parents[1] / "src" / "dashboard.py"), run_name="__main__")
