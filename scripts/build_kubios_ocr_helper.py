"""Build the local macOS Vision OCR helper without downloading dependencies."""

import platform
import shutil
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE = BASE_DIR / "scripts" / "kubios_vision_ocr.swift"
OUTPUT = BASE_DIR / "bin" / "kubios-vision-ocr"


def build():
    if platform.system() != "Darwin":
        raise RuntimeError("macOS Vision OCR is available only on macOS.")
    compiler = shutil.which("swiftc") or shutil.which("xcrun")
    if not compiler:
        raise RuntimeError("Swift compiler is unavailable; install Apple Command Line Tools.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    command = [compiler, str(SOURCE), "-o", str(OUTPUT)]
    if Path(compiler).name == "xcrun":
        command = [compiler, "swiftc", str(SOURCE), "-o", str(OUTPUT)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError("Local Vision OCR helper compilation failed.")
    OUTPUT.chmod(0o755)
    return OUTPUT


if __name__ == "__main__":
    print(build())
