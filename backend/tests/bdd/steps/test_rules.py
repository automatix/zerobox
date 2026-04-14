"""Step definitions for rules.feature."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from zerobox.rules.models import Rule, RuleProfile

scenarios("../features/rules.feature")


# ------------------------------------------------------------------
# Shared state
# ------------------------------------------------------------------


@pytest.fixture()
def rules_context():
    """Mutable dict to pass state between steps."""
    return {}


# ------------------------------------------------------------------
# Given
# ------------------------------------------------------------------


@given("no profiles exist", target_fixture="rules_context")
def no_profiles(rule_service, rules_context):
    rules_context["service"] = rule_service
    assert len(rule_service.list_profiles()) == 0
    return rules_context


@given(parsers.parse('a profile "{profile_id}" exists'), target_fixture="rules_context")
def profile_exists(profile_id, rule_service, rules_context):
    profile = RuleProfile(id=profile_id, name=f"{profile_id} profile")
    rule_service.save_profile(profile)
    rules_context["service"] = rule_service
    rules_context["profile_id"] = profile_id
    return rules_context


@given(
    parsers.parse('a profile with a rule matching "{pattern1}" and "{pattern2}"'),
    target_fixture="rules_context",
)
def profile_with_matching_rule(pattern1, pattern2, rule_service, rules_context):
    profile = RuleProfile(id="match-test", name="Match Test")
    rule_service.save_profile(profile)
    rule = Rule(
        id="rule-match-1",
        profile_id="match-test",
        patterns=[pattern1, pattern2],
        target_name_template="{date}_invoice",
        target_folder_template="Finanzen/Rechnungen",
    )
    rule_service.add_rule("match-test", rule)
    rules_context["service"] = rule_service
    rules_context["profile_id"] = "match-test"
    return rules_context


@given(
    parsers.parse('a profile "{profile_id}" with {count:d} rules'),
    target_fixture="rules_context",
)
def profile_with_n_rules(profile_id, count, rule_service, rules_context):
    profile = RuleProfile(id=profile_id, name=f"{profile_id} profile")
    rule_service.save_profile(profile)
    rule_ids = []
    for i in range(count):
        rule = Rule(
            id=f"rule-{i + 1}",
            profile_id=profile_id,
            patterns=[f"pattern-{i + 1}"],
            target_name_template=f"template-{i + 1}",
            target_folder_template=f"Folder/{i + 1}",
        )
        rule_service.add_rule(profile_id, rule)
        rule_ids.append(rule.id)
    rules_context["service"] = rule_service
    rules_context["profile_id"] = profile_id
    rules_context["rule_ids"] = rule_ids
    return rules_context


# ------------------------------------------------------------------
# When
# ------------------------------------------------------------------


@when(
    parsers.parse('I create a profile "{profile_id}" with name "{name}"'),
    target_fixture="rules_context",
)
def create_profile(profile_id, name, rules_context):
    service = rules_context["service"]
    profile = RuleProfile(id=profile_id, name=name)
    service.save_profile(profile)
    rules_context["profile_id"] = profile_id
    return rules_context


@when(
    parsers.re(r'I add a rule with patterns \["(?P<p1>[^"]+)", "(?P<p2>[^"]+)"\]'),
    target_fixture="rules_context",
)
def add_rule_with_patterns(p1, p2, rules_context):
    service = rules_context["service"]
    profile_id = rules_context["profile_id"]
    rule = Rule(
        id="new-rule-1",
        profile_id=profile_id,
        patterns=[p1, p2],
        target_name_template="{date}_invoice",
        target_folder_template="Finanzen/Rechnungen",
    )
    service.add_rule(profile_id, rule)
    rules_context["added_patterns"] = [p1, p2]
    return rules_context


@when(
    parsers.parse('I match rules against text containing "{text}"'),
    target_fixture="match_results",
)
def match_rules(text, rules_context):
    service = rules_context["service"]
    return service.match_rules(text)


@when("I delete the first rule", target_fixture="rules_context")
def delete_first_rule(rules_context):
    service = rules_context["service"]
    profile_id = rules_context["profile_id"]
    first_rule_id = rules_context["rule_ids"][0]
    service.remove_rule(profile_id, first_rule_id)
    return rules_context


# ------------------------------------------------------------------
# Then
# ------------------------------------------------------------------


@then("the profile should be saved")
def check_profile_saved(rules_context):
    service = rules_context["service"]
    profile_id = rules_context["profile_id"]
    profile = service.get_profile(profile_id)
    assert profile is not None
    assert profile.id == profile_id


@then(parsers.parse("listing profiles should return {count:d} profile"))
def check_profile_count(rules_context, count):
    service = rules_context["service"]
    profiles = service.list_profiles()
    assert len(profiles) == count


@then(parsers.parse("the profile should contain {count:d} rule"))
def check_rule_count(rules_context, count):
    service = rules_context["service"]
    profile_id = rules_context["profile_id"]
    profile = service.get_profile(profile_id)
    assert len(profile.rules) == count


@then("the rule should have the correct patterns")
def check_rule_patterns(rules_context):
    service = rules_context["service"]
    profile_id = rules_context["profile_id"]
    profile = service.get_profile(profile_id)
    expected = rules_context["added_patterns"]
    assert profile.rules[-1].patterns == expected


@then("the rule should match")
def check_rule_matched(match_results):
    assert len(match_results) > 0


@then("no rules should match")
def check_no_match(match_results):
    assert len(match_results) == 0
