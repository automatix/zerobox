"""Tests for rule profile CRUD routes (#18)."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from zerobox.api.dependencies import get_rules
from zerobox.app import create_app
from zerobox.rules.models import Rule, RuleProfile


@pytest.fixture()
def mock_rules():
    """Return a MagicMock that mimics RuleService."""
    return MagicMock()


@pytest.fixture()
def client(mock_rules):
    """TestClient with get_rules overridden to return mock_rules."""
    app = create_app()
    app.dependency_overrides[get_rules] = lambda: mock_rules
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── GET /rules/profiles ───────────────────────────────────────────


def test_list_profiles_returns_list(client, mock_rules):
    profile = RuleProfile(id="p1", name="Test", description="desc")
    mock_rules.list_profiles.return_value = [profile]

    resp = client.get("/rules/profiles")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "p1"
    assert data[0]["name"] == "Test"
    assert data[0]["rules"] == []


# ── GET /rules/profiles/{id} ──────────────────────────────────────


def test_get_profile_returns_profile(client, mock_rules):
    profile = RuleProfile(id="p1", name="Test")
    mock_rules.get_profile.return_value = profile

    resp = client.get("/rules/profiles/p1")

    assert resp.status_code == 200
    assert resp.json()["id"] == "p1"


def test_get_profile_returns_404(client, mock_rules):
    mock_rules.get_profile.side_effect = FileNotFoundError("not found")

    resp = client.get("/rules/profiles/missing")

    assert resp.status_code == 404


# ── POST /rules/profiles ──────────────────────────────────────────


def test_create_profile(client, mock_rules):
    mock_rules.get_profile.side_effect = FileNotFoundError("not found")

    resp = client.post(
        "/rules/profiles",
        json={"id": "new", "name": "New Profile", "description": "a desc"},
    )

    assert resp.status_code == 201
    assert resp.json()["id"] == "new"
    assert resp.json()["name"] == "New Profile"
    mock_rules.save_profile.assert_called_once()


def test_create_profile_conflict(client, mock_rules):
    mock_rules.get_profile.return_value = RuleProfile(id="dup", name="Dup")

    resp = client.post(
        "/rules/profiles",
        json={"id": "dup", "name": "Duplicate"},
    )

    assert resp.status_code == 409


# ── POST /rules/profiles — auto-generated id (#86) ────────────────


def test_create_profile_without_id_slugifies_name(client, mock_rules):
    """Regression for #86: the UI sends only {name, description}."""
    mock_rules.get_profile.side_effect = FileNotFoundError("not found")

    resp = client.post(
        "/rules/profiles",
        json={"name": "Dummy", "description": "Dummy profile"},
    )

    assert resp.status_code == 201
    saved_profile = mock_rules.save_profile.call_args.args[0]
    assert saved_profile.id == "dummy"
    assert saved_profile.name == "Dummy"


def test_create_profile_slugifies_spaces_and_casing(client, mock_rules):
    mock_rules.get_profile.side_effect = FileNotFoundError("not found")

    resp = client.post(
        "/rules/profiles",
        json={"name": "Rechnungen 2026"},
    )

    assert resp.status_code == 201
    assert mock_rules.save_profile.call_args.args[0].id == "rechnungen-2026"


def test_create_profile_appends_suffix_on_slug_collision(client, mock_rules):
    """First `get_profile("dummy")` returns a profile (taken); second
    `get_profile("dummy-2")` raises FileNotFoundError (free)."""
    mock_rules.get_profile.side_effect = [
        RuleProfile(id="dummy", name="taken"),
        FileNotFoundError("free"),
    ]

    resp = client.post(
        "/rules/profiles",
        json={"name": "Dummy"},
    )

    assert resp.status_code == 201
    assert mock_rules.save_profile.call_args.args[0].id == "dummy-2"


def test_create_profile_falls_back_to_random_id_for_non_alnum_name(
    client, mock_rules
):
    """A name like '~~~' has no alphanumeric chars → slug is empty → random id."""
    mock_rules.get_profile.side_effect = FileNotFoundError("not found")

    resp = client.post(
        "/rules/profiles",
        json={"name": "~~~"},
    )

    assert resp.status_code == 201
    new_id = mock_rules.save_profile.call_args.args[0].id
    assert new_id  # non-empty
    assert len(new_id) == 8  # uuid4().hex[:8]


def test_create_profile_honours_explicit_id(client, mock_rules):
    """Providing an explicit id still works (e.g. for imports / scripts)."""
    mock_rules.get_profile.side_effect = FileNotFoundError("not found")

    resp = client.post(
        "/rules/profiles",
        json={"id": "custom-id", "name": "Whatever"},
    )

    assert resp.status_code == 201
    assert mock_rules.save_profile.call_args.args[0].id == "custom-id"


# ── DELETE /rules/profiles/{id} ───────────────────────────────────


def test_delete_profile(client, mock_rules):
    resp = client.delete("/rules/profiles/p1")

    assert resp.status_code == 200
    assert resp.json() == {"status": "deleted"}
    mock_rules.delete_profile.assert_called_once_with("p1")


def test_delete_profile_404(client, mock_rules):
    mock_rules.delete_profile.side_effect = FileNotFoundError("not found")

    resp = client.delete("/rules/profiles/missing")

    assert resp.status_code == 404


# ── POST /rules/profiles/{id}/rules ──────────────────────────────


def test_add_rule(client, mock_rules):
    profile_with_rule = RuleProfile(
        id="p1",
        name="Test",
        rules=[
            Rule(
                id="r1",
                profile_id="p1",
                patterns=["invoice"],
                target_name_template="{date}_invoice",
                target_folder_template="Invoices",
            )
        ],
    )
    mock_rules.get_profile.return_value = profile_with_rule

    resp = client.post(
        "/rules/profiles/p1/rules",
        json={
            "id": "r1",
            "patterns": ["invoice"],
            "target_name_template": "{date}_invoice",
            "target_folder_template": "Invoices",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert len(data["rules"]) == 1
    assert data["rules"][0]["id"] == "r1"
    mock_rules.add_rule.assert_called_once()


# ── POST /rules/profiles/{id}/rules — auto-generated id (#86) ────


def test_add_rule_without_id_generates_random(client, mock_rules):
    """Frontend sends no `id` on add-rule; backend generates one."""
    mock_rules.get_profile.return_value = RuleProfile(id="p1", name="Test")

    resp = client.post(
        "/rules/profiles/p1/rules",
        json={
            "patterns": ["invoice"],
            "target_name_template": "{date}_invoice",
            "target_folder_template": "Invoices",
        },
    )

    assert resp.status_code == 201
    added_rule = mock_rules.add_rule.call_args.args[1]
    assert added_rule.id  # non-empty
    assert len(added_rule.id) == 8


def test_add_rule_404_on_missing_profile(client, mock_rules):
    mock_rules.get_profile.side_effect = FileNotFoundError("no profile")

    resp = client.post(
        "/rules/profiles/does-not-exist/rules",
        json={
            "patterns": ["x"],
            "target_name_template": "",
            "target_folder_template": "",
        },
    )

    assert resp.status_code == 404


# ── DELETE /rules/profiles/{id}/rules/{rule_id} ──────────────────


def test_remove_rule(client, mock_rules):
    resp = client.delete("/rules/profiles/p1/rules/r1")

    assert resp.status_code == 200
    assert resp.json() == {"status": "deleted"}
    mock_rules.remove_rule.assert_called_once_with("p1", "r1")


def test_remove_rule_profile_not_found(client, mock_rules):
    mock_rules.remove_rule.side_effect = FileNotFoundError("not found")

    resp = client.delete("/rules/profiles/missing/rules/r1")

    assert resp.status_code == 404


def test_remove_rule_rule_not_found(client, mock_rules):
    mock_rules.remove_rule.side_effect = ValueError("not found")

    resp = client.delete("/rules/profiles/p1/rules/missing")

    assert resp.status_code == 404
