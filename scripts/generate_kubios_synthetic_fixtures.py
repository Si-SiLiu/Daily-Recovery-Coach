"""Generate clearly labeled synthetic fixtures; no real health data is used."""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.kubios_screenshot.region_extractor import region_pixels
from src.kubios_screenshot.templates import list_templates


OUTPUT_DIR = BASE_DIR / "tests" / "fixtures" / "kubios_screenshots" / "synthetic"
GROUND_TRUTH = {
    "readiness_summary": {
        "date": "2026-01-02", "measurement_time": "06:30:00",
        "rmssd": 54.5, "mean_hr": 58, "readiness": 82,
        "sdnn": 62.0, "pns_index": 1.4, "sns_index": -0.8,
    },
    "measurement_details": {
        "date": "2026-02-03", "measurement_time": "07:15:00",
        "rmssd": 48.0, "mean_hr": 61, "readiness": 76,
        "sdnn": 57.5, "pns_index": 0.9, "sns_index": -0.3,
    },
    "results_summary": {
        "date": "2026-03-04", "measurement_time": "05:45:00",
        "rmssd": 63.2, "mean_hr": 55, "readiness": 88,
        "sdnn": 70.1, "pns_index": 1.8, "sns_index": -1.1,
    },
}


def font(size):
    path = "/System/Library/Fonts/Helvetica.ttc"
    return ImageFont.truetype(path, size) if Path(path).exists() else ImageFont.load_default()


def display_value(field, value):
    if field == "measurement_time":
        return str(value)[:5]
    return str(value)


def generate_fixture(template):
    width, height = 1200, 2400
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 190), fill=(20, 40, 70))
    draw.text((55, 28), "KUBIOS HRV", fill="white", font=font(58))
    anchors = "  •  ".join(template["anchor_labels"])
    draw.text((55, 115), anchors, fill=(205, 225, 245), font=font(30))
    all_truth = GROUND_TRUTH[template["template_id"]]
    truth = {field: all_truth[field] for field in template["field_regions"] if field in all_truth}
    for field, region in template["field_regions"].items():
        if field not in truth:
            continue
        box = region_pixels((width, height), region)
        draw.rounded_rectangle(box, radius=18, fill=(245, 248, 252), outline=(190, 205, 220), width=3)
        value = display_value(field, truth[field])
        value_font = font(64 if field not in {"date", "measurement_time"} else 48)
        text_box = draw.textbbox((0, 0), value, font=value_font)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        x = box[0] + (box[2] - box[0] - text_width) / 2
        y = box[1] + (box[3] - box[1] - text_height) / 2 - 6
        draw.text((x, y), value, fill=(15, 25, 35), font=value_font)
    image.save(OUTPUT_DIR / f"{template['template_id']}.png", format="PNG", optimize=True)
    (OUTPUT_DIR / f"{template['template_id']}.ground_truth.json").write_text(
        json.dumps({"template_id": template["template_id"], **truth}, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for template in list_templates():
        generate_fixture(template)
    print(f"Generated {len(list_templates())} synthetic Kubios fixtures")


if __name__ == "__main__":
    main()
