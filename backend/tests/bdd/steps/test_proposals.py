"""Step definitions for proposals.feature."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from zerobox.app import create_app

scenarios("../features/proposals.feature")


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def proposal_context(tmp_inbox, tmp_output, tmp_profiles, tmp_path):
    """Mutable dict to pass state between steps, with a test app."""
    import os

    # Point config to tmp dirs so create_app() works without real paths
    os.environ["ZEROBOX_INTAKE__INPUT_FOLDER"] = str(tmp_inbox)
    os.environ["ZEROBOX_FILEMANAGER__OUTPUT_ROOT"] = str(tmp_output)
    os.environ["ZEROBOX_PROFILES_DIR"] = str(tmp_profiles)
    os.environ["ZEROBOX_AUDIT__DB_PATH"] = str(tmp_path / "audit.db")

    app = create_app()
    client = TestClient(app)

    ctx = {
        "app": app,
        "client": client,
        "tmp_inbox": tmp_inbox,
        "tmp_output": tmp_output,
    }

    yield ctx

    # Clean up env vars
    for key in [
        "ZEROBOX_INTAKE__INPUT_FOLDER",
        "ZEROBOX_FILEMANAGER__OUTPUT_ROOT",
        "ZEROBOX_PROFILES_DIR",
        "ZEROBOX_AUDIT__DB_PATH",
    ]:
        os.environ.pop(key, None)


def _make_proposal_dict(
    proposal_id: str = "test-001",
    *,
    status: str = "pending",
    original_path: str = "/inbox/scan001.pdf",
    proposed_name: str = "classified_doc.pdf",
    proposed_folder: str = "Documents/Classified",
) -> dict:
    return {
        "id": proposal_id,
        "original_path": original_path,
        "original_name": Path(original_path).name,
        "proposed_name": proposed_name,
        "proposed_folder": proposed_folder,
        "confidence": 0.92,
        "matched_rule": None,
        "status": status,
    }


# ------------------------------------------------------------------
# Given
# ------------------------------------------------------------------


@given("there is a pending proposal", target_fixture="proposal_context")
def pending_proposal(proposal_context):
    app = proposal_context["app"]
    proposal = _make_proposal_dict("test-001", status="pending")
    app.state.proposals["test-001"] = proposal
    proposal_context["proposal_id"] = "test-001"
    return proposal_context


@given(
    parsers.parse("there are {count:d} approved proposals with existing source files"),
    target_fixture="proposal_context",
)
def approved_proposals_with_files(count, proposal_context):
    app = proposal_context["app"]
    tmp_inbox = proposal_context["tmp_inbox"]
    proposal_context["proposal_ids"] = []

    for i in range(count):
        pid = f"test-{i + 1:03d}"
        source_file = tmp_inbox / f"scan{i + 1:03d}.pdf"
        source_file.write_bytes(b"%PDF-1.4 fake content")
        proposal = _make_proposal_dict(
            pid,
            status="approved",
            original_path=str(source_file),
            proposed_name=f"filed_{i + 1:03d}.pdf",
            proposed_folder="Archive",
        )
        app.state.proposals[pid] = proposal
        proposal_context["proposal_ids"].append(pid)

    return proposal_context


# ------------------------------------------------------------------
# When
# ------------------------------------------------------------------


@when("I approve the proposal", target_fixture="response")
def approve_proposal(proposal_context):
    client = proposal_context["client"]
    pid = proposal_context["proposal_id"]
    resp = client.patch(f"/proposals/{pid}", json={"status": "approved"})
    assert resp.status_code == 200
    return resp.json()


@when("I reject the proposal", target_fixture="response")
def reject_proposal(proposal_context):
    client = proposal_context["client"]
    pid = proposal_context["proposal_id"]
    resp = client.patch(f"/proposals/{pid}", json={"status": "rejected"})
    assert resp.status_code == 200
    return resp.json()


@when(
    parsers.parse('I correct the proposal with name "{name}" and folder "{folder}"'),
    target_fixture="response",
)
def correct_proposal(proposal_context, name, folder):
    client = proposal_context["client"]
    pid = proposal_context["proposal_id"]
    resp = client.patch(
        f"/proposals/{pid}",
        json={
            "status": "corrected",
            "corrected_name": name,
            "corrected_folder": folder,
        },
    )
    assert resp.status_code == 200
    return resp.json()


@when("I execute the approved proposals", target_fixture="execute_response")
def execute_proposals(proposal_context):
    client = proposal_context["client"]
    resp = client.post("/proposals/execute")
    assert resp.status_code == 200
    proposal_context["execute_response"] = resp.json()
    return resp.json()


# ------------------------------------------------------------------
# Then
# ------------------------------------------------------------------


@then(parsers.parse('the proposal status should be "{status}"'))
def check_status(response, status):
    assert response["status"] == status


@then(parsers.parse('the proposed name should be "{name}"'))
def check_proposed_name(response, name):
    assert response["proposed_name"] == name


@then(parsers.parse('the proposed folder should be "{folder}"'))
def check_proposed_folder(response, folder):
    assert response["proposed_folder"] == folder


@then("each file should be moved to its target location")
def check_files_moved(execute_response, proposal_context):
    tmp_output = proposal_context["tmp_output"]
    for item in execute_response:
        assert item["target_path"] is not None
        target = Path(item["target_path"])
        assert target.exists()


@then("the moves should be logged in the audit trail")
def check_audit_logged(proposal_context):
    client = proposal_context["client"]
    resp = client.get("/audit/log", params={"action": "file_moved"})
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 1
