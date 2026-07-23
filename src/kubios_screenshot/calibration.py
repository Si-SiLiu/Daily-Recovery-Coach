import json
from datetime import datetime
from pathlib import Path

from .templates import CALIBRATION_PATH, clear_template_cache, get_template, validate_region


def save_calibration(template_id, field_regions, confirmed=False, path=CALIBRATION_PATH):
    if not confirmed:
        raise ValueError("calibration_confirmation_required")
    get_template(template_id)
    cleaned = {}
    for field, region in field_regions.items():
        normalized = {key: round(float(region[key]), 5) for key in ("x", "y", "width", "height")}
        validate_region(normalized)
        cleaned[field] = normalized
    path = Path(path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        document = {"version": "1.0.0", "calibrations": {}}
    document.setdefault("calibrations", {})[template_id] = {
        "field_regions": cleaned,
        "confirmed_by_user": True,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    clear_template_cache()
    return path
