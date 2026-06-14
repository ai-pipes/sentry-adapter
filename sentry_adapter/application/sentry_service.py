import dataclasses
import time
from datetime import datetime, timezone
from typing import Any

from sentry_adapter.domain.audit import BaseAuditBackend
from sentry_adapter.domain.exceptions import (
    SentryAuthError, SentryNotFoundError, SentryTimeoutError, SentryUpstreamError,
)
from sentry_adapter.domain.models import AuthContext, AuditRecord
from sentry_adapter.domain.sanitizer import BaseSanitizer
from sentry_adapter.infrastructure.sentry_client import SentryClient


class SentryService:
    def __init__(
        self,
        client: SentryClient,
        sanitizer: BaseSanitizer,
        audit: BaseAuditBackend,
        log_body: bool = False,
    ):
        self._client = client
        self._sanitizer = sanitizer
        self._audit = audit
        self._log_body = log_body

    async def list_projects(self, auth: AuthContext, request_id: str) -> list[dict]:
        return await self._call("list_projects", {}, auth, request_id, self._client.list_projects)

    async def list_issues(
        self, project_slug: str, query: str, limit: int, auth: AuthContext, request_id: str
    ) -> list[dict]:
        args = {"project_slug": project_slug, "query": query, "limit": limit}
        return await self._call(
            "list_issues", args, auth, request_id,
            lambda: self._client.list_issues(project_slug, query, limit),
        )

    async def get_issue(self, issue_id: str, auth: AuthContext, request_id: str) -> dict:
        return await self._call(
            "get_issue", {"issue_id": issue_id}, auth, request_id,
            lambda: self._client.get_issue(issue_id),
        )

    async def list_events(
        self, issue_id: str, limit: int, auth: AuthContext, request_id: str
    ) -> list[dict]:
        args = {"issue_id": issue_id, "limit": limit}
        return await self._call(
            "list_events", args, auth, request_id,
            lambda: self._client.list_events(issue_id, limit),
        )

    async def _call(
        self,
        tool: str,
        args: dict,
        auth: AuthContext,
        request_id: str,
        fetch_fn,
    ) -> Any:
        start = time.monotonic()
        status = "success"
        error = None
        sanitized_fields: list[str] = []
        sanitized_result = None

        try:
            raw = await fetch_fn()
            raw_dict = _to_serializable(raw)
            sanitized_result, sanitized_fields = await self._sanitize_value(raw_dict)
            return sanitized_result
        except (SentryAuthError, SentryNotFoundError, SentryTimeoutError, SentryUpstreamError) as e:
            status = "error"
            error = type(e).__name__
            raise
        except Exception as e:
            status = "error"
            error = str(e)
            raise
        finally:
            await self._audit.write(AuditRecord(
                request_id=request_id,
                timestamp=datetime.now(timezone.utc),
                key_id=auth.key_id,
                user_id=auth.user_id,
                team_id=auth.team_id,
                tool=tool,
                latency_ms=_ms(start),
                sanitized_fields=sanitized_fields,
                status=status,
                error=error,
                args=args if self._log_body else None,
                response=sanitized_result if self._log_body else None,
            ))

    async def _sanitize_value(self, value: Any) -> tuple[Any, list[str]]:
        if isinstance(value, str):
            result = await self._sanitizer.clean(value)
            return result.text, result.detected
        elif isinstance(value, dict):
            out, detected = {}, []
            for k, v in value.items():
                sv, d = await self._sanitize_value(v)
                out[k] = sv
                detected.extend(d)
            return out, _dedup(detected)
        elif isinstance(value, list):
            out, detected = [], []
            for item in value:
                sv, d = await self._sanitize_value(item)
                out.append(sv)
                detected.extend(d)
            return out, _dedup(detected)
        return value, []


def _to_serializable(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_serializable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, list):
        return [_to_serializable(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    return obj


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
