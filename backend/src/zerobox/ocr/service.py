"""OCR processing module (FR-02)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import ocrmypdf

from zerobox.ocr.models import OcrResult

if TYPE_CHECKING:
    from zerobox.audit.service import AuditService
    from zerobox.config import OcrConfig
    from zerobox.intake.models import IntakeFile

logger = logging.getLogger(__name__)


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
