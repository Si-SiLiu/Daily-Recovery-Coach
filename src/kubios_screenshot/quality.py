from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class ImageQualityResult:
    acceptable: bool
    warnings: list[str]
    width: int
    height: int
    aspect_ratio: float

    def to_dict(self):
        return asdict(self)


def check_image_quality(path, minimum_width=600, minimum_height=1000):
    with Image.open(path) as image:
        width, height = image.size
        fmt = image.format
    warnings = []
    if width < minimum_width or height < minimum_height:
        warnings.append("resolution_too_low")
    if width >= height:
        warnings.append("rotation_or_orientation_wrong")
    ratio = width / height if height else 0.0
    # Kubios exports may be either full-height phone screenshots or sanitized
    # portrait crops. Template anchors still gate recognition after this check.
    if ratio < 0.35 or ratio > 0.90:
        warnings.append("unexpected_aspect_ratio")
    if fmt == "JPEG" and Path(path).stat().st_size < width * height * 0.04:
        warnings.append("strong_compression")
    fatal = {"resolution_too_low", "rotation_or_orientation_wrong", "unexpected_aspect_ratio"}
    return ImageQualityResult(not bool(fatal.intersection(warnings)), warnings, width, height, round(ratio, 4))
