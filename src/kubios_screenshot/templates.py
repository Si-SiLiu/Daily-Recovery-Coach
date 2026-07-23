import copy
import json
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATE_CONFIG_PATH = BASE_DIR / "config" / "kubios_screenshot_templates.json"
CALIBRATION_PATH = BASE_DIR / "config" / "kubios_screenshot_template_calibrations.json"


def validate_region(region):
    for key in ("x", "y", "width", "height"):
        value = float(region[key])
        if not 0 <= value <= 1:
            raise ValueError(f"template_region_{key}_outside_normalized_range")
    if region["width"] <= 0 or region["height"] <= 0:
        raise ValueError("template_region_empty")
    if region["x"] + region["width"] > 1 or region["y"] + region["height"] > 1:
        raise ValueError("template_region_outside_image")


@lru_cache(maxsize=4)
def load_template_config(path=TEMPLATE_CONFIG_PATH, calibration_path=CALIBRATION_PATH):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    templates = config.get("templates", [])
    ids = [item.get("template_id") for item in templates]
    if len(ids) != len(set(ids)) or not all(ids):
        raise ValueError("template_ids_must_be_unique")
    for template in templates:
        for region in template.get("field_regions", {}).values():
            validate_region(region)
    try:
        calibrations = json.loads(Path(calibration_path).read_text(encoding="utf-8")).get("calibrations", {})
    except (OSError, json.JSONDecodeError):
        calibrations = {}
    merged = copy.deepcopy(config)
    for template in merged["templates"]:
        overrides = calibrations.get(template["template_id"], {}).get("field_regions", {})
        for field, region in overrides.items():
            if field in template["field_regions"]:
                validate_region(region)
                template["field_regions"][field].update(region)
    return merged


def list_templates(config=None):
    return (config or load_template_config())["templates"]


def get_template(template_id, config=None):
    for template in list_templates(config):
        if template["template_id"] == template_id:
            return template
    raise KeyError(f"unsupported_template:{template_id}")


def clear_template_cache():
    load_template_config.cache_clear()
