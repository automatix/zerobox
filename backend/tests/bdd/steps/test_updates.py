"""Step definitions for updates.feature."""

from __future__ import annotations

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from zerobox import updates

scenarios("../features/updates.feature")


# ------------------------------------------------------------------
# Shared state
# ------------------------------------------------------------------


@pytest.fixture()
def updates_context():
    """Mutable dict to pass state between steps."""
    return {}


def _release_payload(tag: str) -> dict:
    return {
        "tag_name": f"v{tag}",
        "html_url": f"https://github.com/automatix/zerobox/releases/tag/v{tag}",
        "assets": [
            {
                "name": f"zerobox_{tag}_x64-setup.exe",
                "browser_download_url": (
                    f"https://github.com/automatix/zerobox/releases/download/v{tag}/"
                    f"zerobox_{tag}_x64-setup.exe"
                ),
            }
        ],
    }


# ------------------------------------------------------------------
# Given
# ------------------------------------------------------------------


@given(parsers.parse('the running version is "{version}"'), target_fixture="updates_context")
def running_version(version, updates_context):
    updates_context["current"] = version
    return updates_context


@given(parsers.parse('the latest published release is "{version}"'))
def latest_release(version, updates_context):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_release_payload(version))

    updates_context["client"] = httpx.Client(transport=httpx.MockTransport(handler))


@given("the update server is unreachable")
def server_unreachable(updates_context):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network", request=request)

    updates_context["client"] = httpx.Client(transport=httpx.MockTransport(handler))


# ------------------------------------------------------------------
# When
# ------------------------------------------------------------------


@when("I check for updates")
def check_for_updates(updates_context):
    try:
        updates_context["info"] = updates.check_for_update(
            updates_context["current"], client=updates_context["client"]
        )
    except httpx.HTTPError as exc:
        updates_context["error"] = exc


# ------------------------------------------------------------------
# Then
# ------------------------------------------------------------------


@then("an update should be reported as available")
def update_available(updates_context):
    assert updates_context["info"].update_available is True


@then("the installer asset URL should point to a GitHub host")
def asset_url_is_trusted(updates_context):
    asset_url = updates_context["info"].asset_url
    assert asset_url is not None
    assert updates.is_trusted_asset_url(asset_url)


@then("no update should be reported")
def no_update(updates_context):
    assert updates_context["info"].update_available is False


@then("the check should fail with a network error")
def check_failed(updates_context):
    assert "info" not in updates_context
    assert isinstance(updates_context["error"], httpx.HTTPError)
