"""Pipeline service — orchestrates the full processing workflow (FR-01)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from zerobox.audit.service import AuditService
    from zerobox.classifier.models import Proposal
    from zerobox.classifier.service import ClassifierService
    from zerobox.filemanager.service import FileManagerService
    from zerobox.intake.service import IntakeService
    from zerobox.ocr.service import OcrService

logger = logging.getLogger(__name__)


class PipelineService:
    """Orchestrates the full scan-processing pipeline.

    Stages: Intake -> OCR -> Classifier -> (user review) -> FileManager.
    Every orchestration step is audit-logged for complete traceability.
    """

    def __init__(
        self,
        intake: IntakeService,
        ocr: OcrService,
        classifier: ClassifierService,
        filemanager: FileManagerService,
        audit: AuditService | None = None,
    ) -> None:
        self._intake = intake
        self._ocr = ocr
        self._classifier = classifier
        self._filemanager = filemanager
        self._audit = audit

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> list[Proposal]:
        """Execute the pipeline up to the review point.

        Discovers files, runs OCR, classifies documents, and returns
        a list of pending proposals for user review.
        """
        self._log("pipeline_started", source="pipeline")

        # 1. Discover files
        files = self._intake.scan()

        if not files:
            self._log(
                "pipeline_completed",
                source="pipeline",
                details={"files_found": 0},
            )
            return []

        # 2. OCR all files
        ocr_results = await self._ocr.process_batch(files)

        # 3. Separate successes from failures
        source_to_file = {str(f.path): f for f in files}
        failed_count = 0
        text_file_pairs: list[tuple[str, object]] = []

        for result in ocr_results:
            if not result.success:
                failed_count += 1
                self._log(
                    "ocr_failed",
                    source=str(result.source_path),
                    details={"error": result.error},
                )
                continue

            intake_file = source_to_file.get(str(result.source_path))
            if intake_file is not None:
                text_file_pairs.append((result.text, intake_file))

        # 4. Classify
        proposals = await self._classifier.classify_batch(text_file_pairs)

        # 5. Log completion summary
        self._log(
            "pipeline_completed",
            source="pipeline",
            details={
                "files_found": len(files),
                "ocr_succeeded": len(text_file_pairs),
                "ocr_failed": failed_count,
                "proposals_generated": len(proposals),
            },
        )

        return proposals

    async def execute_approved(
        self,
        proposals: list[Proposal],
    ) -> list[tuple[Proposal, Path | None]]:
        """Execute file operations for approved proposals.

        Args:
            proposals: List of proposals (only approved ones will be processed).

        Returns:
            List of (proposal, target_path_or_none) tuples.
        """
        approved_count = sum(1 for p in proposals if p.status == "approved")
        self._log(
            "execution_started",
            source="pipeline",
            details={"approved_count": approved_count},
        )

        results = self._filemanager.execute_batch(proposals)

        succeeded = sum(1 for _, path in results if path is not None)
        self._log(
            "execution_completed",
            source="pipeline",
            details={"succeeded": succeeded, "total": len(results)},
        )

        return results

    async def run_and_execute(
        self,
        auto_approve: bool = False,
    ) -> list[tuple[Proposal, Path | None]]:
        """Run the full pipeline and optionally auto-approve all proposals.

        Args:
            auto_approve: If ``True``, set all proposals to ``"approved"``
                before executing file operations.

        Returns:
            List of (proposal, target_path_or_none) tuples.
        """
        proposals = await self.run()

        if auto_approve:
            for proposal in proposals:
                proposal.status = "approved"

        return await self.execute_approved(proposals)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(
        self,
        action: str,
        source: str,
        target: str | None = None,
        rule_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Log an action to audit if an audit service is available."""
        if self._audit is not None:
            self._audit.log(
                action=action,
                source=source,
                target=target,
                rule_id=rule_id,
                details=details,
            )
