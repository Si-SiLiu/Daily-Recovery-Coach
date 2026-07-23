"""Stable local branding assets with a non-failing Streamlit fallback."""

from pathlib import Path

from PIL import Image


BASE_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = BASE_DIR / "assets"
PAGE_ICON_PATH = ASSETS_DIR / "app_icon_64.png"
BRAND_ICON_PATH = ASSETS_DIR / "app_icon_256.png"


def load_page_icon(path: Path = PAGE_ICON_PATH):
    """Return a detached PIL image or an emoji fallback when unavailable."""
    try:
        with Image.open(path) as image:
            return image.convert("RGBA").copy()
    except (OSError, ValueError):
        return "💚"


def brand_icon_path(path: Path = BRAND_ICON_PATH) -> Path | None:
    """Return the optimized brand asset only when it is locally readable."""
    return path if path.is_file() else None
