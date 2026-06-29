from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def extract_text(image_path: Path, mode: str) -> str | None:
    if mode == "none":
        return None
    if mode == "tesseract":
        return extract_tesseract(image_path)
    raise ValueError(f"Unknown OCR mode: {mode}")


def extract_tesseract(image_path: Path) -> str | None:
    if shutil.which("tesseract") is None:
        return None
    cmd = ["tesseract", str(image_path), "stdout", "--psm", "6"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    text = "\n".join(line.strip() for line in result.stdout.splitlines() if line.strip())
    return text or None

