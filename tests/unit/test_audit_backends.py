import json
import pytest
from datetime import datetime, timezone
from sentry_adapter.domain.models import AuditRecord
from sentry_adapter.infrastructure.audit.stdout_backend import StdoutAuditBackend
from sentry_adapter.infrastructure.audit.file_backend import FileAuditBackend


def _make_record(**kwargs) -> AuditRecord:
    defaults = dict(
        request_id="req-1",
        timestamp=datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc),
        key_id="k1",
        user_id="alice",
        team_id="eng",
        tool="list_projects",
        latency_ms=42,
        sanitized_fields=["EMAIL_ADDRESS"],
        status="success",
    )
    return AuditRecord(**{**defaults, **kwargs})


async def test_stdout_backend_writes_json(capsys):
    backend = StdoutAuditBackend()
    await backend.write(_make_record())
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["request_id"] == "req-1"
    assert data["tool"] == "list_projects"
    assert data["latency_ms"] == 42
    assert data["sanitized_fields"] == ["EMAIL_ADDRESS"]
    assert data["status"] == "success"
    assert data["error"] is None


async def test_stdout_backend_error_record(capsys):
    backend = StdoutAuditBackend()
    await backend.write(_make_record(status="error", error="SentryAuthError"))
    data = json.loads(capsys.readouterr().out.strip())
    assert data["status"] == "error"
    assert data["error"] == "SentryAuthError"


async def test_file_backend_appends_jsonl(tmp_path):
    path = str(tmp_path / "audit.jsonl")
    backend = FileAuditBackend(path=path)
    await backend.write(_make_record(request_id="r1"))
    await backend.write(_make_record(request_id="r2"))
    lines = (tmp_path / "audit.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["request_id"] == "r1"
    assert json.loads(lines[1])["request_id"] == "r2"


async def test_file_backend_creates_file(tmp_path):
    path = str(tmp_path / "new_dir" / "audit.jsonl")
    backend = FileAuditBackend(path=path)
    await backend.write(_make_record())
    data = json.loads(open(path).read().strip())
    assert data["status"] == "success"
