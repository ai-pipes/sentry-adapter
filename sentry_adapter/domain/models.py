from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AuthContext:
    key_id: str
    user_id: str | None
    team_id: str | None


@dataclass
class SanitizerResult:
    text: str
    detected: list[str]


@dataclass
class AuditRecord:
    request_id: str
    timestamp: datetime
    key_id: str
    user_id: str | None
    team_id: str | None
    tool: str
    latency_ms: int
    sanitized_fields: list[str]
    status: str  # success | error
    error: str | None = None
    args: dict | None = None       # only if body_logging=true
    response: dict | None = None   # only if body_logging=true


@dataclass
class SentryProject:
    id: str
    slug: str
    name: str
    platform: str | None
    status: str


@dataclass
class SentryIssue:
    id: str
    title: str
    culprit: str
    status: str
    count: int
    first_seen: datetime
    last_seen: datetime
    metadata: dict = field(default_factory=dict)


@dataclass
class SentryEvent:
    id: str
    issue_id: str
    timestamp: datetime
    message: str
    tags: dict = field(default_factory=dict)
