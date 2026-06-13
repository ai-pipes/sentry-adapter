import asyncio
import json
from pathlib import Path

from sentry_adapter.domain.audit import BaseAuditBackend
from sentry_adapter.domain.models import AuditRecord
from sentry_adapter.infrastructure.audit.stdout_backend import _to_dict


class FileAuditBackend(BaseAuditBackend):
    def __init__(self, path: str):
        self._path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    async def write(self, record: AuditRecord) -> None:
        line = json.dumps(_to_dict(record))
        await asyncio.to_thread(self._write_sync, line)

    def _write_sync(self, line: str) -> None:
        with open(self._path, "a") as f:
            f.write(line + "\n")
