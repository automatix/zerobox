"""Step definitions for audit.feature."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from zerobox.audit.service import AuditService
from zerobox.classifier.models import Proposal
from zerobox.config import FileManagerConfig
from zerobox.filemanager.service import FileManagerService

scenarios("../features/audit.feature")


# ------------------------------------------------------------------
# Shared state
# ------------------------------------------------------------------


@pytest.fixture()
def audit_context():
    """Mutable dict to pass state between steps."""
    return {}


# ------------------------------------------------------------------
# Given
# ------------------------------------------------------------------


@given("I run a pipeline with files", target_fixture="audit_context")
def run_pipeline_with_files(audit_service, audit_context):
    audit_service.log(action="pipeline_started", source="pipeline")
    audit_service.log(
        action="pipeline_completed",
        source="pipeline",
        details={"files_found": 2, "proposals_generated": 2},
    )
    audit_context["audit"] = audit_service
    return audit_context


@given("a file has been moved by the FileManager", target_fixture="audit_context")
def file_moved_by_filemanager(audit_service, tmp_inbox, tmp_output, audit_context):
    # Create a real source file
    source = tmp_inbox / "invoice.pdf"
    source.write_bytes(b"%PDF-1.4 fake content")

    config = FileManagerConfig(output_root=tmp_output, conflict_strategy="rename")
    fm = FileManagerService(config, audit_service)

    proposal = Proposal(
        id="move-test-001",
        original_path=source,
        original_name="invoice.pdf",
        proposed_name="filed_invoice.pdf",
        proposed_folder=Path("Archive"),
        confidence=0.95,
        matched_rule=None,
        status="approved",
    )

    fm.execute(proposal)

    audit_context["audit"] = audit_service
    audit_context["source_path"] = str(source)
    audit_context["target_folder"] = "Archive"
    return audit_context


@given("multiple audit entries exist", target_fixture="audit_context")
def multiple_entries(audit_service, audit_context):
    audit_service.log(action="pipeline_started", source="pipeline")
    audit_service.log(action="classified", source="/inbox/doc1.pdf")
    audit_service.log(action="classified", source="/inbox/doc2.pdf")
    audit_service.log(action="file_moved", source="/inbox/doc1.pdf", target="/archive/doc1.pdf")
    audit_context["audit"] = audit_service
    return audit_context


@given(parsers.parse("{count:d} audit entries exist"), target_fixture="audit_context")
def n_entries(count, audit_service, audit_context):
    for i in range(count):
        audit_service.log(action=f"action_{i}", source=f"source_{i}")
    audit_context["audit"] = audit_service
    return audit_context


# ------------------------------------------------------------------
# When
# ------------------------------------------------------------------


@when(
    parsers.parse('I query the audit log for action "{action}"'),
    target_fixture="query_results",
)
def query_by_action(action, audit_context):
    audit = audit_context["audit"]
    return audit.query(action=action)


@when(
    parsers.parse('I query the audit log filtered by action "{action}"'),
    target_fixture="query_results",
)
def query_filtered_by_action(action, audit_context):
    audit = audit_context["audit"]
    return audit.query(action=action)


@when(
    parsers.parse("I query the audit log with limit {limit:d}"),
    target_fixture="query_results",
)
def query_with_limit(limit, audit_context):
    audit = audit_context["audit"]
    return audit.query(limit=limit)


# ------------------------------------------------------------------
# Then
# ------------------------------------------------------------------


@then(parsers.parse("I should find at least {count:d} entry"))
def check_min_entries(query_results, count):
    assert len(query_results) >= count


@then("I should find the source and target paths in the entry")
def check_source_target(query_results, audit_context):
    assert len(query_results) >= 1
    entry = query_results[0]
    assert entry.source is not None
    assert entry.target is not None
    assert audit_context["source_path"] in entry.source
    assert audit_context["target_folder"] in entry.target


@then(parsers.parse('only entries with action "{action}" should be returned'))
def check_filtered_action(query_results, action):
    assert len(query_results) > 0
    for entry in query_results:
        assert entry.action == action


@then(parsers.parse("I should receive at most {limit:d} entries"))
def check_limit(query_results, limit):
    assert len(query_results) <= limit
