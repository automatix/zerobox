"""Step definitions for pipeline.feature."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from zerobox.pipeline.service import PipelineService

scenarios("../features/pipeline.feature")


# ------------------------------------------------------------------
# Shared state
# ------------------------------------------------------------------


@pytest.fixture()
def pipeline_context():
    """Mutable dict to pass state between steps."""
    return {}


# ------------------------------------------------------------------
# Given
# ------------------------------------------------------------------


@given(
    parsers.parse("the inbox contains {count:d} PDF files"),
    target_fixture="pipeline_context",
)
def inbox_with_pdfs(
    count,
    tmp_inbox,
    pipeline_context,
    intake_service,
    mock_ocr_service,
    classifier_service,
    filemanager_service,
    audit_service,
):
    for i in range(count):
        pdf = tmp_inbox / f"scan{i + 1:03d}.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake content")
    pipeline = PipelineService(
        intake=intake_service,
        ocr=mock_ocr_service,
        classifier=classifier_service,
        filemanager=filemanager_service,
        audit=audit_service,
    )
    pipeline_context["pipeline"] = pipeline
    pipeline_context["inbox"] = tmp_inbox
    return pipeline_context


@given("the inbox is empty", target_fixture="pipeline_context")
def inbox_empty(
    tmp_inbox,
    pipeline_context,
    intake_service,
    mock_ocr_service,
    classifier_service,
    filemanager_service,
    audit_service,
):
    pipeline = PipelineService(
        intake=intake_service,
        ocr=mock_ocr_service,
        classifier=classifier_service,
        filemanager=filemanager_service,
        audit=audit_service,
    )
    pipeline_context["pipeline"] = pipeline
    pipeline_context["inbox"] = tmp_inbox
    return pipeline_context


@given(
    parsers.parse("the inbox contains {pdf_count:d} PDF file and {docx_count:d} DOCX file"),
    target_fixture="pipeline_context",
)
def inbox_mixed_types(
    pdf_count,
    docx_count,
    tmp_inbox,
    pipeline_context,
    intake_service,
    mock_ocr_service,
    classifier_service,
    filemanager_service,
    audit_service,
):
    for i in range(pdf_count):
        pdf = tmp_inbox / f"scan{i + 1:03d}.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake content")
    for i in range(docx_count):
        docx = tmp_inbox / f"doc{i + 1:03d}.docx"
        docx.write_bytes(b"PK fake docx content")
    pipeline = PipelineService(
        intake=intake_service,
        ocr=mock_ocr_service,
        classifier=classifier_service,
        filemanager=filemanager_service,
        audit=audit_service,
    )
    pipeline_context["pipeline"] = pipeline
    pipeline_context["inbox"] = tmp_inbox
    pipeline_context["docx_count"] = docx_count
    return pipeline_context


# ------------------------------------------------------------------
# When
# ------------------------------------------------------------------


@when("I run the pipeline", target_fixture="proposals")
def run_pipeline(pipeline_context):
    import asyncio

    pipeline = pipeline_context["pipeline"]
    proposals = asyncio.run(pipeline.run())
    pipeline_context["proposals"] = proposals
    return proposals


# ------------------------------------------------------------------
# Then
# ------------------------------------------------------------------


@then(parsers.parse("I should receive {count:d} proposals"))
def check_proposal_count(proposals, count):
    assert len(proposals) == count


@then(parsers.parse('each proposal should have status "{status}"'))
def check_proposal_status(proposals, status):
    for p in proposals:
        assert p.status == status


@then("each proposal should have a proposed name")
def check_proposed_name(proposals):
    for p in proposals:
        assert p.proposed_name
        assert len(p.proposed_name) > 0


@then("each proposal should have a proposed folder")
def check_proposed_folder(proposals):
    for p in proposals:
        assert p.proposed_folder
        assert str(p.proposed_folder) != ""


@then("the unsupported file should be ignored")
def check_unsupported_ignored(pipeline_context):
    inbox = pipeline_context["inbox"]
    docx_files = list(inbox.glob("*.docx"))
    assert len(docx_files) == pipeline_context["docx_count"]
