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
