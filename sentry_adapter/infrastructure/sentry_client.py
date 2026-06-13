from datetime import datetime
import httpx

from sentry_adapter.domain.exceptions import (
    SentryAuthError, SentryNotFoundError, SentryTimeoutError, SentryUpstreamError,
)
from sentry_adapter.domain.models import SentryEvent, SentryIssue, SentryProject


class SentryClient:
    def __init__(self, base_url: str, auth_token: str, organization: str, timeout: int = 10):
        self._base_url = base_url.rstrip("/")
        self._organization = organization
        self._http = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=timeout,
        )

    async def list_projects(self) -> list[SentryProject]:
        data = await self._get(f"/api/0/organizations/{self._organization}/projects/")
        return [self._parse_project(p) for p in data]

    async def list_issues(
        self, project_slug: str, query: str = "", limit: int = 25
    ) -> list[SentryIssue]:
        data = await self._get(
            f"/api/0/projects/{self._organization}/{project_slug}/issues/",
            params={"query": query, "limit": limit},
        )
        return [self._parse_issue(i) for i in data]

    async def get_issue(self, issue_id: str) -> SentryIssue:
        data = await self._get(f"/api/0/issues/{issue_id}/")
        return self._parse_issue(data)

    async def list_events(self, issue_id: str, limit: int = 25) -> list[SentryEvent]:
        data = await self._get(
            f"/api/0/issues/{issue_id}/events/",
            params={"limit": limit},
        )
        return [self._parse_event(issue_id, e) for e in data]

    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        try:
            r = await self._http.get(f"{self._base_url}{path}", params=params)
        except httpx.TimeoutException:
            raise SentryTimeoutError()

        if r.status_code in (401, 403):
            raise SentryAuthError()
        if r.status_code == 404:
            raise SentryNotFoundError(path)
        if not r.is_success:
            raise SentryUpstreamError(f"Sentry returned {r.status_code}")
        return r.json()

    def _parse_project(self, data: dict) -> SentryProject:
        return SentryProject(
            id=data["id"],
            slug=data["slug"],
            name=data["name"],
            platform=data.get("platform"),
            status=data.get("status", "active"),
        )

    def _parse_issue(self, data: dict) -> SentryIssue:
        return SentryIssue(
            id=data["id"],
            title=data["title"],
            culprit=data.get("culprit", ""),
            status=data["status"],
            count=int(data.get("count", 0)),
            first_seen=_parse_dt(data["firstSeen"]),
            last_seen=_parse_dt(data["lastSeen"]),
            metadata=data.get("metadata", {}),
        )

    def _parse_event(self, issue_id: str, data: dict) -> SentryEvent:
        return SentryEvent(
            id=data["id"],
            issue_id=issue_id,
            timestamp=_parse_dt(data["dateCreated"]),
            message=data.get("message", ""),
            tags={tag["key"]: tag["value"] for tag in data.get("tags", [])},
        )

    async def aclose(self) -> None:
        await self._http.aclose()


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
