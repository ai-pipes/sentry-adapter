import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from sentry_adapter.application.sentry_service import SentryService
from sentry_adapter.domain.exceptions import SentryAuthError
from sentry_adapter.domain.models import (
    AuthContext, SanitizerResult, SentryIssue, SentryProject,
)


@pytest.fixture
def auth():
    return AuthContext(key_id="k1", user_id="alice", team_id="eng")


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def mock_sanitizer():
    sanitizer = AsyncMock()
    sanitizer.clean.return_value = SanitizerResult(text="sanitized", detected=["EMAIL_ADDRESS"])
    return sanitizer


@pytest.fixture
def mock_audit():
    return AsyncMock()


@pytest.fixture
def service(mock_client, mock_sanitizer, mock_audit):
    return SentryService(
        client=mock_client,
        sanitizer=mock_sanitizer,
        audit=mock_audit,
        log_body=False,
    )


async def test_list_projects_returns_sanitized_dict(service, mock_client, mock_sanitizer, auth):
    mock_client.list_projects.return_value = [
        SentryProject(id="1", slug="backend", name="alice@corp.com", platform="python", status="active")
    ]
    result = await service.list_projects(auth=auth, request_id="req-1")
    assert isinstance(result, list)
    assert result[0]["name"] == "sanitized"
    mock_sanitizer.clean.assert_called()


async def test_audit_written_on_success(service, mock_client, mock_audit, auth):
    mock_client.list_projects.return_value = []
    await service.list_projects(auth=auth, request_id="req-1")
    mock_audit.write.assert_called_once()
    record = mock_audit.write.call_args[0][0]
    assert record.status == "success"
    assert record.tool == "list_projects"
    assert record.key_id == "k1"
    assert record.request_id == "req-1"


async def test_audit_written_on_error(service, mock_client, mock_audit, auth):
    mock_client.list_projects.side_effect = SentryAuthError()
    with pytest.raises(SentryAuthError):
        await service.list_projects(auth=auth, request_id="req-1")
    mock_audit.write.assert_called_once()
    record = mock_audit.write.call_args[0][0]
    assert record.status == "error"
    assert record.error == "SentryAuthError"


async def test_audit_not_in_response_when_body_logging_disabled(service, mock_client, mock_audit, auth):
    mock_client.list_projects.return_value = []
    await service.list_projects(auth=auth, request_id="req-1")
    record = mock_audit.write.call_args[0][0]
    assert record.args is None
    assert record.response is None


async def test_audit_includes_body_when_enabled(mock_client, mock_sanitizer, mock_audit, auth):
    mock_sanitizer.clean.return_value = SanitizerResult(text="clean", detected=[])
    service_with_log = SentryService(
        client=mock_client,
        sanitizer=mock_sanitizer,
        audit=mock_audit,
        log_body=True,
    )
    mock_client.list_projects.return_value = []
    await service_with_log.list_projects(auth=auth, request_id="req-1")
    record = mock_audit.write.call_args[0][0]
    assert record.args == {}
    assert record.response == []


async def test_sanitized_fields_aggregated(service, mock_client, mock_sanitizer, mock_audit, auth):
    # 2 projects × 4 string fields each (id, slug, name, status) = 8 clean() calls
    # platform=None is NOT a string, skipped by _sanitize_value
    mock_sanitizer.clean.side_effect = [
        SanitizerResult(text="safe", detected=["EMAIL_ADDRESS"]),  # project 1 id
        SanitizerResult(text="safe", detected=[]),                   # project 1 slug
        SanitizerResult(text="safe", detected=["EMAIL_ADDRESS"]),  # project 1 name
        SanitizerResult(text="safe", detected=[]),                   # project 1 status
        SanitizerResult(text="safe", detected=["IP_ADDRESS"]),     # project 2 id
        SanitizerResult(text="safe", detected=[]),                   # project 2 slug
        SanitizerResult(text="safe", detected=["EMAIL_ADDRESS"]),  # project 2 name
        SanitizerResult(text="safe", detected=[]),                   # project 2 status
    ]
    mock_client.list_projects.return_value = [
        SentryProject(id="1", slug="a", name="n1", platform=None, status="active"),
        SentryProject(id="2", slug="b", name="n2", platform=None, status="active"),
    ]
    await service.list_projects(auth=auth, request_id="req-1")
    record = mock_audit.write.call_args[0][0]
    assert "EMAIL_ADDRESS" in record.sanitized_fields
    assert "IP_ADDRESS" in record.sanitized_fields
    assert record.sanitized_fields.count("EMAIL_ADDRESS") == 1  # deduplicated


async def test_get_issue_returns_dict(service, mock_client, mock_sanitizer, auth):
    mock_sanitizer.clean.return_value = SanitizerResult(text="safe", detected=[])
    mock_client.get_issue.return_value = SentryIssue(
        id="42", title="Error", culprit="app.py", status="unresolved",
        count=3,
        first_seen=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_seen=datetime(2026, 6, 1, tzinfo=timezone.utc),
        metadata={},
    )
    result = await service.get_issue(issue_id="42", auth=auth, request_id="r1")
    assert result["id"] == "safe"
    assert isinstance(result["first_seen"], str)  # datetime → ISO string
