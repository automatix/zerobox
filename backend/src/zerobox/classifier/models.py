"""Classifier data models (FR-08)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class ClassificationContext:
    """Context passed to the LLM for classification."""

    original_path: Path
    original_name: str
    file_type: str


@dataclass
class ClassificationResult:
    """Raw result from an LLM provider."""

    proposed_name: str
    proposed_folder: str
    confidence: float  # 0.0–1.0
    matched_rule_id: str | None = None
    reasoning: str = ""


@dataclass
class UserCorrection:
    """A user's correction to a classification result."""

    original_text: str
    original_proposal_name: str
    original_proposal_folder: str
    corrected_name: str
    corrected_folder: str


@dataclass
class Proposal:
    """A classification proposal shown to the user for review."""

    id: str
    original_path: Path
    original_name: str
    proposed_name: str
    proposed_folder: Path
    confidence: float
    matched_rule: str | None
    status: Literal["pending", "approved", "rejected", "corrected"]
