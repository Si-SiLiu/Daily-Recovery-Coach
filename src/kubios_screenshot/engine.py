import argparse
import json
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .ocr_adapter import VisionOCRAdapter
from .parser import parse_ocr_result


def create_synthetic_fixture(path):
    image = Image.new("RGB", (1200, 900), "white")
    draw = ImageDraw.Draw(image)
    font_path = "/System/Library/Fonts/Helvetica.ttc"
    font = ImageFont.truetype(font_path, 54) if Path(font_path).exists() else ImageFont.load_default()
    lines = ["KUBIOS HRV", "Date 2026-01-02", "Time 06:30", "RMSSD 54 ms", "Mean HR 58 bpm", "Readiness 82"]
    for index, line in enumerate(lines):
        draw.text((80, 80 + index * 110), line, fill="black", font=font)
    image.save(path, format="PNG")


def run_synthetic_test(adapter=None):
    adapter = adapter or VisionOCRAdapter()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "synthetic_kubios.png"
        create_synthetic_fixture(path)
        ocr = adapter.recognize(path)
        parsed = parse_ocr_result(ocr)
    found = sorted(parsed.fields)
    required = {"date", "rmssd", "mean_hr"}
    return {
        "synthetic": True,
        "success": required.issubset(found),
        "engine": ocr.engine,
        "fields_found": found,
        "missing_required_fields": parsed.missing_required_fields,
        "overall_confidence": parsed.overall_confidence,
        "real_measurement": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local Kubios screenshot recognition engine.")
    parser.add_argument("--synthetic-test", action="store_true")
    args = parser.parse_args(argv)
    if not args.synthetic_test:
        parser.error("--synthetic-test is required; real images are reviewed in the App.")
    result = run_synthetic_test()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
