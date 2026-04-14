"""Scanner service — file ingestion from a configurable input folder (FR-01)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from zerobox.scanner.models import ScannedFile

if TYPE_CHECKING:
    from zerobox.audit.service import AuditService
    from zerobox.config import ScannerConfig


class ScannerService:
    """Reads supported files from the configured input folder."""

    def __init__(
        self,
        config: ScannerConfig,
        audit: AuditService | None = None,
    ) -> None:
        self._config = config
        self._audit = audit

    def scan(self) -> list[ScannedFile]:
        """Scan the input folder and return a list of supported files.

        Only top-level files are considered; subdirectories are skipped.
        Results are sorted by filename for deterministic output.

        Raises:
            FileNotFoundError: If the configured input folder does not exist.
        """
        input_folder = self._config.input_folder

        if not input_folder.exists():
            raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

        allowed = {ext.lower() for ext in self._config.file_types}

        results: list[ScannedFile] = []
        for entry in input_folder.iterdir():
            if not entry.is_file():
                continue

            if entry.suffix.lower() not in allowed:
                continue

            stat = entry.stat()
            scanned = ScannedFile(
                path=entry.resolve(),
                file_type=entry.suffix.lower(),
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )
            results.append(scanned)

            if self._audit is not None:
                self._audit.log(
                    action="scanned",
                    source=str(scanned.path),
                    details={"size_bytes": scanned.size_bytes, "file_type": scanned.file_type},
                )

        results.sort(key=lambda f: f.path.name)
        return results
