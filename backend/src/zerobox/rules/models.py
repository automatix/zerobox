"""Rule engine data models (FR-05)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Rule:
    """A single classification rule with text patterns and filing templates."""

    id: str
    profile_id: str
    patterns: list[str]  # text patterns to match (case-insensitive)
    target_name_template: str  # e.g. "{date}_{type}_{sender}"
    target_folder_template: str  # e.g. "Finanzen/Rechnungen"
    priority: int = 0  # higher = checked first
    examples: list[str] = field(default_factory=list)


@dataclass
class RuleProfile:
    """A named collection of classification rules."""

    id: str
    name: str
    description: str = ""
    rules: list[Rule] = field(default_factory=list)
