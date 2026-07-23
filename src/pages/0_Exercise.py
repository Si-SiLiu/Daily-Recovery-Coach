"""Training page entrypoint backed by the existing training dashboard."""

import runpy
import sys
from pathlib import Path


project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.pages._bootstrap import ensure_project_root

ensure_project_root()
runpy.run_path(str(project_root / "src" / "dashboard.py"), run_name="__main__")
