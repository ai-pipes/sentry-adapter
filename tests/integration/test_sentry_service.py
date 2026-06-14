import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from sentry_adapter.application.sentry_service import SentryService
from sentry_adapter.domain.models import AuthContext, SentryProject, SentryIssue
from sentry_adapter.infrastructure.audit.stdout_backend import StdoutAuditBackend
from sentry_adapter.infrastructure.presidio_sanitizer import PresidioSanitizer


@pytest.fixture(scope="module")
def sanitizer():
    return PresidioSanitizer(
        entities=["EMAIL_ADDRESS", "IP_ADDRESS"],
        secrets_regex=True,
        nlp_model="en_core_web_sm",
    )


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def service(mock_client, sanitizer):
    return SentryService(
        client=mock_client,
        sanitizer=sanitizer,
        audit=StdoutAuditBackend(),
        log_body=False,
    )


@pytest.fixture
def auth():
    return AuthContext(key_id="k1", user_id="alice", team_id="eng")


async def test_email_in_project_name_is_sanitized(service, mock_client, auth, capsys):
    mock_client.list_projects.return_value = [
        SentryProject(id="1", slug="backend", name="Project by alice@corp.com", platform="python", status="active")
    ]
    result = await service.list_projects(auth=auth, request_id="req-integration-1")
    assert "alice@corp.com" not in result[0]["name"]
    log = json.loads(capsys.readouterr().out.strip())
    assert "EMAIL_ADDRESS" in log["sanitized_fields"]
    assert log["status"] == "success"


async def test_ip_in_issue_title_is_sanitized(service, mock_client, auth):
    mock_client.get_issue.return_value = SentryIssue(
        id="99",
        title="Request from 10.0.0.42 failed",
        culprit="views.py",
        status="unresolved",
        count=5,
        first_seen=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_seen=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    result = await service.get_issue(issue_id="99", auth=auth, request_id="req-integration-2")
    assert "10.0.0.42" not in result["title"]


async def test_clean_data_passes_through_unchanged(service, mock_client, auth):
    mock_client.list_projects.return_value = [
        SentryProject(id="2", slug="frontend", name="Frontend App", platform="javascript", status="active")
    ]
    result = await service.list_projects(auth=auth, request_id="req-integration-3")
    assert result[0]["name"] == "Frontend App"
    assert result[0]["slug"] == "frontend"
