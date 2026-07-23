import io
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError

from .config import load_config


class UnsupportedImageError(ValueError):
    pass


def validate_image_bytes(data, filename, config=None):
    config = config or load_config()
    suffix = Path(filename or "").suffix.lower()
    if suffix not in config.get("supported_extensions", []):
        raise UnsupportedImageError("unsupported_image_format")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnsupportedImageError("invalid_image") from exc
    return suffix


def preprocess_image(source_path, output_path, config=None):
    config = config or load_config()
    options = config["image_preprocessing_defaults"]
    try:
        with Image.open(source_path) as source:
            image = ImageOps.exif_transpose(source).convert("L")
            if options.get("autocontrast", True):
                image = ImageOps.autocontrast(image)
            image = ImageEnhance.Contrast(image).enhance(1.25)
            scale = float(options.get("scale", 2.0))
            if scale != 1:
                image = image.resize(
                    (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                    Image.Resampling.LANCZOS,
                )
            size = int(options.get("median_filter_size", 3))
            if size >= 3 and size % 2 == 1:
                image = image.filter(ImageFilter.MedianFilter(size=size))
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, format="PNG", optimize=True)
            return {"width": image.width, "height": image.height, "mode": image.mode}
    except (UnidentifiedImageError, OSError) as exc:
        raise UnsupportedImageError("image_preprocessing_failed") from exc
