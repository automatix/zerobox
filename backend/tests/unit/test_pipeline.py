"""Tests for PipelineService."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from zerobox.classifier.models import Proposal
from zerobox.intake.models import IntakeFile
from zerobox.ocr.models import OcrResult
from zerobox.pipeline.service import PipelineService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_intake_file(name: str = "scan001.pdf") -> IntakeFile:
    return IntakeFile(
        path=Path(f"/inbox/{name}"),
        file_type=".pdf",
        size_bytes=1024,
        modified_at=datetime(2026, 1, 1),
    )


def _make_ocr_result(
    file: IntakeFile,
    *,
    success: bool = True,
    text: str = "Invoice #123",
    error: str | None = None,
) -> OcrResult:
    return OcrResult(
        source_path=file.path,
        output_path=file.path.with_suffix(".ocr.pdf"),
        text=text if success else "",
        language="eng",
        pages=1 if success else 0,
        success=success,
        error=error,
    )


def _make_proposal(file: IntakeFile, *, status: str = "pending") -> Proposal:
    return Proposal(
        id="p-1",
        original_path=file.path,
        original_name=file.path.name,
        proposed_name="invoice_2026.pdf",
        proposed_folder=Path("invoices"),
        confidence=0.95,
        matched_rule=None,
        status=status,
    )


def _make_pipeline(
    *,
    files: list[IntakeFile] | None = None,
    ocr_results: list[OcrResult] | None = None,
    proposals: list[Proposal] | None = None,
    batch_results: list[tuple[Proposal, Path | None]] | None = None,
    audit: MagicMock | None = MagicMock(),
) -> PipelineService:
    intake = MagicMock()
    intake.scan.return_value = files or []

    ocr = AsyncMock()
    ocr.process_batch.return_value = ocr_results or []

    classifier = AsyncMock()
    classifier.classify_batch.return_value = proposals or []

    filemanager = MagicMock()
    filemanager.execute_batch.return_value = batch_results or []

    return PipelineService(
        intake=intake,
        ocr=ocr,
        classifier=classifier,
        filemanager=filemanager,
        audit=audit,
    )


# ------------------------------------------------------------------
# run — happy path
# ------------------------------------------------------------------


class TestRunHappyPath:
    @pytest.mark.asyncio
    async def test_discovers_ocrs_classifies_and_returns_proposals(self) -> None:
        file = _make_intake_file()
        ocr_result = _make_ocr_result(file)
        proposal = _make_proposal(file)

        svc = _make_pipeline(
            files=[file],
            ocr_results=[ocr_result],
            proposals=[proposal],
        )

        result = await svc.run()

        assert result == [proposal]
        svc._intake.scan.assert_called_once()
        svc._ocr.process_batch.assert_called_once_with([file])
        svc._classifier.classify_batch.assert_called_once_with(
            [(ocr_result.text, file)]
        )

    @pytest.mark.asyncio
    async def test_empty_inbox_returns_empty_list(self) -> None:
        svc = _make_pipeline(files=[])

        result = await svc.run()

        assert result == []
        svc._ocr.process_batch.assert_not_called()
        svc._classifier.classify_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_filters_out_failed_ocr_results(self) -> None:
        good_file = _make_intake_file("good.pdf")
        bad_file = _make_intake_file("bad.pdf")
        good_ocr = _make_ocr_result(good_file, success=True)
        bad_ocr = _make_ocr_result(bad_file, success=False, error="corrupt")
        proposal = _make_proposal(good_file)

        svc = _make_pipeline(
            files=[good_file, bad_file],
            ocr_results=[good_ocr, bad_ocr],
            proposals=[proposal],
        )

        result = await svc.run()

        assert result == [proposal]
        # Only the successful file is passed to the classifier
        svc._classifier.classify_batch.assert_called_once_with(
            [(good_ocr.text, good_file)]
        )


# ------------------------------------------------------------------
# run — audit logging
# ------------------------------------------------------------------


class TestRunAuditLogging:
    @pytest.mark.asyncio
    async def test_logs_pipeline_started_and_completed(self) -> None:
        audit = MagicMock()
        file = _make_intake_file()
        ocr_result = _make_ocr_result(file)
        proposal = _make_proposal(file)

        svc = _make_pipeline(
            files=[file],
            ocr_results=[ocr_result],
            proposals=[proposal],
            audit=audit,
        )

        await svc.run()

        actions = [c.kwargs["action"] for c in audit.log.call_args_list]
        assert actions[0] == "pipeline_started"
        assert actions[-1] == "pipeline_completed"

    @pytest.mark.asyncio
    async def test_logs_completed_with_summary_details(self) -> None:
        audit = MagicMock()
        file = _make_intake_file()
        ocr_result = _make_ocr_result(file)
        proposal = _make_proposal(file)

        svc = _make_pipeline(
            files=[file],
            ocr_results=[ocr_result],
            proposals=[proposal],
            audit=audit,
        )

        await svc.run()

        completed_call = audit.log.call_args_list[-1]
        details = completed_call.kwargs["details"]
        assert details["files_found"] == 1
        assert details["ocr_succeeded"] == 1
        assert details["ocr_failed"] == 0
        assert details["proposals_generated"] == 1

    @pytest.mark.asyncio
    async def test_logs_ocr_failed_for_each_failure(self) -> None:
        audit = MagicMock()
        file = _make_intake_file()
        ocr_result = _make_ocr_result(file, success=False, error="corrupt")

        svc = _make_pipeline(
            files=[file],
            ocr_results=[ocr_result],
            audit=audit,
        )

        await svc.run()

        actions = [c.kwargs["action"] for c in audit.log.call_args_list]
        assert "ocr_failed" in actions

    @pytest.mark.asyncio
    async def test_empty_inbox_logs_completed_with_zero_files(self) -> None:
        audit = MagicMock()
        svc = _make_pipeline(files=[], audit=audit)

        await svc.run()

        completed_call = audit.log.call_args_list[-1]
        assert completed_call.kwargs["details"] == {"files_found": 0}


# ------------------------------------------------------------------
# run — without audit service
# ------------------------------------------------------------------


class TestRunWithoutAudit:
    @pytest.mark.asyncio
    async def test_works_without_audit_service(self) -> None:
        file = _make_intake_file()
        ocr_result = _make_ocr_result(file)
        proposal = _make_proposal(file)

        svc = _make_pipeline(
            files=[file],
            ocr_results=[ocr_result],
            proposals=[proposal],
            audit=None,
        )

        result = await svc.run()

        assert result == [proposal]


# ------------------------------------------------------------------
# execute_approved
# ------------------------------------------------------------------


class TestExecuteApproved:
    @pytest.mark.asyncio
    async def test_delegates_to_filemanager(self) -> None:
        file = _make_intake_file()
        proposal = _make_proposal(file, status="approved")
        target = Path("/archive/invoices/invoice_2026.pdf")
        batch_results = [(proposal, target)]

        svc = _make_pipeline(batch_results=batch_results)

        results = await svc.execute_approved([proposal])

        svc._filemanager.execute_batch.assert_called_once_with([proposal])
        assert results == batch_results

    @pytest.mark.asyncio
    async def test_logs_execution_started_and_completed(self) -> None:
        audit = MagicMock()
        file = _make_intake_file()
        proposal = _make_proposal(file, status="approved")
        target = Path("/archive/invoices/invoice_2026.pdf")

        svc = _make_pipeline(
            batch_results=[(proposal, target)],
            audit=audit,
        )

        await svc.execute_approved([proposal])

        actions = [c.kwargs["action"] for c in audit.log.call_args_list]
        assert "execution_started" in actions
        assert "execution_completed" in actions


# ------------------------------------------------------------------
# run_and_execute
# ------------------------------------------------------------------


class TestRunAndExecute:
    @pytest.mark.asyncio
    async def test_auto_approve_sets_status_to_approved(self) -> None:
        file = _make_intake_file()
        ocr_result = _make_ocr_result(file)
        proposal = _make_proposal(file, status="pending")
        target = Path("/archive/invoices/invoice_2026.pdf")

        svc = _make_pipeline(
            files=[file],
            ocr_results=[ocr_result],
            proposals=[proposal],
            batch_results=[(proposal, target)],
        )

        await svc.run_and_execute(auto_approve=True)

        assert proposal.status == "approved"
        svc._filemanager.execute_batch.assert_called_once_with([proposal])

    @pytest.mark.asyncio
    async def test_without_auto_approve_proposals_stay_pending(self) -> None:
        file = _make_intake_file()
        ocr_result = _make_ocr_result(file)
        proposal = _make_proposal(file, status="pending")

        svc = _make_pipeline(
            files=[file],
            ocr_results=[ocr_result],
            proposals=[proposal],
            batch_results=[(proposal, None)],
        )

        results = await svc.run_and_execute(auto_approve=False)

        assert proposal.status == "pending"
        # filemanager still called, but it skips non-approved
        svc._filemanager.execute_batch.assert_called_once_with([proposal])
        assert results == [(proposal, None)]


# ------------------------------------------------------------------
# Graceful OCR failure handling
# ------------------------------------------------------------------


class TestOcrFailureGraceful:
    @pytest.mark.asyncio
    async def test_partial_ocr_failure_continues_with_rest(self) -> None:
        f1 = _make_intake_file("a.pdf")
        f2 = _make_intake_file("b.pdf")
        f3 = _make_intake_file("c.pdf")

        ocr_results = [
            _make_ocr_result(f1, success=True, text="text-a"),
            _make_ocr_result(f2, success=False, error="corrupt"),
            _make_ocr_result(f3, success=True, text="text-c"),
        ]

        p1 = _make_proposal(f1)
        p3 = _make_proposal(f3)

        svc = _make_pipeline(
            files=[f1, f2, f3],
            ocr_results=ocr_results,
            proposals=[p1, p3],
        )

        result = await svc.run()

        assert result == [p1, p3]
        # Only successful OCR results are classified
        svc._classifier.classify_batch.assert_called_once_with(
            [("text-a", f1), ("text-c", f3)]
        )
