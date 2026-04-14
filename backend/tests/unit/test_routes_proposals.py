"""Tests for proposal API routes (#17)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from zerobox.api.routes.proposals import _proposal_to_dict
from zerobox.app import create_app
from zerobox.classifier.models import Proposal
from zerobox.filemanager.service import FileManagerService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _sample_proposal(
    *,
    id: str = "p-1",
    status: str = "pending",
    proposed_name: str = "invoice_2024.pdf",
    proposed_folder: str = "invoices",
) -> Proposal:
    return Proposal(
        id=id,
        original_path=Path("/tmp/inbox/scan001.pdf"),
        original_name="scan001.pdf",
        proposed_name=proposed_name,
        proposed_folder=Path(proposed_folder),
        confidence=0.92,
        matched_rule="rule-1",
        status=status,
    )


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def app():
    application = create_app()
    return application


@pytest.fixture()
def populated_app(app):
    """App with two pre-populated proposals."""
    p1 = _sample_proposal(id="p-1", status="pending")
    p2 = _sample_proposal(id="p-2", status="approved", proposed_name="receipt.pdf")
    app.state.proposals = {
        "p-1": _proposal_to_dict(p1),
        "p-2": _proposal_to_dict(p2),
    }
    return app


@pytest.fixture()
def client(populated_app):
    mock_fm = MagicMock(spec=FileManagerService)
    mock_fm.execute_batch.return_value = []

    from zerobox.api.dependencies import get_filemanager

    populated_app.dependency_overrides[get_filemanager] = lambda: mock_fm
    return TestClient(populated_app)


@pytest.fixture()
def mock_filemanager(populated_app):
    mock_fm = MagicMock(spec=FileManagerService)
    return mock_fm


# ------------------------------------------------------------------
# GET /proposals
# ------------------------------------------------------------------


class TestListProposals:
    def test_returns_all_proposals(self, client: TestClient) -> None:
        resp = client.get("/proposals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        ids = {p["id"] for p in data}
        assert ids == {"p-1", "p-2"}

    def test_filter_by_status(self, client: TestClient) -> None:
        resp = client.get("/proposals", params={"status": "approved"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "p-2"
        assert data[0]["status"] == "approved"

    def test_filter_returns_empty_for_no_match(self, client: TestClient) -> None:
        resp = client.get("/proposals", params={"status": "rejected"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_empty_store(self, app) -> None:
        c = TestClient(app)
        resp = c.get("/proposals")
        assert resp.status_code == 200
        assert resp.json() == []


# ------------------------------------------------------------------
# GET /proposals/{proposal_id}
# ------------------------------------------------------------------


class TestGetProposal:
    def test_returns_single_proposal(self, client: TestClient) -> None:
        resp = client.get("/proposals/p-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "p-1"
        assert data["proposed_name"] == "invoice_2024.pdf"

    def test_404_for_unknown_id(self, client: TestClient) -> None:
        resp = client.get("/proposals/nonexistent")
        assert resp.status_code == 404


# ------------------------------------------------------------------
# PATCH /proposals/{proposal_id}
# ------------------------------------------------------------------


class TestUpdateProposal:
    def test_approve_proposal(self, client: TestClient) -> None:
        resp = client.patch("/proposals/p-1", json={"status": "approved"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"

    def test_reject_proposal(self, client: TestClient) -> None:
        resp = client.patch("/proposals/p-1", json={"status": "rejected"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_corrected_updates_name_and_folder(self, client: TestClient) -> None:
        resp = client.patch(
            "/proposals/p-1",
            json={
                "status": "corrected",
                "corrected_name": "fixed_name.pdf",
                "corrected_folder": "fixed_folder",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "corrected"
        assert data["proposed_name"] == "fixed_name.pdf"
        assert data["proposed_folder"] == "fixed_folder"

    def test_corrected_without_fields_returns_422(self, client: TestClient) -> None:
        resp = client.patch("/proposals/p-1", json={"status": "corrected"})
        assert resp.status_code == 422

    def test_404_for_unknown_id(self, client: TestClient) -> None:
        resp = client.patch("/proposals/nonexistent", json={"status": "approved"})
        assert resp.status_code == 404


# ------------------------------------------------------------------
# POST /proposals/execute
# ------------------------------------------------------------------


class TestExecuteProposals:
    def test_executes_approved_proposals(self, populated_app) -> None:
        mock_fm = MagicMock(spec=FileManagerService)

        # Build the Proposal that the route will reconstruct from stored dict
        p2_dict = populated_app.state.proposals["p-2"]
        expected_proposal = Proposal(
            id="p-2",
            original_path=Path(p2_dict["original_path"]),
            original_name=p2_dict["original_name"],
            proposed_name=p2_dict["proposed_name"],
            proposed_folder=Path(p2_dict["proposed_folder"]),
            confidence=p2_dict["confidence"],
            matched_rule=p2_dict["matched_rule"],
            status=p2_dict["status"],
        )

        mock_fm.execute_batch.return_value = [
            (expected_proposal, Path("/archive/invoices/receipt.pdf")),
        ]

        from zerobox.api.dependencies import get_filemanager

        populated_app.dependency_overrides[get_filemanager] = lambda: mock_fm
        c = TestClient(populated_app)

        resp = c.post("/proposals/execute")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["proposal_id"] == "p-2"
        assert data[0]["target_path"] is not None

    def test_returns_empty_when_no_approved(self, app) -> None:
        # Only pending proposals
        p = _sample_proposal(id="p-1", status="pending")
        app.state.proposals = {"p-1": _proposal_to_dict(p)}

        mock_fm = MagicMock(spec=FileManagerService)
        mock_fm.execute_batch.return_value = []

        from zerobox.api.dependencies import get_filemanager

        app.dependency_overrides[get_filemanager] = lambda: mock_fm
        c = TestClient(app)

        resp = c.post("/proposals/execute")
        assert resp.status_code == 200
        assert resp.json() == []
        mock_fm.execute_batch.assert_called_once_with([])
