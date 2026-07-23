"""Measure template-parser accuracy; never print recognized health values or OCR text."""

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.kubios_screenshot.config import load_config
from src.kubios_screenshot.field_ocr import parse_template_regions
from src.kubios_screenshot.ocr_adapter import VisionOCRAdapter
from src.kubios_screenshot.template_detector import detect_template
from src.kubios_screenshot.templates import get_template, load_template_config


FIXTURE_ROOT = BASE_DIR / "tests" / "fixtures" / "kubios_screenshots"
NUMERIC_EVALUATION_FIELDS = {
    "rmssd", "mean_hr", "readiness", "sdnn", "pns_index", "sns_index",
    "stress_index", "mean_rr_ms", "poincare_sd1_ms", "poincare_sd2_ms",
    "respiratory_rate_bpm", "lf_power_ms2", "hf_power_ms2", "lf_power_nu",
    "hf_power_nu", "lf_hf_ratio", "physiological_age",
}


def exact_match(actual, expected):
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return abs(float(actual) - float(expected)) < 1e-9
        except (TypeError, ValueError):
            return False
    return actual == expected


def evaluate_directory(directory, adapter=None):
    directory = Path(directory)
    adapter = adapter or VisionOCRAdapter()
    template_config = load_template_config()
    parser_config = load_config()
    samples = []
    for image_path in sorted(directory.glob("*.png")):
        truth_path = image_path.with_suffix(".ground_truth.json")
        if truth_path.is_file():
            samples.append((image_path, json.loads(truth_path.read_text(encoding="utf-8"))))
    fields = tuple(parser_config["supported_fields"])
    field_hits = {field: 0 for field in fields}
    field_totals = {field: 0 for field in fields}
    template_hits = required_complete = numeric_hits = numeric_total = manual_corrections = failures = 0
    failure_samples = []
    for image_path, truth in samples:
        ocr = adapter.recognize(image_path)
        detection = detect_template(ocr.image_size, ocr.text_blocks, template_config)
        template_hits += int(detection.template_id == truth["template_id"])
        template = get_template(truth["template_id"], template_config)
        parsed = parse_template_regions(image_path, template, adapter, parser_config)
        mismatch = False
        for field in fields:
            if field not in truth:
                continue
            field_totals[field] += 1
            actual = parsed.fields.get(field).value if field in parsed.fields else None
            hit = exact_match(actual, truth[field])
            field_hits[field] += int(hit)
            mismatch = mismatch or not hit
            if field in NUMERIC_EVALUATION_FIELDS:
                numeric_total += 1
                numeric_hits += int(hit)
        required = parser_config["minimum_required_fields"]
        complete = all(field in truth for field in required) and all(
            field in parsed.fields and exact_match(parsed.fields[field].value, truth[field])
            for field in required
        )
        required_complete += int(complete)
        manual_corrections += int(mismatch)
        failed = not parsed.fields
        failures += int(failed)
        if mismatch or failed:
            failure_samples.append(image_path.name)
    count = len(samples)
    percentage = lambda hits, total: round(100 * hits / total, 2) if total else None
    return {
        "dataset": directory.name,
        "sample_count": count,
        "template_detection_accuracy": percentage(template_hits, count),
        "required_field_exact_match_rate": percentage(required_complete, count),
        "numeric_field_accuracy": percentage(numeric_hits, numeric_total),
        "per_field_accuracy": {field: percentage(field_hits[field], field_totals[field]) for field in fields if field_totals[field]},
        "manual_correction_rate": percentage(manual_corrections, count),
        "total_failure_rate": percentage(failures, count),
        "failure_samples": failure_samples,
        "contains_real_measurements": directory.name == "anonymized_real" and count > 0,
    }


def print_summary(result):
    print(f"Dataset: {result['dataset']}")
    print(f"Sample count: {result['sample_count']}")
    print(f"Template detection accuracy: {result['template_detection_accuracy']}")
    print(f"Required-field exact match rate: {result['required_field_exact_match_rate']}")
    print(f"Numeric-field accuracy: {result['numeric_field_accuracy']}")
    print("Per-field accuracy: " + json.dumps(result["per_field_accuracy"], sort_keys=True))
    print(f"Manual correction rate: {result['manual_correction_rate']}")
    print(f"Total failure rate: {result['total_failure_rate']}")
    print("Failure samples: " + (", ".join(result["failure_samples"]) or "none"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate template-based local Kubios screenshot parsing.")
    parser.add_argument("--dataset", choices=("synthetic", "anonymized_real", "all"), default="all")
    args = parser.parse_args(argv)
    names = ("synthetic", "anonymized_real") if args.dataset == "all" else (args.dataset,)
    results = [evaluate_directory(FIXTURE_ROOT / name) for name in names]
    for result in results:
        print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
