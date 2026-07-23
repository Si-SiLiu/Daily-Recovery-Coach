"""Streamlit page wrapper for the source-organized Nutrition page."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / "src" / "pages" / "3_Nutrition.py"), run_name="__main__")
