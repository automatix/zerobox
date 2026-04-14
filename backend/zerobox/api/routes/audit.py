"""Audit log API routes (#19)."""

from datetime import datetime

from fastapi import APIRouter, Depends

from zerobox.api.dependencies import get_audit
from zerobox.audit.models import AuditEntry
from zerobox.audit.service import AuditService

router = APIRouter()


def _entry_to_dict(entry: AuditEntry) -> dict:
    """Serialize an AuditEntry dataclass to a JSON-compatible dict."""
    return {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat(),
        "action": entry.action,
        "source": entry.source,
        "target": entry.target,
        "rule_id": entry.rule_id,
        "details": entry.details,
    }


@router.get("/log")
def get_audit_log(
    action: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    rule_id: str | None = None,
    limit: int = 100,
    audit: AuditService = Depends(get_audit),
) -> list[dict]:
    """Query the audit log with optional filters."""
    entries = audit.query(
        action=action,
        start=start,
        end=end,
        rule_id=rule_id,
        limit=limit,
    )
    return [_entry_to_dict(e) for e in entries]
