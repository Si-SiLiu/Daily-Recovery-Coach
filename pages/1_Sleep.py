"""Streamlit page wrapper for the source-organized Sleep page."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / "src" / "pages" / "1_Sleep.py"), run_name="__main__")
