"""Bootstrap the repository root before a Streamlit source page imports ``src``."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def ensure_project_root() -> None:
    """Make the repository root importable for direct page execution."""
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
