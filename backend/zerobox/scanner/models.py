"""Scanner data models (FR-01)."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ScannedFile:
    """Represents a file discovered by the scanner."""

    path: Path
    file_type: str
    size_bytes: int
    modified_at: datetime
