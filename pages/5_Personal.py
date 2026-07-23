"""Streamlit page wrapper for the source-organized Personal page."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / "src" / "pages" / "5_Personal.py"), run_name="__main__")
