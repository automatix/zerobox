"""Unit tests for the audit logging module."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from zerobox.audit.models import AuditEntry
from zerobox.audit.service import AuditService


@pytest.fixture
def audit_service(tmp_path: Path) -> AuditService:
    return AuditService(db_path=tmp_path / "test_audit.db")


class TestAuditEntry:
    def test_defaults(self) -> None:
        entry = AuditEntry(timestamp=datetime.now(), action="test", source="file.pdf")
        assert entry.target is None
        assert entry.rule_id is None
        assert entry.details == {}
        assert entry.id is None


class TestAuditService:
    def test_log_creates_entry(self, audit_service: AuditService) -> None:
        entry = audit_service.log(action="moved", source="scan.pdf", target="archive/scan.pdf")
        assert entry.id is not None
        assert entry.action == "moved"
        assert entry.source == "scan.pdf"
        assert entry.target == "archive/scan.pdf"

    def test_log_with_details(self, audit_service: AuditService) -> None:
        entry = audit_service.log(
            action="classified",
            source="scan.pdf",
            details={"confidence": 0.95},
        )
        assert entry.details == {"confidence": 0.95}

    def test_query_returns_all(self, audit_service: AuditService) -> None:
        audit_service.log(action="moved", source="a.pdf")
        audit_service.log(action="classified", source="b.pdf")
        results = audit_service.query()
        assert len(results) == 2

    def test_query_filter_by_action(self, audit_service: AuditService) -> None:
        audit_service.log(action="moved", source="a.pdf")
        audit_service.log(action="classified", source="b.pdf")
        audit_service.log(action="moved", source="c.pdf")
        results = audit_service.query(action="moved")
        assert len(results) == 2
        assert all(e.action == "moved" for e in results)

    def test_query_filter_by_rule_id(self, audit_service: AuditService) -> None:
        audit_service.log(action="classified", source="a.pdf", rule_id="rule-1")
        audit_service.log(action="classified", source="b.pdf", rule_id="rule-2")
        results = audit_service.query(rule_id="rule-1")
        assert len(results) == 1
        assert results[0].source == "a.pdf"

    def test_query_filter_by_date_range(self, audit_service: AuditService) -> None:
        audit_service.log(action="moved", source="a.pdf")
        now = datetime.now()
        results = audit_service.query(
            start=now - timedelta(minutes=1),
            end=now + timedelta(minutes=1),
        )
        assert len(results) == 1

    def test_query_limit(self, audit_service: AuditService) -> None:
        for i in range(5):
            audit_service.log(action="moved", source=f"{i}.pdf")
        results = audit_service.query(limit=3)
        assert len(results) == 3

    def test_query_order_desc(self, audit_service: AuditService) -> None:
        audit_service.log(action="moved", source="first.pdf")
        audit_service.log(action="moved", source="second.pdf")
        results = audit_service.query()
        assert results[0].source == "second.pdf"
        assert results[1].source == "first.pdf"

    def test_auto_creates_db_directory(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "nested" / "dir" / "audit.db"
        service = AuditService(db_path=deep_path)
        service.log(action="test", source="test.pdf")
        assert deep_path.exists()
