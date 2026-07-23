"""Streamlit page wrapper for the source-organized Personal page."""

from pathlib import Path
import runpy
import sys

source_pages = Path(__file__).resolve().parents[1] / "src" / "pages"
if str(source_pages) not in sys.path:
    sys.path.insert(0, str(source_pages))

runpy.run_path(str(Path(__file__).resolve().parents[1] / "src" / "pages" / "5_Personal.py"), run_name="__main__")
