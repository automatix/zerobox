"""Audit log data models."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AuditEntry:
    timestamp: datetime
    action: str
    source: str
    target: str | None = None
    rule_id: str | None = None
    details: dict = field(default_factory=dict)
    id: int | None = None
