from abc import ABC, abstractmethod
from .models import AuditRecord


class BaseAuditBackend(ABC):
    @abstractmethod
    async def write(self, record: AuditRecord) -> None:
        ...
