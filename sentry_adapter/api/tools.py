from mcp.server.fastmcp import FastMCP

from sentry_adapter.api.context import get_auth, get_request_id
from sentry_adapter.application.sentry_service import SentryService
from sentry_adapter.domain.exceptions import (
    SentryAuthError, SentryNotFoundError, SentryTimeoutError, SentryUpstreamError,
)


def register_tools(mcp: FastMCP, service: SentryService) -> None:
    @mcp.tool()
    async def list_projects() -> list[dict]:
        """List all Sentry projects in the organization."""
        try:
            return await service.list_projects(auth=get_auth(), request_id=get_request_id())
        except SentryAuthError:
            raise ValueError("Sentry authentication failed")
        except SentryTimeoutError:
            raise ValueError("Sentry upstream timeout")
        except SentryUpstreamError as e:
            raise ValueError(str(e))

    @mcp.tool()
    async def list_issues(
        project_slug: str,
        query: str = "",
        limit: int = 25,
    ) -> list[dict]:
        """List issues for a Sentry project. Filter with query (e.g. 'is:unresolved')."""
        try:
            return await service.list_issues(
                project_slug=project_slug,
                query=query,
                limit=limit,
                auth=get_auth(),
                request_id=get_request_id(),
            )
        except SentryNotFoundError as e:
            raise ValueError(str(e))
        except SentryAuthError:
            raise ValueError("Sentry authentication failed")
        except SentryTimeoutError:
            raise ValueError("Sentry upstream timeout")
        except SentryUpstreamError as e:
            raise ValueError(str(e))

    @mcp.tool()
    async def get_issue(issue_id: str) -> dict:
        """Get details of a Sentry issue with sanitized stacktrace and metadata."""
        try:
            return await service.get_issue(
                issue_id=issue_id, auth=get_auth(), request_id=get_request_id()
            )
        except SentryNotFoundError as e:
            raise ValueError(str(e))
        except SentryAuthError:
            raise ValueError("Sentry authentication failed")
        except SentryTimeoutError:
            raise ValueError("Sentry upstream timeout")
        except SentryUpstreamError as e:
            raise ValueError(str(e))

    @mcp.tool()
    async def list_events(issue_id: str, limit: int = 25) -> list[dict]:
        """List events for a Sentry issue."""
        try:
            return await service.list_events(
                issue_id=issue_id, limit=limit, auth=get_auth(), request_id=get_request_id()
            )
        except SentryNotFoundError as e:
            raise ValueError(str(e))
        except SentryAuthError:
            raise ValueError("Sentry authentication failed")
        except SentryTimeoutError:
            raise ValueError("Sentry upstream timeout")
        except SentryUpstreamError as e:
            raise ValueError(str(e))
