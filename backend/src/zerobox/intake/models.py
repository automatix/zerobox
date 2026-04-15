"""Intake data models (FR-01)."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class IntakeFile:
    """Represents a file discovered by the intake module."""

    path: Path
    file_type: str
    size_bytes: int
    modified_at: datetime
