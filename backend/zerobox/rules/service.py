"""Rule engine — JSON profile management and pattern matching (FR-05)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from zerobox.rules.models import Rule, RuleProfile

if TYPE_CHECKING:
    from zerobox.audit.service import AuditService

logger = logging.getLogger(__name__)

_PROFILE_REQUIRED_KEYS = {"id", "name", "rules"}
_RULE_REQUIRED_KEYS = {"id", "patterns", "target_name_template", "target_folder_template"}


def _validate_profile_data(data: dict) -> None:
    """Validate profile JSON structure manually (no external dependency)."""
    if not isinstance(data, dict):
        msg = "Profile data must be a JSON object"
        raise ValueError(msg)

    missing = _PROFILE_REQUIRED_KEYS - data.keys()
    if missing:
        msg = f"Profile missing required keys: {sorted(missing)}"
        raise ValueError(msg)

    if not isinstance(data["id"], str):
        msg = "Profile 'id' must be a string"
        raise ValueError(msg)
    if not isinstance(data["name"], str):
        msg = "Profile 'name' must be a string"
        raise ValueError(msg)
    if not isinstance(data["rules"], list):
        msg = "Profile 'rules' must be an array"
        raise ValueError(msg)

    for i, rule in enumerate(data["rules"]):
        if not isinstance(rule, dict):
            msg = f"Rule at index {i} must be a JSON object"
            raise ValueError(msg)
        rule_missing = _RULE_REQUIRED_KEYS - rule.keys()
        if rule_missing:
            msg = f"Rule at index {i} missing required keys: {sorted(rule_missing)}"
            raise ValueError(msg)
        if not isinstance(rule["patterns"], list):
            msg = f"Rule at index {i}: 'patterns' must be an array"
            raise ValueError(msg)
        if not all(isinstance(p, str) for p in rule["patterns"]):
            msg = f"Rule at index {i}: all patterns must be strings"
            raise ValueError(msg)


def _profile_to_dict(profile: RuleProfile) -> dict:
    """Serialize a RuleProfile to a JSON-compatible dict."""
    return {
        "id": profile.id,
        "name": profile.name,
        "description": profile.description,
        "rules": [
            {
                "id": rule.id,
                "profile_id": rule.profile_id,
                "patterns": rule.patterns,
                "target_name_template": rule.target_name_template,
                "target_folder_template": rule.target_folder_template,
                "priority": rule.priority,
                "examples": rule.examples,
            }
            for rule in profile.rules
        ],
    }


def _dict_to_profile(data: dict) -> RuleProfile:
    """Deserialize a dict into a RuleProfile."""
    profile_id = data["id"]
    rules = [
        Rule(
            id=r["id"],
            profile_id=r.get("profile_id", profile_id),
            patterns=r["patterns"],
            target_name_template=r["target_name_template"],
            target_folder_template=r["target_folder_template"],
            priority=r.get("priority", 0),
            examples=r.get("examples", []),
        )
        for r in data.get("rules", [])
    ]
    return RuleProfile(
        id=profile_id,
        name=data["name"],
        description=data.get("description", ""),
        rules=rules,
    )


class RuleService:
    """Manages rule profiles on disk and provides pattern matching."""

    def __init__(
        self,
        profiles_dir: Path,
        audit: AuditService | None = None,
    ) -> None:
        self._profiles_dir = profiles_dir
        self._audit = audit
        self._profiles_dir.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, profile_id: str) -> Path:
        return self._profiles_dir / f"{profile_id}.json"

    def _log(
        self,
        action: str,
        source: str,
        *,
        rule_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        if self._audit is not None:
            self._audit.log(
                action=action,
                source=source,
                rule_id=rule_id,
                details=details,
            )

    # ── CRUD: profiles ──────────────────────────────────────────────

    def list_profiles(self) -> list[RuleProfile]:
        """List all rule profiles stored in the profiles directory."""
        profiles: list[RuleProfile] = []
        for path in sorted(self._profiles_dir.glob("*.json")):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            profiles.append(_dict_to_profile(data))
        return profiles

    def get_profile(self, profile_id: str) -> RuleProfile:
        """Load a single profile by ID.

        Raises ``FileNotFoundError`` when the profile does not exist.
        """
        path = self._profile_path(profile_id)
        if not path.exists():
            msg = f"Profile not found: {profile_id}"
            raise FileNotFoundError(msg)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return _dict_to_profile(data)

    def save_profile(self, profile: RuleProfile) -> None:
        """Validate and persist a profile to disk."""
        data = _profile_to_dict(profile)
        _validate_profile_data(data)
        path = self._profile_path(profile.id)
        is_new = not path.exists()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if is_new:
            self._log("profile_created", profile.id, details={"name": profile.name})
        logger.info("Saved profile %s to %s", profile.id, path)

    def delete_profile(self, profile_id: str) -> None:
        """Remove a profile file from disk.

        Raises ``FileNotFoundError`` when the profile does not exist.
        """
        path = self._profile_path(profile_id)
        if not path.exists():
            msg = f"Profile not found: {profile_id}"
            raise FileNotFoundError(msg)
        path.unlink()
        self._log("profile_deleted", profile_id)
        logger.info("Deleted profile %s", profile_id)

    # ── CRUD: rules ─────────────────────────────────────────────────

    def add_rule(self, profile_id: str, rule: Rule) -> None:
        """Add a rule to an existing profile and save."""
        profile = self.get_profile(profile_id)
        rule.profile_id = profile_id
        profile.rules.append(rule)
        self.save_profile(profile)
        self._log("rule_created", profile_id, rule_id=rule.id)

    def remove_rule(self, profile_id: str, rule_id: str) -> None:
        """Remove a rule from a profile by rule ID.

        Raises ``ValueError`` when the rule is not found in the profile.
        """
        profile = self.get_profile(profile_id)
        original_len = len(profile.rules)
        profile.rules = [r for r in profile.rules if r.id != rule_id]
        if len(profile.rules) == original_len:
            msg = f"Rule not found: {rule_id} in profile {profile_id}"
            raise ValueError(msg)
        self.save_profile(profile)
        self._log("rule_deleted", profile_id, rule_id=rule_id)

    # ── Pattern matching ────────────────────────────────────────────

    def match_rules(self, text: str) -> list[Rule]:
        """Find all rules whose patterns match the given text.

        All patterns in a rule must be present (case-insensitive) for the rule
        to match.  Results are sorted by priority, highest first.
        """
        text_lower = text.lower()
        matched: list[Rule] = []
        for profile in self.list_profiles():
            for rule in profile.rules:
                if all(p.lower() in text_lower for p in rule.patterns):
                    matched.append(rule)
        matched.sort(key=lambda r: r.priority, reverse=True)
        return matched
