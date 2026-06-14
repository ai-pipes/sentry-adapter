import json
import sys

from sentry_adapter.domain.audit import BaseAuditBackend
from sentry_adapter.domain.models import AuditRecord


class StdoutAuditBackend(BaseAuditBackend):
    async def write(self, record: AuditRecord) -> None:
        print(json.dumps(_to_dict(record)), file=sys.stdout, flush=True)


def _to_dict(record: AuditRecord) -> dict:
    return {
        "request_id": record.request_id,
        "timestamp": record.timestamp.isoformat(),
        "key_id": record.key_id,
        "user_id": record.user_id,
        "team_id": record.team_id,
        "tool": record.tool,
        "latency_ms": record.latency_ms,
        "sanitized_fields": record.sanitized_fields,
        "status": record.status,
        "error": record.error,
        "args": record.args,
        "response": record.response,
    }
