"""OCR data models (FR-02)."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class OcrResult:
    source_path: Path
    output_path: Path
    text: str
    language: str
    pages: int
    success: bool
    error: str | None = None
