"""Unit tests for audit log API routes (#19)."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from zerobox.api.dependencies import get_audit
from zerobox.app import create_app
from zerobox.audit.models import AuditEntry


def _make_entry(
    *,
    id: int = 1,
    action: str = "file.move",
    source: str = "/inbox/scan.pdf",
    target: str | None = "/docs/invoice.pdf",
    rule_id: str | None = "rule-invoices",
    details: dict | None = None,
    timestamp: datetime | None = None,
) -> AuditEntry:
    return AuditEntry(
        id=id,
        timestamp=timestamp or datetime(2026, 4, 14, 10, 30, 0),
        action=action,
        source=source,
        target=target,
        rule_id=rule_id,
        details=details or {},
    )


@pytest.fixture()
def _audit_app():
    """Create app with a mocked audit dependency."""
    app = create_app()
    mock_audit = MagicMock()
    mock_audit.query = MagicMock(return_value=[])
    app.dependency_overrides[get_audit] = lambda: mock_audit
    client = TestClient(app)
    return client, mock_audit


class TestGetAuditLog:
    """GET /audit/log."""

    def test_returns_list_of_entries(self, _audit_app):
        client, mock_audit = _audit_app
        entries = [_make_entry(id=1), _make_entry(id=2, action="file.rename")]
        mock_audit.query.return_value = entries

        response = client.get("/audit/log")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["id"] == 1
        assert body[0]["action"] == "file.move"
        assert body[0]["timestamp"] == "2026-04-14T10:30:00"
        assert body[0]["source"] == "/inbox/scan.pdf"
        assert body[0]["target"] == "/docs/invoice.pdf"
        assert body[0]["rule_id"] == "rule-invoices"
        assert body[0]["details"] == {}
        assert body[1]["id"] == 2
        assert body[1]["action"] == "file.rename"

    def test_with_action_filter(self, _audit_app):
        client, mock_audit = _audit_app
        mock_audit.query.return_value = [_make_entry(action="ocr.complete")]

        response = client.get("/audit/log", params={"action": "ocr.complete"})

        assert response.status_code == 200
        mock_audit.query.assert_called_once_with(
            action="ocr.complete", start=None, end=None, rule_id=None, limit=100,
        )

    def test_with_limit_parameter(self, _audit_app):
        client, mock_audit = _audit_app
        mock_audit.query.return_value = [_make_entry()]

        response = client.get("/audit/log", params={"limit": 5})

        assert response.status_code == 200
        mock_audit.query.assert_called_once_with(
            action=None, start=None, end=None, rule_id=None, limit=5,
        )

    def test_with_date_range_filters(self, _audit_app):
        client, mock_audit = _audit_app
        mock_audit.query.return_value = []

        response = client.get(
            "/audit/log",
            params={
                "start": "2026-04-01T00:00:00",
                "end": "2026-04-14T23:59:59",
            },
        )

        assert response.status_code == 200
        mock_audit.query.assert_called_once_with(
            action=None,
            start=datetime(2026, 4, 1, 0, 0, 0),
            end=datetime(2026, 4, 14, 23, 59, 59),
            rule_id=None,
            limit=100,
        )

    def test_with_rule_id_filter(self, _audit_app):
        client, mock_audit = _audit_app
        mock_audit.query.return_value = [_make_entry(rule_id="rule-receipts")]

        response = client.get("/audit/log", params={"rule_id": "rule-receipts"})

        assert response.status_code == 200
        mock_audit.query.assert_called_once_with(
            action=None, start=None, end=None, rule_id="rule-receipts", limit=100,
        )

    def test_empty_result(self, _audit_app):
        client, mock_audit = _audit_app
        mock_audit.query.return_value = []

        response = client.get("/audit/log")

        assert response.status_code == 200
        assert response.json() == []
