"""OCR processing module (FR-02)."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import ocrmypdf

from zerobox.ocr.models import OcrResult

if TYPE_CHECKING:
    from zerobox.audit.service import AuditService
    from zerobox.config import OcrConfig
    from zerobox.intake.models import IntakeFile

logger = logging.getLogger(__name__)


def _resolve_app_resources_dir() -> Path | None:
    """Return the app's resources/ directory (next to the executable in production)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "resources"
    return None


def _find_tesseract(config_path: Path | None) -> Path | None:
    """Resolve Tesseract executable: explicit config > portable > system PATH."""
    if config_path and config_path.exists():
        return config_path

    res_dir = _resolve_app_resources_dir()
    if res_dir:
        portable = res_dir / "tesseract" / "tesseract.exe"
        if portable.exists():
            return portable

    system = shutil.which("tesseract")
    if system:
        return Path(system)

    return None


def _find_ghostscript(config_path: Path | None) -> Path | None:
    """Resolve Ghostscript executable: explicit config > portable > system PATH."""
    if config_path and config_path.exists():
        return config_path

    res_dir = _resolve_app_resources_dir()
    if res_dir:
        portable = res_dir / "ghostscript" / "bin" / "gswin64c.exe"
        if portable.exists():
            return portable

    system = shutil.which("gswin64c")
    if system:
        return Path(system)

    return None


class OcrService:
    """Processes scanned files through ocrmypdf to produce searchable PDFs."""

    def __init__(
        self,
        config: OcrConfig,
        output_dir: Path,
        audit: AuditService | None = None,
    ) -> None:
        self._config = config
        self._output_dir = output_dir
        self._audit = audit
        self._configure_paths()

    def _configure_paths(self) -> None:
        """Set environment variables for ocrmypdf to find Tesseract and Ghostscript."""
        tesseract = _find_tesseract(self._config.tesseract_path)
        if tesseract:
            os.environ["TESSERACT_CMD"] = str(tesseract)
            logger.info("Tesseract path: %s", tesseract)

        ghostscript = _find_ghostscript(self._config.ghostscript_path)
        if ghostscript:
            # Ghostscript: add its parent directory to PATH so ocrmypdf can find it
            gs_dir = str(ghostscript.parent)
            if gs_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = gs_dir + os.pathsep + os.environ.get("PATH", "")
            logger.info("Ghostscript path: %s", ghostscript)

    def _run_ocr(self, input_path: Path, output_path: Path, sidecar_path: Path) -> int:
        """Run ocrmypdf synchronously and return the exit code."""
        return ocrmypdf.ocr(
            input_file=input_path,
            output_file=output_path,
            language=self._config.language,
            deskew=self._config.deskew,
            optimize=self._config.optimize,
            sidecar=sidecar_path,
        )

    async def process(self, file: IntakeFile) -> OcrResult:
        """Run OCR on a single scanned file and return the result."""
        self._output_dir.mkdir(parents=True, exist_ok=True)

        output_path = self._output_dir / (file.path.stem + ".pdf")
        sidecar_path = self._output_dir / (file.path.stem + ".txt")

        try:
            await asyncio.to_thread(self._run_ocr, file.path, output_path, sidecar_path)

            text = ""
            if sidecar_path.exists():
                text = sidecar_path.read_text(encoding="utf-8")

            # Count pages via a simple heuristic: read sidecar form-feed characters
            # or default to 1 if we cannot determine the count.
            pages = max(1, text.count("\f") + 1) if text else 1

            result = OcrResult(
                source_path=file.path,
                output_path=output_path,
                text=text,
                language=self._config.language,
                pages=pages,
                success=True,
            )

            if self._audit is not None:
                self._audit.log(
                    action="ocr_processed",
                    source=str(file.path),
                    target=str(output_path),
                    details={"language": self._config.language, "pages": pages},
                )

            logger.info("OCR completed: %s -> %s", file.path, output_path)
            return result

        except Exception as exc:
            logger.error("OCR failed for %s: %s", file.path, exc)
            return OcrResult(
                source_path=file.path,
                output_path=output_path,
                text="",
                language=self._config.language,
                pages=0,
                success=False,
                error=str(exc),
            )

    async def process_batch(self, files: list[IntakeFile]) -> list[OcrResult]:
        """Process multiple scanned files sequentially."""
        results: list[OcrResult] = []
        for file in files:
            result = await self.process(file)
            results.append(result)
        return results
