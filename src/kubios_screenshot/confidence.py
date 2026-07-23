from statistics import mean

from .config import load_config


def field_confidence(ocr_confidence, label_exact=True, unit_match=True, value_valid=True, adjacent=True):
    score = max(0.0, min(float(ocr_confidence), 1.0)) * 0.55
    score += 0.18 if label_exact else 0.10
    score += 0.10 if unit_match else 0.03
    score += 0.12 if value_valid else 0.0
    score += 0.05 if adjacent else 0.02
    return round(min(score, 1.0), 3)


def overall_confidence(fields, missing_required, config=None):
    config = config or load_config()
    required = config["minimum_required_fields"]
    required_scores = [fields[name].confidence for name in required if name in fields]
    optional_scores = [value.confidence for name, value in fields.items() if name not in required]
    score = mean(required_scores) if required_scores else 0.0
    if optional_scores:
        score = score * 0.9 + mean(optional_scores) * 0.1
    score -= 0.18 * len(missing_required)
    return round(max(0.0, min(score, 1.0)), 3)


def confidence_band(score, config=None):
    config = config or load_config()
    if score >= config["auto_accept_threshold"]:
        return "high"
    if score >= config["manual_review_threshold"]:
        return "medium"
    if score >= config["reject_threshold"]:
        return "low"
    return "reject"
