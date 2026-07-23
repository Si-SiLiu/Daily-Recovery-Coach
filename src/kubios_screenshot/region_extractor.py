from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .templates import validate_region


def region_pixels(image_size, region):
    validate_region(region)
    width, height = image_size
    left = round(float(region["x"]) * width)
    top = round(float(region["y"]) * height)
    right = round((float(region["x"]) + float(region["width"])) * width)
    bottom = round((float(region["y"]) + float(region["height"])) * height)
    return left, top, max(right, left + 1), max(bottom, top + 1)


def extract_region(image_or_path, region):
    owns_image = not isinstance(image_or_path, Image.Image)
    image = Image.open(image_or_path) if owns_image else image_or_path
    try:
        return image.crop(region_pixels(image.size, region)).copy()
    finally:
        if owns_image:
            image.close()


def preprocessing_candidates(crop):
    original = crop.convert("RGB")
    gray = ImageOps.grayscale(original)
    contrast = ImageEnhance.Contrast(gray).enhance(2.0)
    threshold = gray.point(lambda value: 255 if value > 145 else 0)
    return {
        "original": original,
        "grayscale": gray,
        "high_contrast": contrast,
        "adaptive_binary": threshold,
        "scale_2x": gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS),
        "scale_3x": gray.resize((gray.width * 3, gray.height * 3), Image.Resampling.LANCZOS),
    }


def render_region_overlay(image_or_path, regions, active_field=None):
    from PIL import ImageDraw
    owns_image = not isinstance(image_or_path, Image.Image)
    image = Image.open(image_or_path).convert("RGB") if owns_image else image_or_path.convert("RGB")
    draw = ImageDraw.Draw(image)
    for name, region in regions.items():
        box = region_pixels(image.size, region)
        active = name == active_field
        draw.rectangle(box, outline=(255, 70, 40) if active else (70, 150, 255), width=8 if active else 3)
    return image
