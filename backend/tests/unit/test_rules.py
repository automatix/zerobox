"""Unit tests for the rule engine module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from zerobox.rules.models import Rule, RuleProfile
from zerobox.rules.service import RuleService


# ── Helpers ──────────────────────────────────────────────────────────


def _make_rule(
    rule_id: str = "r-1",
    profile_id: str = "p-1",
    patterns: list[str] | None = None,
    priority: int = 0,
) -> Rule:
    return Rule(
        id=rule_id,
        profile_id=profile_id,
        patterns=patterns or ["invoice"],
        target_name_template="{date}_{type}",
        target_folder_template="Finanzen/Rechnungen",
        priority=priority,
    )


def _make_profile(
    profile_id: str = "p-1",
    name: str = "Default",
    rules: list[Rule] | None = None,
) -> RuleProfile:
    return RuleProfile(id=profile_id, name=name, rules=rules or [])


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def service(tmp_path: Path) -> RuleService:
    return RuleService(profiles_dir=tmp_path / "profiles")


@pytest.fixture
def audit_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service_with_audit(tmp_path: Path, audit_mock: MagicMock) -> RuleService:
    return RuleService(profiles_dir=tmp_path / "profiles_audit", audit=audit_mock)


# ── Profile CRUD ─────────────────────────────────────────────────────


class TestProfileCRUD:
    def test_save_and_load_roundtrip(self, service: RuleService) -> None:
        rule = _make_rule()
        profile = _make_profile(rules=[rule])
        service.save_profile(profile)

        loaded = service.get_profile("p-1")
        assert loaded.id == "p-1"
        assert loaded.name == "Default"
        assert len(loaded.rules) == 1
        assert loaded.rules[0].id == "r-1"
        assert loaded.rules[0].patterns == ["invoice"]
        assert loaded.rules[0].priority == 0

    def test_list_profiles_multiple(self, service: RuleService) -> None:
        service.save_profile(_make_profile("a", "Alpha"))
        service.save_profile(_make_profile("b", "Beta"))
        profiles = service.list_profiles()
        assert len(profiles) == 2
        ids = {p.id for p in profiles}
        assert ids == {"a", "b"}

    def test_list_profiles_empty(self, service: RuleService) -> None:
        assert service.list_profiles() == []

    def test_get_profile_not_found(self, service: RuleService) -> None:
        with pytest.raises(FileNotFoundError, match="no-such"):
            service.get_profile("no-such")

    def test_delete_profile(self, service: RuleService) -> None:
        service.save_profile(_make_profile("del-me", "To Delete"))
        assert len(service.list_profiles()) == 1
        service.delete_profile("del-me")
        assert service.list_profiles() == []

    def test_delete_profile_not_found(self, service: RuleService) -> None:
        with pytest.raises(FileNotFoundError, match="ghost"):
            service.delete_profile("ghost")


# ── Rule CRUD ────────────────────────────────────────────────────────


class TestRuleCRUD:
    def test_add_rule(self, service: RuleService) -> None:
        service.save_profile(_make_profile("p-1", "Prof"))
        rule = _make_rule("r-new", "p-1", patterns=["contract"])
        service.add_rule("p-1", rule)

        loaded = service.get_profile("p-1")
        assert len(loaded.rules) == 1
        assert loaded.rules[0].id == "r-new"
        assert loaded.rules[0].profile_id == "p-1"

    def test_remove_rule(self, service: RuleService) -> None:
        rule = _make_rule("r-1")
        service.save_profile(_make_profile("p-1", "Prof", rules=[rule]))
        service.remove_rule("p-1", "r-1")

        loaded = service.get_profile("p-1")
        assert len(loaded.rules) == 0

    def test_remove_rule_not_found(self, service: RuleService) -> None:
        service.save_profile(_make_profile("p-1", "Prof"))
        with pytest.raises(ValueError, match="Rule not found"):
            service.remove_rule("p-1", "nonexistent")


# ── Pattern matching ─────────────────────────────────────────────────


class TestMatchRules:
    def test_match_single_pattern(self, service: RuleService) -> None:
        rule = _make_rule(patterns=["invoice"])
        service.save_profile(_make_profile(rules=[rule]))

        matches = service.match_rules("This is an invoice from ACME")
        assert len(matches) == 1
        assert matches[0].id == "r-1"

    def test_match_all_patterns_required(self, service: RuleService) -> None:
        rule = _make_rule(patterns=["invoice", "acme"])
        service.save_profile(_make_profile(rules=[rule]))

        assert service.match_rules("invoice from ACME") != []
        assert service.match_rules("invoice from Other") == []

    def test_match_case_insensitive(self, service: RuleService) -> None:
        rule = _make_rule(patterns=["INVOICE"])
        service.save_profile(_make_profile(rules=[rule]))

        matches = service.match_rules("this is an invoice")
        assert len(matches) == 1

    def test_match_no_match(self, service: RuleService) -> None:
        rule = _make_rule(patterns=["receipt"])
        service.save_profile(_make_profile(rules=[rule]))
        assert service.match_rules("unrelated document text") == []

    def test_match_sorted_by_priority(self, service: RuleService) -> None:
        low = _make_rule("r-low", priority=1, patterns=["doc"])
        high = _make_rule("r-high", priority=10, patterns=["doc"])
        mid = _make_rule("r-mid", priority=5, patterns=["doc"])
        service.save_profile(_make_profile(rules=[low, high, mid]))

        matches = service.match_rules("this is a doc")
        assert [m.id for m in matches] == ["r-high", "r-mid", "r-low"]

    def test_match_across_multiple_profiles(self, service: RuleService) -> None:
        r1 = _make_rule("r-1", "p-a", patterns=["invoice"])
        r2 = _make_rule("r-2", "p-b", patterns=["invoice"])
        service.save_profile(_make_profile("p-a", "A", rules=[r1]))
        service.save_profile(_make_profile("p-b", "B", rules=[r2]))

        matches = service.match_rules("an invoice arrived")
        assert len(matches) == 2
        matched_ids = {m.id for m in matches}
        assert matched_ids == {"r-1", "r-2"}


# ── Audit logging ───────────────────────────────────────────────────


class TestAuditIntegration:
    def test_profile_created_logged(
        self, service_with_audit: RuleService, audit_mock: MagicMock
    ) -> None:
        service_with_audit.save_profile(_make_profile("p-1", "Test"))
        audit_mock.log.assert_any_call(
            action="profile_created",
            source="p-1",
            rule_id=None,
            details={"name": "Test"},
        )

    def test_profile_deleted_logged(
        self, service_with_audit: RuleService, audit_mock: MagicMock
    ) -> None:
        service_with_audit.save_profile(_make_profile("p-1", "Test"))
        audit_mock.reset_mock()
        service_with_audit.delete_profile("p-1")
        audit_mock.log.assert_called_once_with(
            action="profile_deleted",
            source="p-1",
            rule_id=None,
            details=None,
        )

    def test_rule_created_logged(
        self, service_with_audit: RuleService, audit_mock: MagicMock
    ) -> None:
        service_with_audit.save_profile(_make_profile("p-1", "Prof"))
        audit_mock.reset_mock()
        service_with_audit.add_rule("p-1", _make_rule("r-new"))
        audit_mock.log.assert_any_call(
            action="rule_created",
            source="p-1",
            rule_id="r-new",
            details=None,
        )

    def test_rule_deleted_logged(
        self, service_with_audit: RuleService, audit_mock: MagicMock
    ) -> None:
        rule = _make_rule("r-1")
        service_with_audit.save_profile(_make_profile("p-1", "Prof", rules=[rule]))
        audit_mock.reset_mock()
        service_with_audit.remove_rule("p-1", "r-1")
        audit_mock.log.assert_any_call(
            action="rule_deleted",
            source="p-1",
            rule_id="r-1",
            details=None,
        )
