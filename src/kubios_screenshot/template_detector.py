from dataclasses import asdict, dataclass

from .templates import list_templates


@dataclass(frozen=True)
class TemplateDetection:
    template_id: str | None
    confidence: float
    requires_manual_selection: bool
    matched_anchors: list[str]
    reasons: list[str]

    def to_dict(self):
        return asdict(self)


def _normalize(value):
    return " ".join(str(value).lower().replace("_", " ").split())


def _block_text(block):
    return block.text if hasattr(block, "text") else block.get("text", "")


def _aspect_score(width, height, expected_range):
    if not width or not height:
        return 0.0
    ratio = width / height
    low, high = map(float, expected_range)
    if low <= ratio <= high:
        return 1.0
    distance = min(abs(ratio - low), abs(ratio - high))
    return max(0.0, 1.0 - distance / max(high, 0.01))


def detect_template(image_size, text_blocks, config=None):
    templates = list_templates(config)
    text = "\n".join(_normalize(_block_text(block)) for block in text_blocks)
    scored = []
    for template in templates:
        anchors = [_normalize(value) for value in template["anchor_labels"]]
        matched = [anchor for anchor in anchors if anchor in text]
        anchor_score = len(matched) / max(len(anchors), 1)
        aspect = _aspect_score(image_size.get("width"), image_size.get("height"), template["expected_image_aspect_ratio"])
        layout_score = 1.0 if image_size.get("height", 0) > image_size.get("width", 0) else 0.0
        score = round(anchor_score * 0.6 + aspect * 0.3 + layout_score * 0.1, 3)
        scored.append((score, template, matched))
    if not scored:
        return TemplateDetection(None, 0.0, True, [], ["no_templates"])
    score, template, matched = max(scored, key=lambda item: item[0])
    threshold = float((config or {"detection_threshold": 0.78}).get("detection_threshold", 0.78))
    reasons = []
    if score < threshold:
        reasons.append("low_template_confidence")
    if not template.get("auto_detection_enabled", False):
        reasons.append("real_calibration_pending")
    requires_manual = bool(reasons)
    return TemplateDetection(
        template["template_id"] if score >= threshold else None,
        score, requires_manual, matched, reasons,
    )
