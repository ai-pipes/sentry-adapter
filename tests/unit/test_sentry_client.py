import pytest
import respx
import httpx
from datetime import timezone

from sentry_adapter.infrastructure.sentry_client import SentryClient
from sentry_adapter.domain.exceptions import (
    SentryAuthError, SentryNotFoundError, SentryTimeoutError, SentryUpstreamError,
)


@pytest.fixture
def client():
    return SentryClient(
        base_url="https://sentry.example.com",
        auth_token="tok-test",
        organization="acme",
        timeout=5,
    )


@respx.mock
async def test_list_projects(client):
    respx.get("https://sentry.example.com/api/0/organizations/acme/projects/").mock(
        return_value=httpx.Response(200, json=[
            {"id": "1", "slug": "backend", "name": "Backend", "platform": "python", "status": "active"},
        ])
    )
    projects = await client.list_projects()
    assert len(projects) == 1
    assert projects[0].slug == "backend"
    assert projects[0].platform == "python"


@respx.mock
async def test_list_issues(client):
    respx.get("https://sentry.example.com/api/0/projects/acme/backend/issues/").mock(
        return_value=httpx.Response(200, json=[{
            "id": "42",
            "title": "ZeroDivisionError: division by zero",
            "culprit": "app/views.py in divide",
            "status": "unresolved",
            "count": "15",
            "firstSeen": "2026-01-01T00:00:00Z",
            "lastSeen": "2026-06-01T00:00:00Z",
            "metadata": {},
        }])
    )
    issues = await client.list_issues("backend", query="is:unresolved", limit=10)
    assert issues[0].id == "42"
    assert issues[0].count == 15
    assert issues[0].first_seen.tzinfo is not None


@respx.mock
async def test_get_issue(client):
    respx.get("https://sentry.example.com/api/0/issues/42/").mock(
        return_value=httpx.Response(200, json={
            "id": "42",
            "title": "ValueError",
            "culprit": "app.py",
            "status": "unresolved",
            "count": "3",
            "firstSeen": "2026-01-01T00:00:00Z",
            "lastSeen": "2026-06-01T00:00:00Z",
            "metadata": {"type": "ValueError"},
        })
    )
    issue = await client.get_issue("42")
    assert issue.id == "42"
    assert issue.metadata == {"type": "ValueError"}


@respx.mock
async def test_list_events(client):
    respx.get("https://sentry.example.com/api/0/issues/42/events/").mock(
        return_value=httpx.Response(200, json=[{
            "id": "evt-1",
            "message": "ValueError at /api/users",
            "dateCreated": "2026-06-01T12:00:00Z",
            "tags": [{"key": "environment", "value": "production"}],
        }])
    )
    events = await client.list_events("42", limit=5)
    assert events[0].id == "evt-1"
    assert events[0].tags == {"environment": "production"}
    assert events[0].issue_id == "42"


@respx.mock
async def test_auth_error(client):
    respx.get("https://sentry.example.com/api/0/organizations/acme/projects/").mock(
        return_value=httpx.Response(401)
    )
    with pytest.raises(SentryAuthError):
        await client.list_projects()


@respx.mock
async def test_not_found(client):
    respx.get("https://sentry.example.com/api/0/issues/999/").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(SentryNotFoundError) as exc_info:
        await client.get_issue("999")
    assert "999" in str(exc_info.value)


@respx.mock
async def test_timeout(client):
    respx.get("https://sentry.example.com/api/0/organizations/acme/projects/").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    with pytest.raises(SentryTimeoutError):
        await client.list_projects()


@respx.mock
async def test_upstream_error(client):
    respx.get("https://sentry.example.com/api/0/organizations/acme/projects/").mock(
        return_value=httpx.Response(500)
    )
    with pytest.raises(SentryUpstreamError):
        await client.list_projects()


async def test_auth_header_sent(client):
    with respx.mock:
        route = respx.get("https://sentry.example.com/api/0/organizations/acme/projects/").mock(
            return_value=httpx.Response(200, json=[])
        )
        await client.list_projects()
        assert route.calls[0].request.headers["Authorization"] == "Bearer tok-test"
