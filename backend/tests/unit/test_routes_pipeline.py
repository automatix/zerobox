"""Unit tests for pipeline API routes (#16)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from zerobox.api.dependencies import get_pipeline
from zerobox.app import create_app
from zerobox.classifier.models import Proposal


@pytest.fixture()
def _pipeline_app():
    """Create app with a mocked pipeline dependency."""
    app = create_app()
    mock_pipeline = MagicMock()
    mock_pipeline.run = AsyncMock()
    mock_pipeline.run_and_execute = AsyncMock()
    app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
    client = TestClient(app)
    return client, mock_pipeline


def _make_proposal(
    *,
    id: str = "p-001",
    status: str = "pending",
) -> Proposal:
    return Proposal(
        id=id,
        original_path=Path("/inbox/scan_001.pdf"),
        original_name="scan_001.pdf",
        proposed_name="Invoice_2026-04.pdf",
        proposed_folder=Path("/documents/invoices"),
        confidence=0.92,
        matched_rule="rule-invoices",
        status=status,
    )


class TestRunPipeline:
    """POST /pipeline/run."""

    def test_returns_proposals(self, _pipeline_app):
        client, mock_pipeline = _pipeline_app
        proposals = [_make_proposal(), _make_proposal(id="p-002")]
        mock_pipeline.run.return_value = proposals

        response = client.post("/pipeline/run")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert len(body["proposals"]) == 2
        p = body["proposals"][0]
        assert p["id"] == "p-001"
        assert p["original_path"] == str(Path("/inbox/scan_001.pdf"))
        assert p["proposed_folder"] == str(Path("/documents/invoices"))
        assert p["confidence"] == 0.92
        assert p["matched_rule"] == "rule-invoices"
        assert p["status"] == "pending"

    def test_empty_inbox(self, _pipeline_app):
        client, mock_pipeline = _pipeline_app
        mock_pipeline.run.return_value = []

        response = client.post("/pipeline/run")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert body["proposals"] == []


class TestRunAndExecutePipeline:
    """POST /pipeline/run-and-execute."""

    def test_with_auto_approve(self, _pipeline_app):
        client, mock_pipeline = _pipeline_app
        proposal = _make_proposal(status="approved")
        target = Path("/documents/invoices/Invoice_2026-04.pdf")
        mock_pipeline.run_and_execute.return_value = [(proposal, target)]

        response = client.post("/pipeline/run-and-execute?auto_approve=true")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert len(body["results"]) == 1
        result = body["results"][0]
        assert result["proposal"]["id"] == "p-001"
        assert result["target_path"] == str(target)
        mock_pipeline.run_and_execute.assert_called_once_with(auto_approve=True)

    def test_without_auto_approve(self, _pipeline_app):
        client, mock_pipeline = _pipeline_app
        proposal = _make_proposal()
        mock_pipeline.run_and_execute.return_value = [(proposal, None)]

        response = client.post("/pipeline/run-and-execute")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        result = body["results"][0]
        assert result["target_path"] is None
        mock_pipeline.run_and_execute.assert_called_once_with(auto_approve=False)
