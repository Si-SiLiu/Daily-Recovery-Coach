import json
import platform
import subprocess
from pathlib import Path

from PIL import Image

from .models import OCRResult, TextBlock


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_HELPER = BASE_DIR / "bin" / "kubios-vision-ocr"


class LocalOCRError(RuntimeError):
    pass


class VisionOCRAdapter:
    """Thin local adapter around macOS Vision; it has no network code path."""

    engine = "macos_vision"

    def __init__(self, helper_path=DEFAULT_HELPER, timeout=90):
        self.helper_path = Path(helper_path)
        self.timeout = timeout

    def readiness(self):
        return {
            "ready": platform.system() == "Darwin" and self.helper_path.is_file(),
            "engine": self.engine,
            "helper_present": self.helper_path.is_file(),
            "network_required": False,
        }

    def recognize(self, image_path):
        image_path = Path(image_path)
        if not self.readiness()["ready"]:
            raise LocalOCRError("local_ocr_unavailable")
        if not image_path.is_file():
            raise LocalOCRError("image_not_found")
        try:
            with Image.open(image_path) as image:
                fallback_size = {"width": image.width, "height": image.height}
            completed = subprocess.run(
                [str(self.helper_path), str(image_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
            )
        except subprocess.TimeoutExpired as exc:
            raise LocalOCRError("local_ocr_timeout") from exc
        except OSError as exc:
            raise LocalOCRError("local_ocr_launch_failed") from exc
        if completed.returncode != 0:
            raise LocalOCRError("local_ocr_failed")
        try:
            payload = json.loads(completed.stdout)
            blocks = [
                TextBlock(
                    text=str(item["text"])[:500],
                    confidence=max(0.0, min(float(item["confidence"]), 1.0)),
                    bounding_box={key: float(value) for key, value in item.get("bounding_box", {}).items()},
                    candidates=[
                        {"text": str(candidate.get("text", ""))[:200],
                         "confidence": max(0.0, min(float(candidate.get("confidence", 0)), 1.0))}
                        for candidate in item.get("candidates", [])[:3]
                    ],
                )
                for item in payload.get("text_blocks", [])
                if str(item.get("text", "")).strip()
            ]
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise LocalOCRError("local_ocr_invalid_response") from exc
        raw_text = "\n".join(block.text for block in blocks)
        return OCRResult(
            engine=self.engine,
            engine_version=str(payload.get("engine_version", "unknown")),
            image_size=payload.get("image_size") or fallback_size,
            text_blocks=blocks,
            raw_text=raw_text,
            processing_warnings=list(payload.get("processing_warnings", [])),
        )
